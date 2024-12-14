import bpy
import os
from bpy.types import Operator, Panel

bl_info = {
    "name": "Export Unreal",
    "author": "Tarmunds",
    "version": (3, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Tarmunds Addons > Export Unreal",
    "description": "Exports selected objects or hierarchies into separate files at the origin.",
    "doc_url": "https://docs.google.com/document/d/1j2DZWXR-klQArrlfSLQAV_ltop4BOsD6ZXgRYFnC0b0/edit?usp=sharing",
    "tracker_url": "https://github.com/Tarmunds/Unreal-exporter",
    "category": "Import-Export",
}

class MeshRenamePanel(Panel):
    bl_idname = "VIEW3D_PT_export_unreal"
    bl_label = "Export Unreal"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tarmunds Addons'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        
        col.prop(context.scene, "mesh_rename_path", text="Path")
        
        box = col.box()
        box.prop(context.scene, "path_dropdown", icon="TRIA_DOWN", text="Path Options", emboss=False)
        if context.scene.path_dropdown:
            row = box.row()
            row.operator("export.add_path", text="Save Path")
            row = box.row()
            row.prop(context.scene, "saved_path_enum", text="Saved Paths")
            row.operator("export.select_saved_path", text="Use Path")
        
        col.prop(context.scene, "include_transform", text="Include Location")
        col.operator("export.selected_objects", text="Export Selected Objects")
        col.operator("export.parented_objects", text="Export Each Hierarchy")

class ExportSelectedObjectsOperator(Operator):
    bl_idname = "export.selected_objects"
    bl_label = "Export Selected Objects"

    def execute(self, context):
        path = context.scene.mesh_rename_path.strip()
        if not path:
            self.report({'ERROR'}, "Export path is empty. Please specify a valid path.")
            return {'CANCELLED'}
        
        export_format = context.scene.export_format.lower()
        include_transform = context.scene.include_transform
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

            try:
                if export_format == "fbx":
                    bpy.ops.export_scene.fbx(
                        filepath=fn,
                        use_selection=True,
                        apply_unit_scale=False,
                        object_types={'MESH', 'ARMATURE'},
                        mesh_smooth_type='FACE',
                        use_mesh_modifiers=True
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


class ExportParentedObjectsOperator(Operator):
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

            bpy.ops.object.select_all(action='DESELECT')
            parent.select_set(True)
            for child in parent.children_recursive:
                child.select_set(True)

            name = bpy.path.clean_name(parent.name)
            fn = os.path.join(export_dir, f"{name}.{export_format}")

            try:
                if export_format == "fbx":
                    bpy.ops.export_scene.fbx(
                        filepath=fn,
                        use_selection=True,
                        apply_unit_scale=False,
                        object_types={'MESH', 'ARMATURE'},
                        mesh_smooth_type='FACE',
                        use_mesh_modifiers=True
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


class AddPathOperator(Operator):
    bl_idname = "export.add_path"
    bl_label = "Save Export Path"

    def execute(self, context):
        path = context.scene.mesh_rename_path
        saved_paths = context.scene.saved_paths
        if not any(path_item.name == path for path_item in saved_paths):
            saved_paths.add().name = path
        return {'FINISHED'}

class SelectSavedPathOperator(Operator):
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

def register():
    bpy.utils.register_class(ExportSelectedObjectsOperator)
    bpy.utils.register_class(ExportParentedObjectsOperator)
    bpy.utils.register_class(AddPathOperator)
    bpy.utils.register_class(SelectSavedPathOperator)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.utils.register_class(MeshRenamePanel)

    bpy.types.Scene.mesh_rename_path = bpy.props.StringProperty(name="Path", default="", maxlen=1024, subtype='DIR_PATH' )
    bpy.types.Scene.export_format = bpy.props.EnumProperty(
        name="Format",
        description="Choose export format",
        items=[('FBX', 'FBX', 'Export as FBX file'),
               ('OBJ', 'OBJ', 'Export as OBJ file')],
        default='FBX'
    )
    bpy.types.Scene.include_transform = bpy.props.BoolProperty(
        name="Include Location",
        description="Include location in the export",
        default=False
    )
    bpy.types.Scene.saved_paths = bpy.props.CollectionProperty(
        type=bpy.types.PropertyGroup
    )
    bpy.types.Scene.saved_path_enum = bpy.props.EnumProperty(
        items=update_saved_paths_enum,
        name="Saved Path",
        description="Select a saved path",
    )
    bpy.types.Scene.path_dropdown = bpy.props.BoolProperty(
        name="Path Options",
        description="Toggle path options dropdown",
        default=False
    )

def unregister():
    bpy.utils.unregister_class(ExportSelectedObjectsOperator)
    bpy.utils.unregister_class(ExportParentedObjectsOperator)
    bpy.utils.unregister_class(AddPathOperator)
    bpy.utils.unregister_class(SelectSavedPathOperator)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(MeshRenamePanel)
    
    del bpy.types.Scene.mesh_rename_path
    del bpy.types.Scene.export_format
    del bpy.types.Scene.include_transform
    del bpy.types.Scene.saved_paths
    del bpy.types.Scene.saved_path_enum
    del bpy.types.Scene.path_dropdown

if __name__ == "__main__":
    register()
