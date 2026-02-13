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

        row = go_to_row(layout)
        row.label(text="This panel is for testing and development purposes only.", icon='ERROR')
        row = go_to_row(layout)
        row.operator("ct.add_collision_to_selected", text="Add Cube Collision to Selected", icon='CUBE')
        row = go_to_row(layout)
        row.operator("ct.add_collision_to_selected", text="Add Sphere Collision to Selected", icon='SPHERE')
        row = go_to_row(layout)
        row.operator("ct.add_collision_to_selected", text="Add Capsule Collision to Selected", icon='MESH_CYLINDER')
        row = go_to_row(layout, scale_y=2.0)
        row.operator("ct.generate_convex_collision_to_selected", text="Generate Convex Collision to Selected", icon='MOD_SOLIDIFY')
    
_classes = (
    CT_Panel,
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)