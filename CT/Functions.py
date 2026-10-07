import bpy
import bmesh
from mathutils import Vector, Matrix
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d
from ..UEE.Functions import convert_to_mesh

COLLISION_PREFIXES = ("UCX_", "UBX_", "USP_", "UCP_")
SLICE_TAG = "ct_slice"

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def collision_tools_enabled(context):
    addon = context.preferences.addons.get(__package__.rpartition(".")[0])
    return bool(addon.preferences.show_collision_tools) if addon else True

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

def get_object_vertices(obj: bpy.types.Object, use_evaluated_mesh: bool, space = "WORLD"):
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
        all_geom = geom_unused + geom_interior
        uniq = []
        seen = set()
        for g in all_geom:
            if g.is_valid:
                k = id(g)
                if k not in seen:
                    seen.add(k)
                    uniq.append(g)
        if uniq:
            bmesh.ops.delete(bm, geom=uniq, context="VERTS")

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
    elif wire:
        obj.display_type = "WIRE"
        obj.show_in_front = False
        obj.show_wire = False
    elif color:
        obj.display_type = "SOLID"
        obj.show_in_front = True
        obj.show_wire = False
    else:
        obj.display_type = "SOLID"
        obj.show_in_front = False
        obj.show_wire = False
    # One shared material, so the colour follows the toggle for every collision at once.
    setup_collision_material(mat, mat_color if color else (1.0, 1.0, 1.0, 1.0))
    
    obj.hide_select = not ct_props.selectable

def set_display_socket(socket, context):
    ct_props = context.scene.ct_properties
    d_name = ct_props.socket_name
    d_front = ct_props.socket_in_front
    selectable = ct_props.selectable_socket
    
    socket.show_name = d_name
    socket.show_in_front = d_front
    socket.hide_select = not selectable


def setup_collision_material(mat, mat_color):
    """Make the collision material read as a translucent overlay in every shading mode.

    diffuse_color alone only covers Solid shading, which is why collision imported from
    Unreal kept showing its own material in Material Preview and Rendered.
    """
    mat.diffuse_color = mat_color
    mat.roughness = 1.0
    mat.surface_render_method = 'BLENDED'
    node = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if mat.node_tree else None
    if node:
        node.inputs["Base Color"].default_value = (mat_color[0], mat_color[1], mat_color[2], 1.0)
        node.inputs["Alpha"].default_value = mat_color[3]
        node.inputs["Roughness"].default_value = 1.0
    return mat

def get_collision_material(mat_color=(0.31, 0.258, 1, 0.278)):
    mat = bpy.data.materials.get("M_CT_Collision_Mat")
    if mat is None:
        mat = bpy.data.materials.new("M_CT_Collision_Mat")
    return setup_collision_material(mat, mat_color)

def assign_collision_material(obj, mat_color=(0.31, 0.258, 1, 0.278)):
    mat = get_collision_material(mat_color)
    # A collision mesh keeps exactly one slot holding the collision material. Whatever came
    # in with it (Unreal imports arrive with their own materials, joins leave leftovers)
    # is replaced rather than kept alongside.
    mats = obj.data.materials
    if len(mats) != 1 or mats[0] is not mat:
        mats.clear()
        mats.append(mat)
    return mat, mat_color

def get_collision_objects():
    return [obj for obj in bpy.data.objects if check_if_collision(obj)]



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

def get_top_parents(objects, run_once=False):
    if not run_once:
        top_parents = set()
        for obj in objects:
            parent = obj
            while parent.parent:
                parent = parent.parent
            top_parents.add(parent)
        return top_parents
    else:
        obj = objects
        while obj.parent:
            obj = obj.parent
        return obj

def get_relevant_source_objects(context):
    selection = context.selected_objects
    active_obj = context.view_layer.objects.active
    if active_obj and active_obj in selection: 
        return active_obj
    elif selection:
        return selection[0]
    else:
        return None

def prepare_to_iterate_over_selection(context, self, force_multiple = False):
    ct_props = context.scene.ct_properties
    selection = context.selected_objects
    if not selection:
        self.report({'WARNING'}, "No objects selected.")
        return {'CANCELLED'}

    if ct_props.multiple_selection_behavior == "ONE_COLLISION" and not force_multiple:
        first_mesh = selection[0]
        c = [first_mesh]
        multiple = False
    else :
        c = []
        multiple = True
        for obj in selection:
            c.append(obj)
    return c, multiple, selection

def prepare_duplicate_and_join(context, c, multiple, selection):
        if multiple :
            bpy.ops.object.select_all(action='DESELECT')
            c.select_set(True)

        active_obj = context.view_layer.objects.active
        #getting name of active or first of the list
        if active_obj and not multiple and active_obj in selection: 
            og_name = bpy.path.clean_name(active_obj.name) 
            source_obj = active_obj
        else: 
            og_name = bpy.path.clean_name(context.selected_objects[0].name)
            source_obj = context.selected_objects[0]

        bpy.ops.object.duplicate()
        duplicate_objects = context.selected_objects
        convert_to_mesh(duplicate_objects)
        
        bpy.ops.object.join()
        
        dup_and_join_obj = context.selected_objects[0]
        bpy.context.view_layer.objects.active = dup_and_join_obj

        return dup_and_join_obj, og_name, source_obj


def add_box_collision_to_selected(context, self):
    ct_props = context.scene.ct_properties
    c, multiple, selection = prepare_to_iterate_over_selection(context, self)
    for c in c:
        dup_and_join_obj, og_name, source_obj = prepare_duplicate_and_join(context, c, multiple, selection)

        verts = get_object_vertices(dup_and_join_obj, True)
        if not verts:
            continue

        min_v = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
        max_v = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))

        size = max_v - min_v
        if size.length == 0:
            continue

        mesh = bpy.data.meshes.new(f"BoxCollision_{og_name}")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bm.to_mesh(mesh)
        bm.free()

        # Scale cube to fit bounding box
        for v in mesh.vertices:
            v.co.x *= size.x
            v.co.y *= size.y
            v.co.z *= size.z

        col_obj = create_collision_object(dup_and_join_obj, mesh, f"UBX_{og_name}", display_wire=False, parent=True, context=context)
        copy_transforms_and_parent(source_obj, col_obj)
        bpy.data.objects.remove(dup_and_join_obj, do_unlink=True)

        
    
def source_local_bounds(obj):
    """(center, size, verts) of obj's evaluated geometry in its own local space."""
    verts = get_object_vertices(obj, True, "LOCAL")
    if not verts:
        return None
    min_v = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
    max_v = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
    return (min_v + max_v) * 0.5, max_v - min_v, verts

def apply_capsule_fit(ct_props, bounds):
    """Size the capsule properties to the bounds, so the generator builds it fitted.

    Assigned radius first then height: the property update callbacks keep the pair valid.
    """
    _, size, _ = bounds
    # ponytail: capsule assumed Z-up (Unreal convention), no best-axis search
    ct_props.capsule_radius = max(size.x, size.y, 0.02) * 0.5
    ct_props.capsule_height = max(size.z, ct_props.capsule_radius * 2.0)

def fit_transforms_and_parent(source_obj, col_obj, prefix, bounds):
    """Place a freshly spawned primitive onto the source bounds, then parent it."""
    center, size, verts = bounds
    if prefix == "USP":
        r = max(max((v - center).length for v in verts), 1e-4)
        scale = (r, r, r)
    elif prefix == "UBX":
        scale = (max(size.x, 1e-4) * 0.5, max(size.y, 1e-4) * 0.5, max(size.z, 1e-4) * 0.5)
    else:
        scale = (1.0, 1.0, 1.0)  # capsule is already generated at the fitted size

    mw = source_obj.matrix_world @ Matrix.Translation(center) @ Matrix.Diagonal((*scale, 1.0))
    col_obj.parent = source_obj
    col_obj.matrix_parent_inverse = source_obj.matrix_world.inverted_safe()
    col_obj.matrix_world = mw

def copy_transforms_and_parent(target_obj, col_obj):
        col_obj.matrix_world = Matrix.Translation(target_obj.location)
        mw = col_obj.matrix_world.copy()
        col_obj.parent = target_obj
        col_obj.matrix_parent_inverse = target_obj.matrix_world.inverted_safe()
        col_obj.matrix_world = mw

        
        
def find_available_collision_name(name, prefix="UCX"):
    num = 1
    while True:
        name_exists = any(o.name == f"{prefix}_{name}_{num:02}" for o in bpy.data.objects)
        if not name_exists:
            break
        num += 1
    joined_name = f"{prefix}_{name}_{num:02}"
    return joined_name

def spawn_collision(context, self, operator, prefix="UBX", pass_context=False):
    ct_props = context.scene.ct_properties
    c, multiple, selection = prepare_to_iterate_over_selection(context, self, force_multiple=True)
    collision_set = []
    for obj in c:
        if check_if_collision(obj):
            self.report({'WARNING'}, f"Collision objects selected. {obj.name} is skipped")
            continue
        bounds = source_local_bounds(obj) if ct_props.try_to_fit_simple_collision else None
        if bounds and prefix == "UCP":
            apply_capsule_fit(ct_props, bounds)
        if context and self and pass_context:
            operator(context=context, self=self)        
        else :
            operator()
        box = context.view_layer.objects.active
        box.name = find_available_collision_name(obj.name, prefix)
        if bounds:
            fit_transforms_and_parent(obj, box, prefix, bounds)
        else:
            copy_transforms_and_parent(obj, box)
        set_display(box, context)
        collision_set.append(box)
    set_selection(collision_set)
    
   
def spawn_box_collision(context, self):
    spawn_collision(context, self, bpy.ops.mesh.primitive_cube_add, prefix="UBX") 

def spawn_sphere_collision(context, self):
    spawn_collision(context, self, simple_sphere, prefix="USP")
    
def spawn_capsule_collision(context, self):
    spawn_collision(context, self, add_capsule_collision, prefix="UCP", pass_context=True)

def add_capsule_collision(context, self):
    ct_props = context.scene.ct_properties
    caps, aya = spawn_capsule(name="UCX_Capsule_01", radius=ct_props.capsule_radius, height=ct_props.capsule_height, location=(0, 0, 0), segments=16, rings=8, context=context)
    context.view_layer.objects.active = caps
    return caps
def set_selection(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
        
def simple_sphere():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8)
    
def check_if_collision(obj):
    return obj.type == 'MESH' and obj.name.startswith(COLLISION_PREFIXES)

def collision_prefix(obj):
    """Collision prefix of obj without its trailing underscore, or None."""
    for p in COLLISION_PREFIXES:
        if obj.name.startswith(p):
            return p[:-1]
    return None

def name_matches_parent(obj, parent):
    """True when obj is already named after parent, so it binds to it in Unreal."""
    prefix = collision_prefix(obj)
    return prefix is not None and obj.name.startswith(f"{prefix}_{parent.name}_")


def spawn_capsule(name="Capsule", radius=0.25, height=1.0, location=(0, 0, 0), segments=32, rings=16, context=None):
    """
    Capsule total height = height
    Cylinder height = max(height - 2*radius, 0)
    """
    loc = Vector(location)
    cyl_h = max(height - 2.0 * radius, 0.0)

    # Ensure Object Mode
    if context and context.object and context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    source_obj = context.active_object if context.active_object in context.selected_objects else context.selected_objects[0]
    bpy.ops.object.select_all(action='DESELECT')

    created = []

    # Cylinder (if any)
    if cyl_h > 0.0:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=segments,
            radius=radius,
            depth=cyl_h,
            location=loc
        )
        cyl = bpy.context.active_object
        cyl.name = name + "_Cyl"
        created.append(cyl)
        pruned_ngon(cyl)

        top_z = loc.z + cyl_h / 2.0
        bot_z = loc.z - cyl_h / 2.0
    else:
        # Degenerates to a sphere if height <= 2*radius
        top_z = bot_z = loc.z

    # Top sphere
    top_sphere =bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=radius,
        location=(loc.x, loc.y, top_z)
    )
    top = bpy.context.active_object
    top.name = name + "_Top"
    created.append(top)
    delete_half(top, axis="Z", above=False)

    # Bottom sphere
    bot_sphere = bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=radius,
        location=(loc.x, loc.y, bot_z)
    )
    bot = bpy.context.active_object
    bot.name = name + "_Bot"
    created.append(bot)
    delete_half(bot, axis="Z", above=True)

    # Join into one object
    for o in created:
        o.select_set(True)
    context.view_layer.objects.active = created[0]
    bpy.ops.object.join()

    capsule = context.active_object
    capsule.name = name
    bm = bmesh.new()
    bm.from_mesh(capsule.data)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(capsule.data)
    bm.free()

    return capsule, source_obj


def view_cut_plane(region, rv3d, start, end):
    """World space (point, normal) of the plane through a screen line and the view.

    The plane contains the view rays cast through both ends of the drawn line, so the
    cut is whatever you see yourself drawing, from any orbit angle.
    """
    o1 = region_2d_to_origin_3d(region, rv3d, start)
    d1 = region_2d_to_vector_3d(region, rv3d, start)
    o2 = region_2d_to_origin_3d(region, rv3d, end)
    d2 = region_2d_to_vector_3d(region, rv3d, end)
    n = d1.cross(d2)
    if n.length < 1e-6:          # orthographic view: the two rays are parallel
        n = d1.cross(o2 - o1)
    if n.length < 1e-6:
        return None
    return o1, n.normalized()

def world_plane_to_local(obj, co, normal):
    mw_inv = obj.matrix_world.inverted_safe()
    return mw_inv @ co, (mw_inv.to_3x3().transposed() @ normal).normalized()

def source_bmesh(obj, context):
    """bmesh of obj's evaluated geometry, in object local space."""
    depsgraph = context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
    finally:
        obj_eval.to_mesh_clear()
    return bm

def clip_bmesh(bm, co, normal, dist=1e-6):
    """Drop the part of bm on the positive side of the plane, in place.

    bisect_plane creates the vertices where the plane crosses the geometry, so the
    hull of what is left meets the neighbouring piece exactly on the cut.
    """
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=dist, plane_co=co, plane_no=normal, clear_outer=True)
    return bm

def split_slice_regions(regions, co, normal):
    """Split every region whose geometry the plane actually crosses.

    A region is a dict of the planes bounding it, the clipped source geometry cached as
    a bmesh, and the collision object showing it. Returns (regions, retired), where
    retired holds the objects of replaced regions for the caller to remove.
    """
    out, retired = [], []
    for region in regions:
        inner = clip_bmesh(region["bm"].copy(), co, normal)
        outer = clip_bmesh(region["bm"].copy(), co, -normal)
        if len(inner.verts) < 4 or len(outer.verts) < 4:
            inner.free()
            outer.free()
            out.append(region)
            continue
        # ponytail: regions are cached per piece, so a cut only re-clips what it crosses.
        # A rebuild from the full source each time would be 2**cuts clips instead.
        region["bm"].free()
        if region["obj"] is not None:
            retired.append(region["obj"])
        out.append({"planes": region["planes"] + [(co, normal)], "bm": inner, "obj": None})
        out.append({"planes": region["planes"] + [(co, -normal)], "bm": outer, "obj": None})
    return out, retired

def budget_collision_faces(col_obj, target_face_count):
    """Live decimate so a piece respects the panel's face budget.

    Left unbaked on purpose: both exporters apply modifiers, so Unreal gets the budgeted
    mesh while the piece stays re-editable here. Re-callable: it retunes the modifier it
    already added and drops it once the budget covers the mesh outright.
    """
    face_count = len(col_obj.data.polygons)
    dec = next((m for m in col_obj.modifiers if m.type == 'DECIMATE'), None)
    if face_count <= target_face_count:
        if dec:
            col_obj.modifiers.remove(dec)
        return
    if dec is None:
        dec = col_obj.modifiers.new(name="Decimate", type='DECIMATE')
    dec.decimate_type = 'COLLAPSE'
    dec.ratio = clamp(target_face_count / face_count)
    dec.use_collapse_triangulate = True

def slice_collision_piece(bm, source_obj, context):
    """Convex collision object for one sliced region, or None if it is degenerate."""
    ct_props = context.scene.ct_properties
    mesh = build_convex_hull_mesh_from_points(
        [v.co.copy() for v in bm.verts], name=f"{source_obj.name}_SLICE_MESH"
    )
    if mesh is None:
        return None
    col_obj = create_collision_object(
        source_obj,
        mesh,
        find_available_collision_name(source_obj.name, prefix="UCX"),
        context=context,
    )
    col_obj.matrix_world = source_obj.matrix_world.copy()
    col_obj.parent = source_obj
    col_obj.matrix_parent_inverse = source_obj.matrix_world.inverted_safe()
    col_obj[SLICE_TAG] = True
    budget_collision_faces(col_obj, ct_props.target_face_count)
    return col_obj

def get_slice_pieces(source_obj):
    """Collision children this tool generated, never hand made ones."""
    return [c for c in source_obj.children if SLICE_TAG in c and check_if_collision(c)]

def get_selected_verts(obj, space="LOCAL"):
    """Vertices selected in the mesh currently being edited."""
    bm = bmesh.from_edit_mesh(obj.data)
    verts = [v.co.copy() for v in bm.verts if v.select]
    if space == "WORLD":
        mw = obj.matrix_world
        return [mw @ v for v in verts]
    return verts

def delete_half(obj,axis="Z", above=True):

    bm = bmesh.new()
    bm.from_mesh(obj.data)

    verts_to_delete = []

    for v in bm.verts:
        match axis:
            case "X":
                if v.co.x > 0 if above else v.co.x < 0:
                    verts_to_delete.append(v)
            case "Y":
                if v.co.y > 0 if above else v.co.y < 0:
                    verts_to_delete.append(v)
            case "Z":
                if v.co.z > 0 if above else v.co.z < 0:
                    verts_to_delete.append(v)

    # Delete them properly
    bmesh.ops.delete(bm, geom=verts_to_delete, context='VERTS')
            
    bm.to_mesh(obj.data)
    bm.free()

def pruned_ngon(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    face_to_delete = []
    for f in bm.faces:
        if len(f.verts) > 4: 
            face_to_delete.append(f)
    bmesh.ops.delete(bm, geom=face_to_delete, context='FACES')
            
    bm.to_mesh(obj.data)
    bm.free()

# Update functions for properties

def update_collision_object_display(self, context):
    collision_meshes = get_collision_objects()
    for obj in collision_meshes:
        set_display(obj, context)

def update_color_display(self, context):
    ct_props = context.scene.ct_properties
    mat = bpy.data.materials.get("M_CT_Collision_Mat")
    if mat:
        setup_collision_material(mat, ct_props.mat_color)
        
def update_radius(self, context):
    ct_props = context.scene.ct_properties
    if ct_props.capsule_radius > ct_props.capsule_height / 2.0:
        ct_props.capsule_height = ct_props.capsule_radius * 2.0
        
def update_height(self, context):
    ct_props = context.scene.ct_properties
    if ct_props.capsule_height < ct_props.capsule_radius * 2.0:
        ct_props.capsule_radius = ct_props.capsule_height / 2.0

def update_socket_display(self, context):
    ct_props = context.scene.ct_properties
    for obj in bpy.data.objects:
        if obj.name.startswith("SOCKET_") and obj.type == 'EMPTY':
            set_display_socket(obj, context)

def method_object_not_collision(context):
    selection = context.selected_objects
    value = True
    if not selection:
        return False
    for obj in selection:
        if check_if_collision(obj) or obj.type != 'MESH' or obj.name.startswith("SOCKET_") or context.mode != 'OBJECT':
            value = False
            break
    return value

def method_is_capsule(context):
    selection = context.selected_objects
    value = True
    if not selection:
        return False
    for obj in selection:
        if not obj.name.startswith("UCP_"):
            value = False
            break
    return value
