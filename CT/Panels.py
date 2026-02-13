import bpy
from ..Utils.PanelUtils import *

class CT_Panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_collision_tools"
    bl_label = "Collision Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarmunds Addons'

    def draw(self, context):
        layout = self.layout
        ct_props = context.scene.ct_properties

        row = go_to_row(layout)
        row.label(text="This panel is for testing and development purposes only.", icon='ERROR')
        row.prop(ct_props, "wire_display", text="Wireframe Display", toggle=True)
        row = go_to_row(layout)
        row.operator("ct.add_collision_to_selected", text="Add Cube Collision to Selected", icon='CUBE')
        row = go_to_row(layout)
        row.operator("ct.add_collision_to_selected", text="Add Sphere Collision to Selected", icon='SPHERE')
        row = go_to_row(layout)
        row.operator("ct.add_collision_to_selected", text="Add Capsule Collision to Selected", icon='MESH_CYLINDER')
        row = go_to_row(layout, scale_y=2.0)
        row.operator("ct.generate_convex_collision_to_selected", text="Generate Convex Collision to Selected", icon='MOD_SOLIDIFY')

        box = dropdown_menu(layout, ct_props, "convex_options", "Convex Hull Options", section_icon='MOD_SOLIDIFY')
        if box:
            row = go_to_row(box)
            row.prop(ct_props, "bake_simplification", toggle=True)
            row.prop(ct_props, "target_face_count", slider=True)

        row = go_to_row(layout, scale_y=2.0)
        row.operator("ct.kdop_generate_collision", text="Generate k-DOP Collision Hull", icon='MESH_ICOSPHERE')
        row = go_to_row(layout)
        row.prop(ct_props, "kdop_mode")

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

    
_classes = (
    CT_Panel,
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)