import bpy
from bpy.props import (BoolProperty, FloatVectorProperty, EnumProperty, PointerProperty, IntProperty, StringProperty, FloatProperty)
from bpy.types import PropertyGroup

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
    wire_display: bpy.props.BoolProperty(
        name="Wire Display",
        default=True,
        description="Display collision object as wire and in front",
    )
    convex_options: bpy.props.BoolProperty(
        name="Show Convex Hull Options",
        default=False,
        description="Show additional options for convex hull generation",
    )

    ###Kdop properties###
    kdop_options: bpy.props.BoolProperty(
        name="Show k-DOP Options",
        default=False,
        description="Show additional options for k-DOP generation",
    )
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
    kdop_space: bpy.props.EnumProperty(
        name="Axis Space",
        items=[
            ("LOCAL", "Local", "Use the object's local axes"),
            ("WORLD", "World", "Use world axes"),
        ],
        default="WORLD",
    )
    kdop_use_evaluated_mesh: bpy.props.BoolProperty(
        name="Use Evaluated Mesh (Modifiers)",
        default=True,
        description="Use mesh after modifiers (recommended)",
    )
    kdop_inside_epsilon: bpy.props.FloatProperty(
        name="Inside Epsilon",
        default=1e-6,
        min=1e-9,
        max=1e-2,
        description="Tolerance for inside test",
    )
    kdop_name_prefix: bpy.props.StringProperty(
        name="Name Prefix",
        default="UCX_",
        description="Prefix for collision object name (Unreal convention is UCX_)",
    )
    kdop_parent_to_source: bpy.props.BoolProperty(
        name="Parent To Source",
        default=True,
        description="Parent collision object to the source object",
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