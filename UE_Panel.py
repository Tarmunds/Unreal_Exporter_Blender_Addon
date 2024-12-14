import bpy
import os
from bpy.types import Panel

class UnrealExport_ExportPanel(Panel):
    bl_idname = "VIEW3D_PT_export_unreal"
    bl_label = "Export Unreal"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarmunds Addons'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        
        col.prop(context.scene, "mesh_rename_path", text="Path")
        
        box = col.box()
        box.prop(context.scene, "path_dropdown", icon="TRIA_DOWN", text="Path Options", emboss=False)
        if context.scene.path_dropdown:
            row = box.row()
            row.operator("export.add_path", text="Save Path")
            row = box.row()
            row.prop(context.scene, "saved_path_enum", text="Saved Paths")
            row.operator("export.select_saved_path", text="Use Path")
        
        col.prop(context.scene, "include_transform", text="Include Location")
        col.operator("export.selected_objects", text="Export Selected Objects")
        col.operator("export.parented_objects", text="Export Each Hierarchy")

