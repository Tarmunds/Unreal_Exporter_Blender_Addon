if "bpy" in locals():
    import importlib
    importlib.reload(UE_Panel)
    importlib.reload(UE_Exporter)

import bpy
import os
from . import UE_Panel
from . import UE_Exporter
from .UE_Exporter import update_saved_paths_enum



from bpy.types import Panel

bl_info = {
    "name": "Unreal Exporter",
    "author": "Tarmunds",
    "version": (3, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Tarmunds Addons > Export Unreal",
    "description": "Exports selected objects or hierarchies into separate files at the origin.",
    "doc_url": "https://tarmunds.gumroad.com/l/UnrealExporter",
    "tracker_url": "https://discord.gg/h39W5s5ZbQ",
    "category": "Import-Export",
}

classes = (
    UE_Exporter.UnrealExport_ExportSelectedObjectsOperator,
    UE_Exporter.UnrealExport_ExportParentedObjectsOperator,
    UE_Exporter.UnrealExport_AddPathOperator,
    UE_Exporter.UnrealExport_SelectSavedPathOperator,
    UE_Panel.UnrealExport_ExportPanel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.mesh_rename_path = bpy.props.StringProperty(
        name="Path",
        default="",
        maxlen=1024,
        subtype='DIR_PATH',
        update=lambda self, context: setattr(
            context.scene, "mesh_rename_path",
            bpy.path.abspath(context.scene.mesh_rename_path)
        )
    )


    bpy.types.Scene.export_format = bpy.props.EnumProperty(
        name="Format",
        description="Choose export format",
        items=[('FBX', 'FBX', 'Export as FBX file'),
               ('OBJ', 'OBJ', 'Export as OBJ file')],
        default='FBX'
    )
    bpy.types.Scene.include_transform = bpy.props.BoolProperty(
        name="Include Location",
        description="Include location in the export",
        default=False
    )
    bpy.types.Scene.saved_paths = bpy.props.CollectionProperty(
        type=bpy.types.PropertyGroup
    )
    bpy.types.Scene.saved_path_enum = bpy.props.EnumProperty(
        items=update_saved_paths_enum,
        name="Saved Path",
        description="Select a saved path",
    )
    bpy.types.Scene.path_dropdown = bpy.props.BoolProperty(
        name="Path Options",
        description="Toggle path options dropdown",
        default=False
    )


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.mesh_rename_path
    del bpy.types.Scene.export_format
    del bpy.types.Scene.include_transform
    del bpy.types.Scene.saved_paths
    del bpy.types.Scene.saved_path_enum
    del bpy.types.Scene.path_dropdown  # Ensure this is removed


if __name__ == "__main__":
    register()
