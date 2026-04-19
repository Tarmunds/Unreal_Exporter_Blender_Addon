import bpy
from bpy.props import (BoolProperty, FloatVectorProperty, EnumProperty, PointerProperty, IntProperty, StringProperty, FloatProperty)
from bpy.types import PropertyGroup
from .Functions import update_collision_object_display, update_color_display, update_selectable, update_radius, update_height, update_socket_display

class CT_Properties(PropertyGroup):
    target_face_count: IntProperty(
        name="Target Face Count",
        description="Target number of faces for the generated collision mesh. Higher values result in more detailed collision meshes.",
        default=25,
        min=4,
        max=75,
    )
    bake_simplification: BoolProperty(
        name="Bake Simplification",
        description="Bake simplification to the generated collision mesh. This can help reduce the number of faces and improve performance, but may result in less accurate collision.",
        default=True,
    )
    wire_display: BoolProperty(
        name="Wire Display",
        default=True,
        description="Display collision object as wire and in front",
        update=update_collision_object_display,
    )
    color_display: BoolProperty(
        name="Color Display",
        default=False,
        description="Display collision object with a color overlay",
        update=update_collision_object_display,
    )
    mat_color: FloatVectorProperty(
        name="Collision Color",
        subtype='COLOR',
        size=4,
        default=(0.31, 0.258, 1.0, 0.278),
        min=0.0,
        max=1.0,
        description="Color for collision objects when Color Display is enabled",
        update=update_color_display,
    )
    selectable: BoolProperty(
        name="Selectable",
        default=True,
        description="Allow selection of collision objects in the viewport",
        update=update_selectable,
    )
    convex_options: BoolProperty(
        name="Show Convex Hull Options",
        default=False,
        description="Show additional options for convex hull generation",
    )
    advanced_options: BoolProperty(
        name="Show Advanced Options",
        default=False,
        description="Show advanced options for collision generation (use with caution)",
    )
    convex_parent: BoolProperty(
        name="Parent To Source",
        default=True,
        description="Parent generated convex hull to the source object",
    )
    visibility_button_field: EnumProperty(
        name="Visibility Button Field",
        items=[
            ("All_MESH", "All Mesh", "Toggle visibility for collision on all mesh objects"),
            ("CURRENT_HIERARCHY", "Current Hierarchy", "Toggle visibility for collision on the current selected hierarchy"),
        ],
        default="All_MESH",
    )
    multiple_selection_behavior: EnumProperty(
        name="Multiple Selection Behavior",
        items=[
            ("ONE_COLLISION", "One Collision", "Generate one collision mesh for the entire selection"),
            ("MULTIPLE_COLLISIONS", "Multiple Collisions", "Generate separate collision meshes for each selected object"),
        ],
        default="ONE_COLLISION",
    )
    try_to_fit_simple_collision: BoolProperty(
        name="Try To Fit Simple Collision",
        default=False,
        description="Try to fit simple collision primitives (box, sphere, capsule) to the selected object before generating a convex hull. This can result in better performance and simpler collision meshes for objects that are well-suited to simple primitives.",
    )
    
    capsule_radius: FloatProperty(
        name="Capsule Radius",
        default=0.5,
        min=0.01,
        soft_max=3.0,
        description="Radius of the capsule collision primitive",
        update=update_radius,
    )
    capsule_height: FloatProperty(
        name="Capsule Height",
        default=2.0,
        min=0.01,
        soft_max=6.0,
        description="Height of the capsule collision primitive (including the hemispherical ends)",
        update=update_height,
    )

    ###Kdop properties###
    kdop_options: BoolProperty(
        name="Show k-DOP Options",
        default=False,
        description="Show additional options for k-DOP generation",
    )
    kdop_mode: EnumProperty(
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
        default="DOP14",
    )
    kdop_space: EnumProperty(
        name="Axis Space",
        items=[
            ("LOCAL", "Local", "Use the object's local axes"),
            ("WORLD", "World", "Use world axes"),
        ],
        default="WORLD",
    )
    kdop_use_evaluated_mesh: BoolProperty(
        name="Use Evaluated Mesh (Modifiers)",
        default=True,
        description="Use mesh after modifiers (recommended)",
    )
    kdop_inside_epsilon: FloatProperty(
        name="Inside Epsilon",
        default=1e-6,
        min=1e-9,
        max=1e-2,
        description="Tolerance for inside test",
    )
    kdop_name_prefix: StringProperty(
        name="Name Prefix",
        default="UCX_",
        description="Prefix for collision object name (Unreal convention is UCX_)",
    )
    kdop_parent_to_source: BoolProperty(
        name="Parent To Source",
        default=True,
        description="Parent collision object to the source object",
    )

    #socket visibility
    socket_name: BoolProperty(
        name="Socket Name Display",
        default=True,
        description="Display socket names in the viewport",
        update=update_socket_display,
    )
    socket_in_front: BoolProperty(
        name="Socket In Front",
        default=True,
        description="Display sockets in front of other objects in the viewport",
        update=update_socket_display,
    )
    selectable_socket: BoolProperty(
        name="Selectable Sockets",
        default=True,
        description="Allow selection of sockets in the viewport",
        update=update_socket_display,
    )
    socket_at_cursor: BoolProperty(
        name="Socket at Cursor",
        default=False,
        description="When enabled, new sockets will be created at the 3D cursor location instead of the origin of the parent object",
    )
    socket_options: BoolProperty(
        name="Show Socket Options",
        default=False,
        description="Show additional options for socket display",
    )

    
_classes = (
    CT_Properties,
    )

def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ct_properties = PointerProperty(type=CT_Properties)


def unregister():
    del bpy.types.Scene.ct_properties
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)