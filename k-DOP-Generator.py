bl_info = {
    "name": "k-DOP Collision Hull Generator",
    "author": "Tarmunds",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > KDOP",
    "description": "Generate k-DOP convex collision hull (6/14/18/26) from selected mesh",
    "category": "Object",
}

import bpy
import bmesh
from math import sqrt
from mathutils import Vector, Matrix


# -----------------------------
# Direction sets (unit vectors)
# -----------------------------

def _unit(v: Vector) -> Vector:
    l = v.length
    if l == 0.0:
        return v
    return v / l


def kdop_directions(k: int):
    if k == 6:
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
        ]
    elif k == 14:
        # Klosowski et al. 1998 (7 axes, plus +/- planes => 14 planes)
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((1, 1, 1)),
            Vector((1, -1, 1)),
            Vector((1, 1, -1)),
            Vector((1, -1, -1)),
        ]
    elif k == 18:
        # 3 axes + 6 edge-cutting axes (plus +/- planes => 18 planes)
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
    elif k == 26:
        # Union of 14-DOP and 18-DOP defining axes (per Klosowski et al.)
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
        raise ValueError("Unsupported k")

    return [_unit(d) for d in dirs]



# -----------------------------
# Core geometry
# -----------------------------

def get_object_vertices_local(obj: bpy.types.Object):
    """
    Get evaluated mesh vertices in the object's local space (after modifiers).
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)

    if obj_eval.type != "MESH":
        return []

    mesh = obj_eval.to_mesh()
    try:
        verts = [Vector(v.co) for v in mesh.vertices]
        return verts
    finally:
        obj_eval.to_mesh_clear()


def build_kdop_planes(verts_local, dirs, eps=1e-9):
    """
    Returns list of planes in the form (n, d) representing half-space:
        n.dot(x) <= d
    For each direction u, we create planes for +u and -u based on max/min projections.
    """
    planes = []

    for u in dirs:
        min_p = 1e30
        max_p = -1e30
        for v in verts_local:
            p = u.dot(v)
            if p < min_p:
                min_p = p
            if p > max_p:
                max_p = p

        # +u plane
        planes.append((u.copy(), max_p))

        # -u plane
        planes.append((-u.copy(), -min_p))

    # Optional: remove near-duplicate planes (rare, but can happen with degenerate meshes)
    unique = []
    for (n, d) in planes:
        found = False
        for (n2, d2) in unique:
            if (n - n2).length < eps and abs(d - d2) < 1e-6:
                found = True
                break
        if not found:
            unique.append((n, d))

    return unique


def intersect_3_planes(n1, d1, n2, d2, n3, d3, det_eps=1e-10):
    """
    Solve:
        n1·x = d1
        n2·x = d2
        n3·x = d3
    Using matrix inversion.
    Returns Vector or None if near-singular.
    """
    A = Matrix((n1, n2, n3))
    det = A.determinant()
    if abs(det) < det_eps:
        return None
    b = Vector((d1, d2, d3))
    x = A.inverted() @ b
    return x


def point_inside_all_planes(p: Vector, planes, eps=1e-6) -> bool:
    for (n, d) in planes:
        if n.dot(p) > d + eps:
            return False
    return True


def generate_kdop_points(planes, inside_eps=1e-6, hash_decimals=6):
    """
    Generate candidate polyhedron vertices by intersecting all plane triplets,
    then keep those inside all half-spaces.
    """
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
    """
    Create a new Mesh datablock built as the convex hull of provided points.
    """
    if len(points) < 4:
        return None

    bm = bmesh.new()
    try:
        bm_verts = [bm.verts.new(p) for p in points]
        bm.verts.ensure_lookup_table()

        # bmesh convex hull will create faces/edges
        res = bmesh.ops.convex_hull(bm, input=bm_verts, use_existing_faces=False)
        # Clean loose edges/verts if any
        bmesh.ops.delete(bm, geom=res.get("geom_unused", []), context='VERTS')

        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        mesh.update()
        return mesh
    finally:
        bm.free()


def create_collision_object(source_obj, mesh, obj_name, display_wire=True, parent=True):
    """
    Create object in same collection(s) as source_obj, optionally parent it.
    """
    col_obj = bpy.data.objects.new(obj_name, mesh)

    # Link into same collections as the source object (best effort).
    if source_obj.users_collection:
        for c in source_obj.users_collection:
            c.objects.link(col_obj)
    else:
        bpy.context.collection.objects.link(col_obj)

    # Match transforms
    col_obj.matrix_world = source_obj.matrix_world.copy()

    if parent:
        col_obj.parent = source_obj
        col_obj.matrix_parent_inverse = source_obj.matrix_world.inverted_safe()

    if display_wire:
        col_obj.display_type = 'WIRE'
        col_obj.show_in_front = True

    return col_obj


# -----------------------------
# Operator + UI
# -----------------------------

class KDOP_OT_generate_collision(bpy.types.Operator):
    bl_idname = "object.kdop_generate_collision"
    bl_label = "Generate k-DOP Collision Hull"
    bl_options = {'REGISTER', 'UNDO'}

    kdop_k: bpy.props.EnumProperty(
        name="k-DOP",
        items=[
            ('6', "6-DOP (AABB)", "Axis aligned box planes"),
            ('14', "14-DOP", "Axis + body diagonals"),
            ('18', "18-DOP", "Axis + face diagonals"),
            ('26', "26-DOP", "Axis + face + body diagonals"),
        ],
        default='14',
    )

    name_prefix: bpy.props.StringProperty(
        name="Name Prefix",
        default="UCX_",
        description="Prefix for the generated collision object name (common Unreal convention is UCX_)",
    )

    use_evaluated_mesh: bpy.props.BoolProperty(
        name="Use Evaluated Mesh (Modifiers)",
        default=True,
        description="Use mesh after modifiers (recommended)",
    )

    inside_epsilon: bpy.props.FloatProperty(
        name="Inside Epsilon",
        default=1e-6,
        min=1e-9,
        max=1e-2,
        description="Tolerance for testing if a point is inside all planes",
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({'ERROR'}, "Select an active mesh object")
            return {'CANCELLED'}

        k = int(self.kdop_k)
        dirs = kdop_directions(k)

        verts_local = get_object_vertices_local(obj)
        if not verts_local:
            self.report({'ERROR'}, "Object has no vertices")
            return {'CANCELLED'}

        planes = build_kdop_planes(verts_local, dirs)

        points = generate_kdop_points(planes, inside_eps=self.inside_epsilon)
        if len(points) < 4:
            self.report({'ERROR'}, f"Not enough hull points generated ({len(points)}). Try a different k-DOP or increase epsilon.")
            return {'CANCELLED'}

        hull_mesh = build_convex_hull_mesh_from_points(points, name=f"{obj.name}_KDOP{k}_MESH")
        if hull_mesh is None:
            self.report({'ERROR'}, "Failed to build convex hull mesh")
            return {'CANCELLED'}

        col_name = f"{self.name_prefix}{obj.name}_KDOP{k}"
        col_obj = create_collision_object(obj, hull_mesh, col_name, display_wire=True, parent=True)

        # Select the created hull
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        col_obj.select_set(True)
        context.view_layer.objects.active = col_obj

        self.report({'INFO'}, f"Generated {k}-DOP collision hull: {col_obj.name} (points: {len(points)}, planes: {len(planes)})")
        return {'FINISHED'}


class KDOP_PT_panel(bpy.types.Panel):
    bl_label = "k-DOP Collision"
    bl_idname = "KDOP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tarmunds Addons"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Generate k-DOP Hull")
        layout.operator("object.kdop_generate_collision", text="Generate", icon='MESH_CUBE')
        layout.separator()
        layout.label(text="Tip: Select a mesh object in Object Mode.")


classes = (
    KDOP_OT_generate_collision,
    KDOP_PT_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
