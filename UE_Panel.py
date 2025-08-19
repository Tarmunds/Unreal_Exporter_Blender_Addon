import bpy
import os
from bpy.types import Panel

class UnrealExport_ExportPanel(Panel):
    bl_idname = "VIEW3D_PT_export_unreal"
    bl_label = "Unreal Exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarmunds Addons'

    def draw(self, context):
        layout = self.layout
        # Path field
        row = layout.row()
        row.scale_y = 1.5
        row.prop(context.scene, "mesh_rename_path", text="Path")

        # Proper spacing
        col = self.layout.column(align=True)
        col.separator()
        # Dropdown menu logic
        if not context.scene.path_dropdown:
            # Dropdown closed, no box
            box = col.box()
            row = box.row()
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

       
        col = self.layout.column(align=True)
        
        #---Unity and more Options---
        
        if not context.scene.MoreOptions:
            # Dropdown closed, no box
            box = col.box()
            row = box.row()
            icon = 'TRIA_RIGHT'
            row.prop(context.scene, "MoreOptions", icon=icon, text="More Options", emboss=False, toggle=True)
        else:
            # Dropdown open, everything inside a box
            box = col.box()
            row = box.row()
            icon = 'TRIA_DOWN'
            row.prop(context.scene, "MoreOptions", icon=icon, text="More Options", emboss=False, toggle=True)

            row = box.row()
            row.prop(context.scene, "Yup", text="Y-Up")
            row.prop(context.scene, "JoinAll", text="Join Meshes at Export")
            row = box.row()
            row.prop(context.scene, "include_transform", text="Include Location")
            row.prop(context.scene, "IncludeCurve", text="Include Curve Geometry")

        # Export buttons
        row = layout.row()
        row.scale_y = 1.5
        row.operator("export.selected_objects", text="Export Selected Objects", icon='STICKY_UVS_DISABLE')
        row = layout.row()
        row.scale_y = 1.5
        row.operator("export.parented_objects", text="Export Each Hierarchy", icon='STICKY_UVS_LOC')
