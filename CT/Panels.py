import bpy
from ..Utils.PanelUtils import *

class CT_Panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_collision_tools"
    bl_label = "Collision Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarmunds Addons'

    def draw_header_preset(self, context):
        layout = self.layout
        layout.label(icon='MESH_CUBE')
        #layout.prop(context.scene.uee_properties, "export_collision", text="Export Col", toggle=True, icon='MESH_CUBE' if context.scene.uee_properties.export_collision else 'CANCEL')
        layout.label(text="")

    def draw(self, context):
        layout = self.layout
        ct_props = context.scene.ct_properties

        row = go_to_row(layout)
        row.label(text="Collision Display Options:")
        row = go_to_row(layout)
        row.prop(ct_props, "color_display", text="Color", toggle=True)
        row.prop(ct_props, "wire_display", text="Wireframe", toggle=True)
        row.prop(ct_props, "selectable", text="Selectable", toggle=True)
        row = go_to_row(layout)
        row.operator("ct.set_collision_visibility", text=f"Hide {'All' if ct_props.visibility_button_field == 'All_MESH' else 'Hierarchy'} Collisions", icon='HIDE_ON').visibility = False
        row.operator("ct.set_collision_visibility", text=f"Show {'All' if ct_props.visibility_button_field == 'All_MESH' else 'Hierarchy'} Collisions", icon='HIDE_OFF').visibility = True
        
        row = go_to_row(layout)

        left, right = split_row(row, factor=0.5)
        left.label(text="Simple Collision Operators:")

        right.label(text="UBX, USP, UCP")

        row = go_to_row(layout, scale_y=2.0)
        row.operator("ct.add_collision_to_selected", text="Add Cube Collision", icon='CUBE').volume_type = "BOX"
        row.operator("ct.add_collision_to_selected", text="Add Sphere Collision", icon='SPHERE').volume_type = "SPHERE"
        row = go_to_row(layout)
        left, right = split_row(row, factor=0.7, right_align=False)
        left.operator("ct.add_collision_to_selected", text="Add Capsule Collision", icon='MESH_CYLINDER').volume_type = "CAPSULE"
        right.operator("ct.regenerate_capsule_collision", text="Regenerate", icon='CON_FOLLOWPATH')
        row = go_to_row(layout, scale_y=1.0)
        row.prop(ct_props, "capsule_radius", text="Capsule Radius", slider=True)
        row.prop(ct_props, "capsule_height", text="Capsule Height", slider=True)

        row = go_to_row(layout)
        left, right = split_row(row, factor=0.5)
        left.label(text="Collision Generators:")
        right.label(text="UCX")


        row = go_to_row(layout, scale_y=2.0)
        row.operator("ct.generate_convex_collision_to_selected", text="Generate Convex Collision to Selected", icon='MOD_SOLIDIFY')
        box = dropdown_menu(layout, ct_props, "convex_options", "Convex Hull Options", section_icon='MOD_SOLIDIFY')
        if box:
            row = go_to_row(box)
            row.prop(ct_props, "target_face_count", slider=True)
            row = go_to_row(box)
            row.prop(ct_props, "bake_simplification", toggle=True)
            row.prop(ct_props, "convex_parent", text="Parent to Source", toggle=True)

        row = go_to_row(layout, scale_y=2.0)
        row.operator("ct.kdop_generate_collision", text="Generate k-DOP Collision Hull", icon='MESH_ICOSPHERE')
        row = go_to_row(layout)
        row.prop(ct_props, "kdop_mode", text="k-DOP Mode")

        box = dropdown_menu(layout, ct_props, "kdop_options", "k-DOP Options", section_icon='MESH_ICOSPHERE')
        if box:
            row = go_to_row(box)
            row.prop(ct_props, "kdop_space")
            row = go_to_row(box)
            row.prop(ct_props, "kdop_use_evaluated_mesh", text="Use Evaluated Mesh", toggle=True)
            row.prop(ct_props, "kdop_parent_to_source", text="Parent to Source", toggle=True)
            row = go_to_row(box)
            row.prop(ct_props, "kdop_inside_epsilon", text="Inside Epsilon")
            row = go_to_row(box)
            row.prop(ct_props, "kdop_name_prefix", text="Prefix")
        
        row = go_to_row(layout)
        row.label(text="Options :")
        box = dropdown_menu(layout, ct_props, "advanced_options", "Advanced Options", section_icon='PREFERENCES')
        if box:
            row = go_to_row(box)
            row.label(text="Field of visibility:")
            row.prop(ct_props, "visibility_button_field", text="Visibility Button Field", expand=True)
            row = go_to_row(box)
            row.label(text="Multiple Selection Behavior:")
            row.prop(ct_props, "multiple_selection_behavior", text="Multiple Selection Behavior", expand=True)
            row = go_to_row(box)
            row.operator("ct.delete_collision", text="Delete All Collision", icon='TRASH').selected_hierarchy = False
            row.operator("ct.delete_collision", text="Delete Hierarchy Collision", icon='TRASH').selected_hierarchy = True
            row = go_to_row(box)
            row.prop(ct_props, "mat_color", text="Collision Color")
    
_classes = (
    CT_Panel,
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)