import bpy
from ..Utils.PanelUtils import *

class UEE_Panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_export_unreal"
    bl_label = "Unreal Exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarmunds Addons'

    def draw_header_preset(self, context):
        layout = self.layout
        layout.label(icon='EXPORT')
        #layout.prop(context.scene.uee_properties, "export_collision", text="Export Collision", toggle=True, icon='MESH_CUBE' if context.scene.uee_properties.export_collision else 'CANCEL')
        layout.label(text="")

    def draw(self, context):
        layout = self.layout
        uee_props = context.scene.uee_properties

        # Path field
        row = go_to_row(layout)
        row.prop(uee_props, "export_path", text="Path")

        box = dropdown_menu(layout, uee_props, "path_options", "Path Options", section_icon='FILE_FOLDER')
        if box:
            row = go_to_row(box)
            row.operator("export.add_path", text="Save Path")
            row = go_to_row(box)
            row.prop(uee_props, "saved_paths_enum", text="Saved Paths")
            row.operator("export.select_saved_path", text="Use Path")

        layout.separator(type='LINE')
        

        row = go_to_row(layout)
        row.prop(uee_props, "export_collision", text=f"Collision Export {'Enable' if uee_props.export_collision else 'Disable'}", toggle=True, icon='MESH_CUBE' if uee_props.export_collision else 'CANCEL')
        row.prop(uee_props, "export_sockets", text=f"Socket Export {'Enable' if uee_props.export_sockets else 'Disable'}", toggle=True, icon='EMPTY_DATA' if uee_props.export_sockets else 'CANCEL')
        # Export buttons
        row = go_to_row(layout, scale_y=2)
        row.operator("export.selected_objects", text="Export Selected Objects", icon='STICKY_UVS_DISABLE')
        row = go_to_row(layout, scale_y=2)
        row.operator("export.parented_objects", text="Export Each Hierarchy", icon='STICKY_UVS_LOC')
        if uee_props.enable_experimental_features:
            row = go_to_row(layout, scale_y=2)
            row.operator("export.export_rig", text="Export Rigged Asset / Animation", icon='ARMATURE_DATA')

        row = go_to_row(layout)
        #---Unity and more Options---
        box = dropdown_menu(row, uee_props, "advanced_options", "Advanced Options", section_icon='PREFERENCES')
        if box:
            row = go_to_row(box)
            row.label(text="General Export Settings", icon='SETTINGS')
            row = go_to_row(box)
            row.prop(uee_props, "y_up", text="Y-Up", toggle=True, icon='CHECKMARK' if uee_props.y_up else 'CANCEL')
            row.prop(uee_props, "join_meshes", text="Join Meshes at Export", toggle=True, icon='CHECKMARK' if uee_props.join_meshes else 'CANCEL')
            row = go_to_row(box)
            row.prop(uee_props, "include_transform", text="Include Location", toggle=True, icon='CHECKMARK' if uee_props.include_transform else 'CANCEL')
            row.prop(uee_props, "include_curve", text="Include Curve Geometry", toggle=True, icon='CHECKMARK' if uee_props.include_curve else 'CANCEL')
            box.separator(type='LINE')
            if uee_props.enable_experimental_features:
                row = go_to_row(box)
                row.label(text="Rig and Animation Export Settings", icon='ARMATURE_DATA')
                row = go_to_row(box)
                row.prop(uee_props, "export_rigged_settings", text="Rigged Asset Export Settings", expand=True)
                row.prop(uee_props, "rig_face_y", text="Face Y Forward", toggle=True, icon='CHECKMARK' if uee_props.rig_face_y else 'CANCEL')
                row = go_to_row(box)
                row.prop(uee_props, "rigged_asset_name", text="Rigged Asset Name")
                row.prop(uee_props, "export_only_rig", text=f"Export Only Rig", toggle=True, icon='CHECKMARK' if uee_props.export_only_rig else 'CANCEL')
                box.separator(type='LINE')
            row = go_to_row(box)
            row.prop(uee_props, "enable_experimental_features", toggle=True, icon='CHECKMARK' if uee_props.enable_experimental_features else 'CANCEL')

_classes = ( 
    UEE_Panel, 
    )

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)