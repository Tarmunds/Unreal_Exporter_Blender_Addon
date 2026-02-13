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
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        ct_props = context.scene.ct_properties
        selection = context.selected_objects
        active_obj = context.view_layer.objects.active
        if not selection:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}
        
        #getting name of active or first of the list
        if active_obj : name = bpy.path.clean_name(active_obj.name) 
        else: name = context.selected_objects[0].name

        bpy.ops.object.duplicate()
        duplicate_objects = context.selected_objects
        convert_to_mesh(duplicate_objects)
        bpy.ops.object.join()
        
        joined_obj = context.selected_objects[0]
        bpy.context.view_layer.objects.active = joined_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode='OBJECT')

        data = joined_obj.data
        face_count = len(data.polygons)
        ratio = clamp(ct_props.target_face_count / face_count if face_count > 0 else 1.0)

        dec = joined_obj.modifiers.new(name="Decimate", type='DECIMATE')
        dec.decimate_type = 'COLLAPSE'
        dec.ratio = ratio
        dec.use_collapse_triangulate = True
        if ct_props.bake_simplification :
            duplicate_objects = convert_to_mesh(joined_obj)

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