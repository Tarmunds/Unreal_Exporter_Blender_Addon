import bpy
from bpy.types import Operator
from .Functions import *
from ..UEE.Functions import restore_selection, convert_to_mesh, find_top_parent_in_one_hierarchy

class CT_AddCollisionToSelected(Operator):
    bl_idname = "ct.add_collision_to_selected"
    bl_label = "Add Collision to Selected"

    def execute(self, context):
        selection = context.selected_objects
        if not selection:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        for obj in selection:
            pass
        
        return {'FINISHED'}
    
class CT_GenerateConvexCollisionToSelected(Operator):
    bl_idname = "ct.generate_convex_collision_to_selected"
    bl_label = "Generate Convex Collision to Selected"

    def execute(self, context):
        selection = context.selected_objects
        active_obj = context.view_layer.objects.active
        if not selection:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}
        
        name = bpy.path.clean_name(active_obj.name)

        bpy.ops.object.duplicate()
        duplicate_objects = context.selected_objects
        convert_to_mesh(duplicate_objects)
        bpy.ops.object.join()
        
        joined_obj = context.selected_objects[0]
        bpy.context.view_layer.objects.active = joined_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode='OBJECT')
        num = 1
        while True:
            name_exists = any(o.name == f"UCX_{name}_{num:02}" for o in bpy.data.objects)
            if not name_exists:
                break
            num += 1
        joined_obj.name = f"UCX_{name}_{num:02}"

        return {'FINISHED'}




_classes = (
    CT_AddCollisionToSelected,
    CT_GenerateConvexCollisionToSelected,
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)