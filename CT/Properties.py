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