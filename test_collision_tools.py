"""Self-check for the collision tools. Run it with:

    blender --background --python test_collision_tools.py

Asserts the pieces that are easy to break: primitive auto fit, rebinding a
collision onto another asset, the collision material replacement, and hull
generation from an Edit Mode selection.
"""

import os
import sys

import bmesh
import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ROOT))
addon = __import__(os.path.basename(ROOT))
addon.register()

from Unreal_Exporter_Blender_Addon.CT.Functions import (  # noqa: E402
    budget_collision_faces,
    collision_prefix,
    collision_tools_enabled,
    get_slice_pieces,
    name_matches_parent,
    set_display,
    setup_collision_material,
    slice_collision_piece,
    source_bmesh,
    split_slice_regions,
    world_plane_to_local,
)

EPS = 1e-4
props = bpy.context.scene.ct_properties


def approx(a, b, eps=1e-5):
    return len(a) == len(b) and all(abs(x - y) < eps for x, y in zip(a, b))


def bounds_in(obj, ref):
    """obj's vertex bounds expressed in ref's local space."""
    m = ref.matrix_world.inverted_safe() @ obj.matrix_world
    pts = [m @ Vector(v.co) for v in obj.data.vertices]
    return (
        Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
        Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))),
    )


def new_mesh(name, location, scale, offset=(0.0, 0.0, 0.0)):
    """Cube with its scale applied and its geometry pushed off the origin."""
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for v in obj.data.vertices:
        v.co += Vector(offset)
    obj.rotation_euler = (0.3, 0.0, 0.7)
    bpy.context.view_layer.update()
    return obj


def only(objects, active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active or (objects[0] if objects else None)


def named(prefix):
    return next(o for o in bpy.data.objects if o.name.startswith(prefix))


# Local size (2, 4, 1), geometry centred on (0, 0, 5), rotated object.
table = new_mesh("Table", (3.0, 0.0, 0.0), (1.0, 2.0, 0.5), offset=(0.0, 0.0, 5.0))
src_min, src_max = bounds_in(table, table)

# --- auto fit: box lands exactly on the source bounds, offset included
props.try_to_fit_simple_collision = True
only([table])
bpy.ops.ct.add_collision_to_selected(volume_type="BOX")
ubx = named("UBX_Table")
box_min, box_max = bounds_in(ubx, table)
assert (box_min - src_min).length < EPS, (box_min, src_min)
assert (box_max - src_max).length < EPS, (box_max, src_max)
assert ubx.parent is table

# --- auto fit: sphere encloses the source bounds
only([table])
bpy.ops.ct.add_collision_to_selected(volume_type="SPHERE")
sph_min, sph_max = bounds_in(named("USP_Table"), table)
assert all(sph_min[i] <= src_min[i] + EPS for i in range(3)), (sph_min, src_min)
assert all(sph_max[i] >= src_max[i] - EPS for i in range(3)), (sph_max, src_max)

# --- auto fit: capsule properties follow the bounds, radius/height stay valid
only([table])
bpy.ops.ct.add_collision_to_selected(volume_type="CAPSULE")
assert abs(props.capsule_radius - 2.0) < EPS, props.capsule_radius      # max(2, 4) / 2
assert abs(props.capsule_height - 4.0) < EPS, props.capsule_height      # clamped up to 2 * radius
cap_min, cap_max = bounds_in(named("UCP_Table"), table)
assert abs((cap_max.z - cap_min.z) - 4.0) < 1e-2, (cap_min, cap_max)

# --- auto fit off: primitive keeps its default size at the source origin
props.try_to_fit_simple_collision = False
only([table])
bpy.ops.ct.add_collision_to_selected(volume_type="BOX")
plain = [o for o in bpy.data.objects if o.name.startswith("UBX_Table")][-1]
assert abs(plain.dimensions.x - 2.0) < EPS, plain.dimensions

# --- a plain mesh child still converts against its own parent
blob = new_mesh("Blob", (3.0, 0.0, 0.0), (1.0, 1.0, 1.0))
blob.parent = table
only([blob], active=blob)
bpy.ops.ct.convert_to_ucx()
assert blob.name == "UCX_Table_01", blob.name
assert name_matches_parent(blob, table)

# --- rebind: active mesh takes over the selected collisions, prefix preserved
chair = new_mesh("Chair", (-3.0, 0.0, 0.0), (1.0, 1.0, 1.0))
only([ubx, blob, chair], active=chair)
bpy.ops.ct.convert_to_ucx()
assert ubx.parent is chair and ubx.name == "UBX_Chair_01", (ubx.name, ubx.parent)
assert blob.parent is chair and blob.name == "UCX_Chair_01", (blob.name, blob.parent)
assert collision_prefix(ubx) == "UBX"

# --- rebinding twice is a no-op, not an endless _02 _03 rename
before = ubx.name
bpy.ops.ct.convert_to_ucx()
assert ubx.name == before, (ubx.name, before)

# --- collision arriving from Unreal with its own materials: every slot is replaced and
# the collision material is set up for solid, material preview and rendered alike
for name in ("UE_WeirdMat_A", "UE_WeirdMat_B", "UE_WeirdMat_C"):
    ubx.data.materials.append(bpy.data.materials.new(name))
for i, poly in enumerate(ubx.data.polygons):
    poly.material_index = i % len(ubx.data.materials)
props.color_display = True
set_display(ubx, bpy.context)
assert len(ubx.data.materials) == 1, len(ubx.data.materials)
collision_mat = ubx.data.materials[0]
assert collision_mat.name == "M_CT_Collision_Mat", collision_mat.name
assert all(p.material_index == 0 for p in ubx.data.polygons)
assert approx(collision_mat.diffuse_color, props.mat_color)
assert collision_mat.surface_render_method == 'BLENDED', collision_mat.surface_render_method
principled = next(n for n in collision_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
assert approx(tuple(principled.inputs["Base Color"].default_value)[:3], tuple(props.mat_color)[:3])
assert abs(principled.inputs["Alpha"].default_value - props.mat_color[3]) < 1e-6

# the colour picker keeps the nodes in step, not just the solid mode colour
props.mat_color = (0.9, 0.1, 0.2, 0.5)
assert approx(tuple(principled.inputs["Base Color"].default_value)[:3], (0.9, 0.1, 0.2))
assert abs(principled.inputs["Alpha"].default_value - 0.5) < 1e-6

# turning colour off whitens both, so no shading mode is left tinted
props.color_display = False
assert approx(collision_mat.diffuse_color, (1.0, 1.0, 1.0, 1.0))
assert abs(principled.inputs["Alpha"].default_value - 1.0) < 1e-6
props.color_display = True

# --- hull from an Edit Mode selection
for hull, prefix in (("CONVEX", "UCX_Table"), ("KDOP", "UCX_Table")):
    only([table], active=table)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    count = len(bpy.data.objects)
    bpy.ops.ct.collision_from_selection(hull_type=hull)
    bpy.ops.object.mode_set(mode='OBJECT')
    assert len(bpy.data.objects) == count + 1, hull
    hull_obj = [o for o in bpy.data.objects if o.name.startswith(prefix)][-1]
    assert hull_obj.parent is table, (hull, hull_obj.parent)
    assert len(hull_obj.data.vertices) >= 4, (hull, len(hull_obj.data.vertices))
    hmin, hmax = bounds_in(hull_obj, table)
    assert all(hmin[i] <= src_min[i] + 1e-2 for i in range(3)), (hull, hmin, src_min)
    assert all(hmax[i] >= src_max[i] - 1e-2 for i in range(3)), (hull, hmax, src_max)

# --- slicer: the geometry half of the modal, driven with explicit planes
# (the drag itself needs a viewport region, which --background has none of)
def slice_session(source, planes):
    regions = [{"planes": [], "bm": source_bmesh(source, bpy.context), "obj": None}]
    for region in regions:
        region["obj"] = slice_collision_piece(region["bm"], source, bpy.context)
    for co, normal in planes:
        regions, retired = split_slice_regions(regions, co, normal)
        for obj in retired:
            bpy.data.objects.remove(obj, do_unlink=True)
        for region in regions:
            if region["obj"] is None:
                region["obj"] = slice_collision_piece(region["bm"], source, bpy.context)
    for region in regions:
        region["bm"].free()
    return [r["obj"] for r in regions if r["obj"] is not None]

# L shaped source: a 4x4x1 slab with a 2x4x3 upright on its -X end
bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 0.0))
ell = bpy.context.active_object
ell.name = "Ell"
for v in ell.data.vertices:
    v.co = Vector((v.co.x * 2.0, v.co.y * 2.0, v.co.z * 0.5 - 0.5))
upright = bpy.data.meshes.new("up")
bm_pts = [Vector((x, y, z)) for x in (-2.0, -1.0) for y in (-2.0, 2.0) for z in (-1.0, 2.0)]
upright.from_pydata([tuple(p) for p in bm_pts], [], [])
helper = bpy.data.objects.new("UpHelper", upright)
bpy.context.collection.objects.link(helper)
only([helper, ell], active=ell)
bpy.ops.object.join()
ell = bpy.context.active_object
ell.rotation_euler = (0.0, 0.0, 0.4)
ell.location = (1.0, -2.0, 0.5)
bpy.context.view_layer.update()

def mesh_volume(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    volume = bm.calc_volume(signed=False)
    bm.free()
    return volume


def drop(objects):
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)


props.target_face_count = 75     # keep the budget out of the volume numbers

# a cut through solid geometry: both pieces must reach the plane, or collision leaks
plane_x = -1.0
co, normal = world_plane_to_local(
    ell,
    ell.matrix_world @ Vector((plane_x, 0.0, 0.0)),
    (ell.matrix_world.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized(),
)
pieces = slice_session(ell, [(co, normal)])
assert len(pieces) == 2, [p.name for p in pieces]
assert all(p.parent is ell for p in pieces)
assert all(p.name.startswith("UCX_Ell_") for p in pieces), [p.name for p in pieces]
assert set(get_slice_pieces(ell)) == set(pieces)
for piece in pieces:
    at_plane = [
        (ell.matrix_world.inverted_safe() @ (piece.matrix_world @ Vector(v.co))).x
        for v in piece.data.vertices
    ]
    assert min(abs(x - plane_x) for x in at_plane) < 1e-4, (piece.name, at_plane)
drop(pieces)

# undo inside the session: snapshot taken before a cut restores the earlier pieces
# exactly, bmeshes included, without re-slicing the source
regions = [{"planes": [], "bm": source_bmesh(ell, bpy.context), "obj": None}]
regions[0]["obj"] = slice_collision_piece(regions[0]["bm"], ell, bpy.context)
history = [[{"planes": list(r["planes"]), "bm": r["bm"].copy()} for r in regions]]
regions, retired = split_slice_regions(regions, co, normal)
drop(retired)
for region in regions:
    if region["obj"] is None:
        region["obj"] = slice_collision_piece(region["bm"], ell, bpy.context)
assert len(regions) == 2, len(regions)

drop([r["obj"] for r in regions if r["obj"] is not None])
for region in regions:
    region["bm"].free()
regions = [{"planes": r["planes"], "bm": r["bm"], "obj": None} for r in history.pop()]
for region in regions:
    region["obj"] = slice_collision_piece(region["bm"], ell, bpy.context)
assert len(regions) == 1, len(regions)
assert regions[0]["planes"] == []
undone = [r["obj"] for r in regions if r["obj"] is not None]
assert len(undone) == 1 and undone[0].parent is ell
for region in regions:
    region["bm"].free()
drop(undone)

# a plane that misses the asset splits nothing
far = slice_session(ell, [(Vector((50.0, 0.0, 0.0)), Vector((1.0, 0.0, 0.0)))])
assert len(far) == 1, len(far)
drop(far)

# tightness: two blocks with a gap. One hull bridges the gap, slicing through it
# rebuilds each piece from the geometry inside it and gives back the empty space.
verts = [
    (x, y, z)
    for bx in (-3.0, 1.0)
    for x in (bx, bx + 2.0)
    for y in (-1.0, 1.0)
    for z in (-1.0, 1.0)
]
pair_mesh = bpy.data.meshes.new("pair")
pair_mesh.from_pydata(verts, [], [])
pair = bpy.data.objects.new("Pair", pair_mesh)
bpy.context.collection.objects.link(pair)
pair.rotation_euler = (0.2, 0.0, 0.9)
pair.location = (-4.0, 4.0, 1.0)
bpy.context.view_layer.update()

bridged = slice_session(pair, [])
assert len(bridged) == 1, len(bridged)
bridged_volume = mesh_volume(bridged[0])
drop(bridged)

split = slice_session(pair, [(Vector((0.0, 0.0, 0.0)), Vector((1.0, 0.0, 0.0)))])
assert len(split) == 2, [p.name for p in split]
split_volume = sum(mesh_volume(p) for p in split)
assert split_volume < bridged_volume * 0.8, (split_volume, bridged_volume)
drop(split)

# face budget rides along as a live modifier, so the exporters bake it
props.target_face_count = 6
budgeted = slice_session(ell, [(co, normal)])
assert any(m.type == 'DECIMATE' for p in budgeted for m in p.modifiers), "no decimate applied"
for piece in budgeted:
    evaluated = piece.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    assert len(mesh.polygons) <= 8, (piece.name, len(mesh.polygons))
    evaluated.to_mesh_clear()

drop(budgeted)

# retuning the budget live, as +/- does inside the modal: the modifier is reused, never
# stacked, and it goes away once the budget covers the mesh outright
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, location=(0.0, 0.0, 20.0))
probe = bpy.context.active_object
raw_faces = len(probe.data.polygons)
assert raw_faces > 40, raw_faces
for target in (10, 40, 8):
    budget_collision_faces(probe, target)
    decimates = [m for m in probe.modifiers if m.type == 'DECIMATE']
    assert len(decimates) == 1, (target, len(decimates))
    assert abs(decimates[0].ratio - target / raw_faces) < 1e-6, (target, decimates[0].ratio)
budget_collision_faces(probe, raw_faces + 1)
assert not [m for m in probe.modifiers if m.type == 'DECIMATE'], "decimate left behind"
drop([probe])

# --- the modal slicer registers; its drag/draw half needs an interactive viewport,
# which --background cannot provide, so only its geometry is covered above
assert hasattr(bpy.ops.ct, "slice_collision")

# --- panel visibility toggle resolves without an enabled addon entry
assert collision_tools_enabled(bpy.context) in (True, False)

print("collision tools self-check: OK")
