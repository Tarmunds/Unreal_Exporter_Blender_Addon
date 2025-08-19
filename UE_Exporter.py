import bpy
import os
from bpy.types import Operator

class UnrealExport_ExportSelectedObjectsOperator(Operator):
    bl_idname = "export.selected_objects"
    bl_label = "Export Selected Objects"

    def execute(self, context):
        path = context.scene.mesh_rename_path.strip()
        if not path:
            self.report({'ERROR'}, "Export path is empty. Please specify a valid path.")
            return {'CANCELLED'}
        
        export_format = context.scene.export_format.lower()
        include_transform = context.scene.include_transform
        Yup = context.scene.Yup
        basedir = os.path.dirname(bpy.data.filepath)
        export_dir = os.path.join(basedir, path)

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

            if bpy.types.Scene.IncludeCurve :
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
                        bake_space_transform=Yup
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


class UnrealExport_ExportParentedObjectsOperator(Operator):
    bl_idname = "export.parented_objects"
    bl_label = "Export Each Hierarchy"

    def execute(self, context):
        path = context.scene.mesh_rename_path.strip()
        if not path:
            self.report({'ERROR'}, "Export path is empty. Please specify a valid path.")
            return {'CANCELLED'}

        export_format = context.scene.export_format.lower()
        include_transform = context.scene.include_transform
        basedir = os.path.dirname(bpy.data.filepath)
        export_dir = os.path.join(basedir, path)
        Yup = context.scene.Yup
        JoinAll = getattr(context.scene, "JoinAll", False)

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

            if bpy.types.Scene.IncludeCurve:
                ObjectTypeExported = {'MESH', 'ARMATURE', 'OTHER'}
            else:
                ObjectTypeExported = {'MESH', 'ARMATURE'}

            # --- JOIN ALL MODE ---
            if JoinAll:
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
                            bake_space_transform=Yup
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
                            bake_space_transform=Yup
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


class UnrealExport_AddPathOperator(Operator):
    bl_idname = "export.add_path"
    bl_label = "Save Export Path"

    def execute(self, context):
        path = context.scene.mesh_rename_path
        saved_paths = context.scene.saved_paths
        if not any(path_item.name == path for path_item in saved_paths):
            saved_paths.add().name = path
        return {'FINISHED'}

class UnrealExport_SelectSavedPathOperator(Operator):
    bl_idname = "export.select_saved_path"
    bl_label = "Select Saved Path"

    def execute(self, context):
        saved_path = context.scene.saved_paths[int(context.scene.saved_path_enum)].name
        context.scene.mesh_rename_path = saved_path
        return {'FINISHED'}

def update_saved_paths_enum(self, context):
    items = [(str(i), path.name, "") for i, path in enumerate(context.scene.saved_paths)]
    return items

def menu_func_export(self, context):
    self.layout.operator(ExportSelectedObjectsOperator.bl_idname, text="Export Selected Unreal Ready (fbx/obj)")