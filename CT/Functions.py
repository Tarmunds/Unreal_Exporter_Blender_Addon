import bpy
import bmesh
from mathutils import Vector, Matrix

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def _unit(v: Vector) -> Vector:
    l = v.length
    return v if l == 0.0 else (v / l)

def kdop_directions(mode: str):
    if mode == "DOP6":
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
        ]

    elif mode == "DOP10_X":
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((0, 1, 1)),
            Vector((0, 1, -1)),
        ]

    elif mode == "DOP10_Y":
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((1, 0, 1)),
            Vector((1, 0, -1)),
        ]

    elif mode == "DOP10_Z":
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((1, 1, 0)),
            Vector((1, -1, 0)),
        ]

    elif mode == "DOP14":
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((1, 1, 1)),
            Vector((1, -1, 1)),
            Vector((1, 1, -1)),
            Vector((1, -1, -1)),
        ]

    elif mode == "DOP18":
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((1, 1, 0)),
            Vector((1, -1, 0)),
            Vector((1, 0, 1)),
            Vector((1, 0, -1)),
            Vector((0, 1, 1)),
            Vector((0, 1, -1)),
        ]

    elif mode == "DOP26":
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((1, 1, 1)),
            Vector((1, -1, 1)),
            Vector((1, 1, -1)),
            Vector((1, -1, -1)),
            Vector((1, 1, 0)),
            Vector((1, -1, 0)),
            Vector((1, 0, 1)),
            Vector((1, 0, -1)),
            Vector((0, 1, 1)),
            Vector((0, 1, -1)),
        ]

    else:
        raise ValueError(f"Unsupported k-DOP mode: {mode}")

    return [_unit(d) for d in dirs]

def get_object_vertices(obj: bpy.types.Object, use_evaluated_mesh: bool, space: str):
    if obj.type != "MESH":
        return []

    if use_evaluated_mesh:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        try:
            if space == "WORLD":
                mw = obj.matrix_world
                return [mw @ Vector(v.co) for v in mesh.vertices]
            return [Vector(v.co) for v in mesh.vertices]
        finally:
            obj_eval.to_mesh_clear()
    else:
        mesh = obj.data
        if space == "WORLD":
            mw = obj.matrix_world
            return [mw @ Vector(v.co) for v in mesh.vertices]
        return [Vector(v.co) for v in mesh.vertices]
    
def build_kdop_planes(verts, dirs, dedupe_eps=1e-9):
    planes = []

    for u in dirs:
        min_p = 1e30
        max_p = -1e30
        for v in verts:
            p = u.dot(v)
            if p < min_p:
                min_p = p
            if p > max_p:
                max_p = p

        planes.append((u.copy(), max_p))         
        planes.append((-u.copy(), -min_p))        

    #dedupe
    unique = []
    for (n, d) in planes:
        found = False
        for (n2, d2) in unique:
            if (n - n2).length < dedupe_eps and abs(d - d2) < 1e-6:
                found = True
                break
        if not found:
            unique.append((n, d))

    return unique

def intersect_3_planes(n1, d1, n2, d2, n3, d3, det_eps=1e-10):
    A = Matrix((n1, n2, n3))
    det = A.determinant()
    if abs(det) < det_eps:
        return None
    b = Vector((d1, d2, d3))
    return A.inverted() @ b


def point_inside_all_planes(p: Vector, planes, eps=1e-6) -> bool:
    for (n, d) in planes:
        if n.dot(p) > d + eps:
            return False
    return True

def generate_kdop_points(planes, inside_eps=1e-6, hash_decimals=6):
    pts = []
    seen = set()

    nplanes = len(planes)
    for i in range(nplanes - 2):
        n1, d1 = planes[i]
        for j in range(i + 1, nplanes - 1):
            n2, d2 = planes[j]
            for k in range(j + 1, nplanes):
                n3, d3 = planes[k]
                p = intersect_3_planes(n1, d1, n2, d2, n3, d3)
                if p is None:
                    continue
                if not point_inside_all_planes(p, planes, eps=inside_eps):
                    continue

                key = (round(p.x, hash_decimals), round(p.y, hash_decimals), round(p.z, hash_decimals))
                if key in seen:
                    continue
                seen.add(key)
                pts.append(p)

    return pts

def build_convex_hull_mesh_from_points(points, name="KDOP_HULL"):
    if len(points) < 4:
        return None

    bm = bmesh.new()
    try:
        bm_verts = [bm.verts.new(p) for p in points]
        bm.verts.ensure_lookup_table()

        res = bmesh.ops.convex_hull(bm, input=bm_verts, use_existing_faces=False)

        # Clean leftovers that can appear with convex_hull
        geom_unused = res.get("geom_unused", [])
        geom_interior = res.get("geom_interior", [])
        if geom_unused or geom_interior:
            bmesh.ops.delete(bm, geom=geom_unused + geom_interior, context="VERTS")

        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        mesh.update()
        return mesh
    finally:
        bm.free()

def create_collision_object(source_obj, mesh, obj_name, display_wire=True, parent=True, context=None):
    col_obj = bpy.data.objects.new(obj_name, mesh)

    # Link to the same collections as the source object
    if source_obj.users_collection:
        for c in source_obj.users_collection:
            c.objects.link(col_obj)
    else:
        bpy.context.collection.objects.link(col_obj)

    set_display(col_obj, context)

    return col_obj

def set_display(obj, context):
    ct_props = context.scene.ct_properties
    wire = ct_props.wire_display
    color = ct_props.color_display
    mat, mat_color = assign_collision_material(obj, mat_color=ct_props.mat_color)
    if wire and color:
        obj.display_type = "SOLID"
        obj.show_in_front = True
        obj.show_wire = True
        mat.diffuse_color = mat_color
    elif wire:
        obj.display_type = "WIRE"
        obj.show_in_front = False
        obj.show_wire = False
        mat.diffuse_color = (1, 1, 1, 1)
    elif color:
        obj.display_type = "SOLID"
        obj.show_in_front = True
        obj.show_wire = False
        mat.diffuse_color = mat_color
    else:
        obj.display_type = "SOLID"
        obj.show_in_front = False
        obj.show_wire = False
        mat.diffuse_color = (1, 1, 1, 1)
    
    obj.hide_select = not ct_props.selectable


def assign_collision_material(obj, mat_color=(0.31, 0.258, 1, 0.278)):
    mat_name = "M_CT_Collision_Mat"
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(mat_name)
        mat.diffuse_color = mat_color
        mat.roughness = 1.0
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    return mat, mat_color

def get_collision_objects():
    return [
        obj for obj in bpy.data.objects
        if obj.type == 'MESH' and (obj.name.startswith("UCX_") or obj.name.startswith("UBX_") or obj.name.startswith("USP_"))
    ]

def update_collision_object_display(self, context):
    collision_meshes = get_collision_objects()
    for obj in collision_meshes:
        set_display(obj, context)

def update_color_display(self, context):
    ct_props = context.scene.ct_properties
    mat_name = "M_CT_Collision_Mat"
    mat = bpy.data.materials.get(mat_name)
    if mat:
        mat.diffuse_color = ct_props.mat_color

def set_collision_objects_visibility(visible, context):
    collision_meshes = get_collision_objects()
    ct_props = context.scene.ct_properties

    if ct_props.visibility_button_field == "All_MESH":
        for obj in collision_meshes:
            obj.hide_viewport = not visible

    elif ct_props.visibility_button_field == "CURRENT_HIERARCHY":
        obj = get_top_parents(context.selected_objects)
        for obj in obj :
            for child in obj.children_recursive:
                if child in collision_meshes:
                    child.hide_viewport = not visible


def update_selectable(self, context):
    ct_props = context.scene.ct_properties
    collision_meshes = get_collision_objects()
    for obj in collision_meshes:
        obj.hide_select = not ct_props.selectable

def get_top_parents(objects):
    top_parents = set()
    for obj in objects:
        parent = obj
        while parent.parent:
            parent = parent.parent
        top_parents.add(parent)
    return top_parents