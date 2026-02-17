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

       
        col = self.layout.column(align=True)
        
        #---Unity and more Options---
        box = dropdown_menu(col, uee_props, "advanced_options", "Advanced Options", section_icon='PREFERENCES')
        if box:

            row = go_to_row(box)
            row.prop(uee_props, "y_up", text="Y-Up")
            row.prop(uee_props, "join_meshes", text="Join Meshes at Export")
            row = go_to_row(box)
            row.prop(uee_props, "include_transform", text="Include Location")
            row.prop(uee_props, "include_curve", text="Include Curve Geometry")

        row = go_to_row(layout)
        row.prop(uee_props, "export_collision", text=f"Collision Export {'Enable' if uee_props.export_collision else 'Disable'}", toggle=True, icon='MESH_CUBE' if uee_props.export_collision else 'CANCEL')
        row.prop(uee_props, "export_sockets", text=f"Socket Export {'Enable' if uee_props.export_sockets else 'Disable'}", toggle=True, icon='EMPTY_DATA' if uee_props.export_sockets else 'CANCEL')
        # Export buttons
        row = go_to_row(layout, scale_y=2)
        row.operator("export.selected_objects", text="Export Selected Objects", icon='STICKY_UVS_DISABLE')
        row = go_to_row(layout, scale_y=2)
        row.operator("export.parented_objects", text="Export Each Hierarchy", icon='STICKY_UVS_LOC')


_classes = ( 
    UEE_Panel, 
    )

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)