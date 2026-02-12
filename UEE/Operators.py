import bpy
import os
from bpy.types import Operator

class UEE_ExportSelectedObjects(Operator):
    bl_idname = "export.selected_objects"
    bl_label = "Export Selected Objects"
    

    def execute(self, context):
        uee_props = context.scene.uee_properties
        path = uee_props.export_path

        if not path:
            self.report({'ERROR'}, "Export path is empty. Please specify a valid path.")
            return {'CANCELLED'}

        export_format = uee_props.export_format.lower()
        include_transform = uee_props.include_transform
        include_curve = uee_props.include_curve
        basedir = os.path.dirname(bpy.data.filepath)
        export_dir = os.path.join(basedir, path)
        y_up = uee_props.y_up


        try:
            os.makedirs(export_dir, exist_ok=True)
        except OSError as e:
            self.report({'ERROR'}, f"Failed to create directory: {export_dir}. Error: {e}")
            return {'CANCELLED'}

        selection = context.selected_objects
        for obj in selection:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)

            original_location = obj.location.copy()
            if not include_transform:
                obj.location = (0, 0, 0)

            name = bpy.path.clean_name(obj.name)
            fn = os.path.join(export_dir, f"{name}.{export_format}")

            if include_curve:
                ObjectTypeExported = 'MESH', 'ARMATURE', 'OTHER'
            else :
                ObjectTypeExported = 'MESH', 'ARMATURE'

            try:
                if export_format == "fbx":
                    bpy.ops.export_scene.fbx(
                        filepath=fn,
                        use_selection=True,
                        apply_unit_scale=False,
                        object_types=set(ObjectTypeExported),
                        mesh_smooth_type='FACE',
                        use_mesh_modifiers=True,
                        bake_space_transform=y_up
                    )
                elif export_format == "obj":
                    bpy.ops.wm.obj_export(
                        filepath=fn,
                        check_existing=True
                    )
                else:
                    self.report({'ERROR'}, f"Unsupported export format: {export_format}")
                    return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"Export failed for {fn}: {str(e)}")
                return {'CANCELLED'}

            if not include_transform:
                obj.location = original_location

            self.report({'INFO'}, f"Written: {fn}")

        return {'FINISHED'}


class UEE_ExportParentedObjects(Operator):
    bl_idname = "export.parented_objects"
    bl_label = "Export Each Hierarchy"

    def execute(self, context):
        uee_props = context.scene.uee_properties
        path = uee_props.export_path

        if not path:
            self.report({'ERROR'}, "Export path is empty. Please specify a valid path.")
            return {'CANCELLED'}

        export_format = uee_props.export_format.lower()
        include_transform = uee_props.include_transform
        include_curve = uee_props.include_curve
        basedir = os.path.dirname(bpy.data.filepath)
        export_dir = os.path.join(basedir, path)
        y_up = uee_props.y_up
        join_meshes = uee_props.join_meshes

        try:
            os.makedirs(export_dir, exist_ok=True)
        except OSError as e:
            self.report({'ERROR'}, f"Failed to create directory: {export_dir}. Error: {e}")
            return {'CANCELLED'}

        processed_parents = set()
        for obj in context.selected_objects:
            parent = obj
            while parent.parent:
                parent = parent.parent

            if parent in processed_parents:
                continue
            processed_parents.add(parent)

            original_location = parent.location.copy()
            if not include_transform:
                parent.location = (0, 0, 0)

            # deselect everything
            bpy.ops.object.select_all(action='DESELECT')
            parent.select_set(True)
            for child in parent.children_recursive:
                child.select_set(True)

            name = bpy.path.clean_name(parent.name)
            fn = os.path.join(export_dir, f"{name}.{export_format}")

            if include_curve:
                ObjectTypeExported = {'MESH', 'ARMATURE', 'OTHER'}
            else:
                ObjectTypeExported = {'MESH', 'ARMATURE'}

            # --- JOIN ALL MODE ---
            if join_meshes:
                # duplicate hierarchy to avoid breaking original
                bpy.ops.object.duplicate()
                dup_objects = [o for o in context.selected_objects]
                dup_parent = None
                for o in dup_objects:
                    if not o.parent:
                        dup_parent = o
                        break

                # make all converted to mesh
                for o in dup_objects:
                    try:
                        bpy.context.view_layer.objects.active = o
                        bpy.ops.object.convert(target='MESH')
                    except:
                        pass

                # join them all into one
                bpy.context.view_layer.objects.active = dup_parent
                bpy.ops.object.join()
                joined_obj = bpy.context.view_layer.objects.active

                # export only the joined mesh
                bpy.ops.object.select_all(action='DESELECT')
                joined_obj.select_set(True)

                try:
                    if export_format == "fbx":
                        bpy.ops.export_scene.fbx(
                            filepath=fn,
                            use_selection=True,
                            apply_unit_scale=False,
                            object_types={'MESH'},
                            mesh_smooth_type='FACE',
                            use_mesh_modifiers=True,
                            bake_space_transform=y_up
                        )
                    elif export_format == "obj":
                        bpy.ops.wm.obj_export(
                            filepath=fn,
                            check_existing=True
                        )
                    else:
                        self.report({'ERROR'}, f"Unsupported export format: {export_format}")
                        return {'CANCELLED'}
                except Exception as e:
                    self.report({'ERROR'}, f"Export failed for {fn}: {str(e)}")
                    return {'CANCELLED'}

                # delete duplicates (restore original hierarchy automatically)
                bpy.ops.object.delete()

            else:
                # --- NORMAL MODE ---
                try:
                    if export_format == "fbx":
                        bpy.ops.export_scene.fbx(
                            filepath=fn,
                            use_selection=True,
                            apply_unit_scale=False,
                            object_types=ObjectTypeExported,
                            mesh_smooth_type='FACE',
                            use_mesh_modifiers=True,
                            bake_space_transform=y_up
                        )
                    elif export_format == "obj":
                        bpy.ops.wm.obj_export(
                            filepath=fn,
                            check_existing=True
                        )
                    else:
                        self.report({'ERROR'}, f"Unsupported export format: {export_format}")
                        return {'CANCELLED'}
                except Exception as e:
                    self.report({'ERROR'}, f"Export failed for {fn}: {str(e)}")
                    return {'CANCELLED'}

            if not include_transform:
                parent.location = original_location

            self.report({'INFO'}, f"Written: {fn}")

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

def update_saved_paths_enum(self, context):
    items = [(str(i), path.name, "") for i, path in enumerate(context.scene.saved_paths)]
    return items

def menu_func_export(self, context):
    self.layout.operator(UEE_ExportSelectedObjects.bl_idname, text="Export Selected Unreal Ready (fbx/obj)")

_classes = (
    UEE_ExportSelectedObjects, 
    UEE_ExportParentedObjects, 
    UEE_AddPathOperator, 
    UEE_SelectSavedPathOperator, 
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)