bl_info = {
    "name": "k-DOP Collision Hull Generator",
    "author": "Tarmunds",
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > KDOP",
    "description": "Generate k-DOP convex collision hull (6/10X/10Y/10Z/14/18/26) from selected mesh",
    "category": "Object",
}

import bpy
import bmesh
from mathutils import Vector, Matrix


# ------------------------------------------------------------
# Directions
# ------------------------------------------------------------

def _unit(v: Vector) -> Vector:
    l = v.length
    return v if l == 0.0 else (v / l)


def kdop_directions(mode: str):
    """
    Returns the "positive" direction set.
    For each direction u, we later create both +u and -u slab planes,
    so each direction contributes 2 planes.
    """
    if mode == "DOP6":
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
        ]

    elif mode == "DOP10_X":
        # 6 box planes + 4 bevel planes around X axis (bevel in YZ)
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((0, 1, 1)),
            Vector((0, 1, -1)),
        ]

    elif mode == "DOP10_Y":
        # 6 box planes + 4 bevel planes around Y axis (bevel in XZ)
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((1, 0, 1)),
            Vector((1, 0, -1)),
        ]

    elif mode == "DOP10_Z":
        # 6 box planes + 4 bevel planes around Z axis (bevel in XY)
        dirs = [
            Vector((1, 0, 0)),
            Vector((0, 1, 0)),
            Vector((0, 0, 1)),
            Vector((1, 1, 0)),
            Vector((1, -1, 0)),
        ]

    elif mode == "DOP14":
        # 3 axes + 4 body diagonals
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
        # 3 axes + 6 face diagonals
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
        # Union of 14 and 18 direction axes
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


# ------------------------------------------------------------
# Mesh sampling (evaluated mesh, local/world space)
# ------------------------------------------------------------

def get_object_vertices(obj: bpy.types.Object, use_evaluated_mesh: bool, space: str):
    """
    Returns vertices in either LOCAL or WORLD space.
    - LOCAL: mesh vertex coords as stored on the evaluated mesh
    - WORLD: transformed by obj.matrix_world
    """
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


# ------------------------------------------------------------
# Half-space construction and polyhedron vertex generation
# ------------------------------------------------------------

def build_kdop_planes(verts, dirs, dedupe_eps=1e-9):
    """
    Planes are stored as (n, d) for half-space:
        n.dot(x) <= d
    Each direction u creates two planes:
        +u with d = max(u·v)
        -u with d = -min(u·v)
    """
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

        planes.append((u.copy(), max_p))          # u·x <= max
        planes.append((-u.copy(), -min_p))        # (-u)·x <= -min

    # Optional dedupe (rare, but helps degenerate cases)
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
    """
    Solve:
        n1·x = d1
        n2·x = d2
        n3·x = d3
    Returns Vector or None if singular.
    """
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
    """
    Candidate vertices come from all 3-plane intersections.
    Keep those that satisfy all half-spaces.
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
    Create a mesh from the convex hull of the points using BMesh.
    """
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


def create_collision_object(source_obj, mesh, obj_name, display_wire=True, parent=True):
    col_obj = bpy.data.objects.new(obj_name, mesh)

    # Link to the same collections as the source object
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
        col_obj.display_type = "WIRE"
        col_obj.show_in_front = True

    return col_obj


# ------------------------------------------------------------
# Settings stored in Scene (so the panel can expose options)
# ------------------------------------------------------------

class KDOP_Settings(bpy.types.PropertyGroup):
    kdop_mode: bpy.props.EnumProperty(
        name="Collision Type",
        items=[
            ("DOP6", "Box Simplified Collision", "6 planes"),
            ("DOP10_X", "10DOP-X Simplified Collision", "Bevel in YZ, simplified over world/local X"),
            ("DOP10_Y", "10DOP-Y Simplified Collision", "Bevel in XZ, simplified over world/local Y"),
            ("DOP10_Z", "10DOP-Z Simplified Collision", "Bevel in XY, simplified over world/local Z"),
            ("DOP14", "14DOP Simplified Collision", "14 planes"),
            ("DOP18", "18DOP Simplified Collision", "18 planes"),
            ("DOP26", "26DOP Simplified Collision", "26 planes"),
        ],
        default="DOP26",
    )

    space: bpy.props.EnumProperty(
        name="Axis Space",
        items=[
            ("LOCAL", "Local", "Use the object's local axes"),
            ("WORLD", "World", "Use world axes"),
        ],
        default="WORLD",
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
        description="Tolerance for inside test",
    )

    name_prefix: bpy.props.StringProperty(
        name="Name Prefix",
        default="UCX_",
        description="Prefix for collision object name (Unreal convention is UCX_)",
    )

    parent_to_source: bpy.props.BoolProperty(
        name="Parent To Source",
        default=True,
        description="Parent collision object to the source object",
    )

    wire_display: bpy.props.BoolProperty(
        name="Wire Display",
        default=True,
        description="Display collision object as wire and in front",
    )


# ------------------------------------------------------------
# Operator
# ------------------------------------------------------------

class KDOP_OT_generate_collision(bpy.types.Operator):
    bl_idname = "object.kdop_generate_collision"
    bl_label = "Generate k-DOP Collision Hull"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, "Select an active mesh object")
            return {"CANCELLED"}

        s = context.scene.kdop_settings

        # Sample verts in requested space
        verts = get_object_vertices(obj, use_evaluated_mesh=s.use_evaluated_mesh, space=s.space)
        if not verts:
            self.report({"ERROR"}, "Object has no vertices")
            return {"CANCELLED"}

        dirs = kdop_directions(s.kdop_mode)
        planes = build_kdop_planes(verts, dirs)

        points = generate_kdop_points(planes, inside_eps=s.inside_epsilon)
        if len(points) < 4:
            self.report(
                {"ERROR"},
                f"Not enough hull points generated ({len(points)}). Try another DOP type or increase Inside Epsilon.",
            )
            return {"CANCELLED"}

        # If we computed in WORLD space, convert points back to LOCAL space so the hull mesh is local
        if s.space == "WORLD":
            inv = obj.matrix_world.inverted_safe()
            points = [inv @ p for p in points]

        hull_mesh = build_convex_hull_mesh_from_points(points, name=f"{obj.name}_{s.kdop_mode}_MESH")
        if hull_mesh is None:
            self.report({"ERROR"}, "Failed to build convex hull mesh")
            return {"CANCELLED"}

        col_name = f"{s.name_prefix}{obj.name}_{s.kdop_mode}"
        col_obj = create_collision_object(
            obj,
            hull_mesh,
            col_name,
            display_wire=s.wire_display,
            parent=s.parent_to_source,
        )

        # Select the created hull
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        col_obj.select_set(True)
        context.view_layer.objects.active = col_obj

        self.report(
            {"INFO"},
            f"Generated {s.kdop_mode} collision hull: {col_obj.name} (points: {len(points)}, planes: {len(planes)})",
        )
        return {"FINISHED"}


# ------------------------------------------------------------
# UI Panel
# ------------------------------------------------------------

class KDOP_PT_panel(bpy.types.Panel):
    bl_label = "k-DOP Collision"
    bl_idname = "KDOP_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'Tarmunds Addons'

    def draw(self, context):
        layout = self.layout
        s = context.scene.kdop_settings

        layout.prop(s, "kdop_mode")
        layout.prop(s, "space")
        layout.prop(s, "use_evaluated_mesh")
        layout.prop(s, "inside_epsilon")
        layout.separator()
        layout.prop(s, "name_prefix")
        layout.prop(s, "parent_to_source")
        layout.prop(s, "wire_display")
        layout.separator()
        layout.operator("object.kdop_generate_collision", text="Generate", icon="MESH_CUBE")


# ------------------------------------------------------------
# Register
# ------------------------------------------------------------

classes = (
    KDOP_Settings,
    KDOP_OT_generate_collision,
    KDOP_PT_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.kdop_settings = bpy.props.PointerProperty(type=KDOP_Settings)


def unregister():
    if hasattr(bpy.types.Scene, "kdop_settings"):
        del bpy.types.Scene.kdop_settings
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
