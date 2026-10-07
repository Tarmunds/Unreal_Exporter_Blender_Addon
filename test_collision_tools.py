"""Self-check for the collision tools. Run it with:

    blender --background --python test_collision_tools.py

Asserts the pieces that are easy to break: primitive auto fit, rebinding a
collision onto another asset, the collision material replacement, and hull
generation from an Edit Mode selection.
"""

import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ROOT))
addon = __import__(os.path.basename(ROOT))
addon.register()

from Unreal_Exporter_Blender_Addon.CT.Functions import (  # noqa: E402
    collision_prefix,
    collision_tools_enabled,
    name_matches_parent,
    set_display,
)

EPS = 1e-4
props = bpy.context.scene.ct_properties


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

# --- wrong materials on a collision mesh are replaced, not kept
junk = bpy.data.materials.new("Junk")
ubx.data.materials.clear()
ubx.data.materials.append(junk)
ubx.data.materials.append(junk)
set_display(ubx, bpy.context)
assert len(ubx.data.materials) == 1, len(ubx.data.materials)
assert ubx.data.materials[0].name == "M_CT_Collision_Mat", ubx.data.materials[0].name

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

# --- panel visibility toggle resolves without an enabled addon entry
assert collision_tools_enabled(bpy.context) in (True, False)

print("collision tools self-check: OK")
