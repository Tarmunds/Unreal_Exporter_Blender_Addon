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

        # Path field
        col.prop(context.scene, "mesh_rename_path", text="Path")

        # Proper spacing
        col.separator()

        # Dropdown menu logic
        if not context.scene.path_dropdown:
            # Dropdown closed, no box
            row = col.row()
            icon = 'TRIA_RIGHT'
            row.prop(context.scene, "path_dropdown", icon=icon, text="Path Options", emboss=False, toggle=True)
        else:
            # Dropdown open, everything inside a box
            box = col.box()
            row = box.row()
            icon = 'TRIA_DOWN'
            row.prop(context.scene, "path_dropdown", icon=icon, text="Path Options", emboss=False, toggle=True)

            # Expanded path options
            row = box.row()
            row.operator("export.add_path", text="Save Path")
            row = box.row()
            row.prop(context.scene, "saved_path_enum", text="Saved Paths")
            row.operator("export.select_saved_path", text="Use Path")

        # Proper spacing
        col.separator()

        # Include location toggle
        col.prop(context.scene, "include_transform", text="Include Location")

        # Proper spacing
        col.separator()

        # Export buttons
        col.operator("export.selected_objects", text="Export Selected Objects")
        col.operator("export.parented_objects", text="Export Each Hierarchy")
