import bpy
from .Functions import *
from ..CT.Functions import check_if_collision, set_display, get_collision_objects, find_available_collision_name, get_top_parents
from bpy.types import Operator


class UEE_ExportSelectedObjects(Operator):
    bl_idname = "export.selected_objects"
    bl_label = "Export Selected Objects"
    
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0 and context.mode == 'OBJECT'


    def execute(self, context):
        uee_props = context.scene.uee_properties
        path = uee_props.export_path
        include_transform = uee_props.include_transform

        valid_path, export_dir = check_path_valid(path, self)
        if not valid_path:
            self.report({'ERROR'}, "Invalid export path. Please set a valid path before exporting.")
            return {'CANCELLED'}
        
        collision_selectable_state = set_collision_objects_selectable(context)
        socket_selectable_state = set_socket_objects_selectable(context)

        selection = context.selected_objects
        for obj in selection:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)

            collision_affected = []
            prepare_collision_to_export(obj, context, collision_affected, check_if_collision)
            socket_affected = []
            prepare_sockets_to_export(obj, context, socket_affected)

            original_location = obj.location.copy()
            if not include_transform:
                obj.location = (0, 0, 0)

            c = export_object(obj, export_dir, self)
            if not include_transform:
                obj.location = original_location
            if not c:
                return {'CANCELLED'}
            
            for collision in collision_affected:
                set_display(collision, context)
            
            if socket_affected:
                for socket in socket_affected:
                    socket.scale *= 100
            
        reset_collision_objects_selectable(context, collision_selectable_state)
        reset_socket_objects_selectable(context, socket_selectable_state)
        restore_selection(selection)
        return {'FINISHED'}


class UEE_ExportParentedObjects(Operator):
    bl_idname = "export.parented_objects"
    bl_label = "Export Each Hierarchy"

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0 and context.mode == 'OBJECT'

    def execute(self, context):
        uee_props = context.scene.uee_properties
        path = uee_props.export_path
        include_transform = uee_props.include_transform
        join_meshes = uee_props.join_meshes

        valid_path, export_dir = check_path_valid(path, self)
        if not valid_path:
            self.report({'ERROR'}, "Invalid export path. Please set a valid path before exporting.")
            return {'CANCELLED'}
        
        collision_selectable_state = set_collision_objects_selectable(context)
        socket_selectable_state = set_socket_objects_selectable(context)

        processed_parents = set()
        selection = context.selected_objects
        for obj in context.selected_objects:
            #getting to top parent of the hierarchy
            parent = obj
            while parent.parent:
                parent = parent.parent
            #skip if already processed
            if parent in processed_parents:
                continue
            processed_parents.add(parent)

            original_location = parent.location.copy()
            if not include_transform:
                parent.location = (0, 0, 0)

            # deselect everything and select hierarchy
            bpy.ops.object.select_all(action='DESELECT')
            parent.select_set(True)
            for child in parent.children_recursive:
                child.select_set(True)

            collision_affected = []
            prepare_collision_to_export(parent, context, collision_affected, check_if_collision, all_children=True)
            socket_affected = []
            prepare_sockets_to_export(parent, context, socket_affected, all_children=True)
            
            if not join_meshes:
                c = export_object(parent, export_dir, self)
                if not include_transform:
                    parent.location = original_location
                if not c:
                    return {'CANCELLED'}
            else:
                # duplicate hierarchy to avoid breaking original
                bpy.ops.object.duplicate()
                duplicate_objects = context.selected_objects
                duplicate_parent = find_top_parent_in_one_hierarchy(duplicate_objects)
                collision_collection = get_collision_objects()

                #get all non mesh duplcated object
                collision_duplicate = []
                socket_duplicate = []
                for obj in duplicate_parent.children_recursive:
                    if obj.type == 'MESH' and obj in collision_collection:
                        collision_duplicate.append(obj)
                        duplicate_objects.remove(obj)
                        obj.select_set(False)
                    if obj.type == 'EMPTY' and obj.name.startswith("SOCKET_"):
                        socket_duplicate.append(obj)
                        duplicate_objects.remove(obj)
                        obj.select_set(False)


                # make all converted to mesh
                convert_to_mesh(duplicate_objects)
                # join them all into one
                bpy.context.view_layer.objects.active = duplicate_parent
                bpy.ops.object.join()
                joined_obj = bpy.context.view_layer.objects.active
                # export only the joined mesh
                bpy.ops.object.select_all(action='DESELECT')
                joined_obj.select_set(True)
                for obj in collision_duplicate:
                    prefix = obj.name[:3]
                    obj.name = find_available_collision_name(joined_obj.name, prefix)
                    obj.parent = joined_obj
                    obj.select_set(True)

                for obj in socket_duplicate:
                    obj.name = find_available_collision_name(joined_obj.name, "SOCKET")
                    obj.parent = joined_obj
                    obj.select_set(True)

                c = export_object(parent, export_dir, self)
                if not include_transform:
                    parent.location = original_location
                bpy.ops.object.delete()
                if not c:
                    return {'CANCELLED'}
            for collision in collision_affected:
                set_display(collision, context)
            if socket_affected:
                for socket in socket_affected:
                    socket.scale *= 100

        reset_collision_objects_selectable(context, collision_selectable_state)
        reset_socket_objects_selectable(context, socket_selectable_state)
        restore_selection(selection)
        return {'FINISHED'}


class UEE_AddPathOperator(Operator):
    bl_idname = "export.add_path"
    bl_label = "Save Export Path"

    def execute(self, context):
        uee_props = context.scene.uee_properties
        path = uee_props.export_path
        saved_paths = uee_props.saved_paths
        if not any(path_item.name == path for path_item in saved_paths):
            saved_paths.add().name = path
        return {'FINISHED'}

class UEE_SelectSavedPathOperator(Operator):
    bl_idname = "export.select_saved_path"
    bl_label = "Select Saved Path"

    def execute(self, context):
        uee_props = context.scene.uee_properties
        saved_path = uee_props.saved_paths[int(uee_props.saved_paths_enum)].name
        uee_props.export_path = saved_path
        return {'FINISHED'}
    
class UEE_ExportRigOperator(bpy.types.Operator):
    bl_idname = "export.export_rig"
    bl_label = "Export Rig with Animation"

    def execute(self, context):
        uee_props = context.scene.uee_properties
        path = uee_props.export_path

        valid_path, export_dir = check_path_valid(path, self)
        if not valid_path:
            return {'CANCELLED'}

        selection = list(context.selected_objects)
        active_before = context.view_layer.objects.active

        if not selection or active_before is None:
            self.report({'ERROR'}, "Select at least one object in the hierarchy (and make one active).")
            return {'CANCELLED'}
        if active_before not in selection:
            self.report({'ERROR'}, "Active object must be part of the selection.")
            return {'CANCELLED'}

        def get_root(obj):
            while obj.parent:
                obj = obj.parent
            return obj

        # Root determined from ACTIVE (stable)
        top_parent = get_root(active_before)

        # Ensure all selected are in same hierarchy root
        for obj in selection:
            if get_root(obj) != top_parent:
                self.report({'ERROR'}, "Selected objects are not in the same hierarchy")
                return {'CANCELLED'}

        # Pick a good name:
        # 1) explicit prop
        # 2) selected/active mesh name
        # 3) first mesh anywhere under the root
        object_name = None
        if active_before and active_before.type == 'MESH':
            object_name = active_before.name
        else:
            sel_mesh = next((o for o in selection if o.type == 'MESH'), None)
            if sel_mesh:
                object_name = sel_mesh.name
            else:
                any_mesh = next((o for o in top_parent.children_recursive if o.type == 'MESH'), None)
                if any_mesh:
                    object_name = any_mesh.name

        name = uee_props.rigged_asset_name or object_name or top_parent.name or "RiggedAsset"
        file_path = os.path.join(export_dir, f"{name}.{uee_props.export_format.lower()}")

        socket_selectable_state = None

        try:
            # Make sockets selectable (your existing logic)
            socket_selectable_state = set_socket_objects_selectable(context)

            # Build export selection from root no matter what user initially selected
            bpy.ops.object.select_all(action='DESELECT')
            top_parent.select_set(True)
            for obj in top_parent.children_recursive:
                obj.select_set(True)

            context.view_layer.objects.active = top_parent

            bpy.ops.export_scene.fbx(
                filepath=file_path,
                use_selection=True,

                object_types={'MESH', 'ARMATURE', 'EMPTY'},

                apply_unit_scale=True,
                bake_space_transform=True,

                axis_forward='-Y',
                axis_up='Z',

                use_mesh_modifiers=True,
                mesh_smooth_type='FACE',

                add_leaf_bones=False,
                use_armature_deform_only=True,
                armature_nodetype='NULL',

                bake_anim=True,
                bake_anim_step=1.0,
                bake_anim_simplify_factor=0.0,
                bake_anim_force_startend_keying=True,
            )

        finally:
            # Always restore scene state even if export errors
            if socket_selectable_state is not None:
                reset_socket_objects_selectable(context, socket_selectable_state)

            bpy.ops.object.select_all(action='DESELECT')
            for obj in selection:
                if obj and obj.name in context.scene.objects:
                    obj.select_set(True)

            if active_before and active_before.name in context.scene.objects:
                context.view_layer.objects.active = active_before

        self.report({'INFO'}, f"Exported rigged asset: {name}.{uee_props.export_format.lower()}")
        return {'FINISHED'}


_classes = (
    UEE_ExportSelectedObjects, 
    UEE_ExportParentedObjects, 
    UEE_AddPathOperator, 
    UEE_SelectSavedPathOperator, 
    UEE_ExportRigOperator,
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)