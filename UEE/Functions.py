import os, bpy, bmesh
from mathutils import Vector, Matrix


def check_path_valid(path, self):
        basedir = os.path.dirname(bpy.data.filepath)
        if not path:
            self.report({'ERROR'}, "Export path is empty. Please specify a valid path.")
            return False, None
        
        export_dir = os.path.join(basedir, path)
        
        try:
            os.makedirs(export_dir, exist_ok=True)
        except OSError as e:
            self.report({'ERROR'}, f"Failed to create directory: {export_dir}. Error: {e}")
            return False, None
        return True, export_dir

def export_object(main_obj, path, self):
    uee_props= bpy.context.scene.uee_properties

    name = bpy.path.clean_name(main_obj.name)
    file_path = os.path.join(path, f"{name}.{uee_props.export_format.lower()}")

    if uee_props.include_curve :
        type_export = 'MESH', 'ARMATURE', 'OTHER' 
    else: 
        type_export = 'MESH', 'ARMATURE'
        if main_obj.type == 'CURVE': 
            self.report({'WARNING'}, f"Skipping curve object: {main_obj.name} (curve export is disabled)")
            return False
    
    try:
        if uee_props.export_format == "FBX":
            bpy.ops.export_scene.fbx(
                filepath=file_path,
                use_selection=True,
                apply_unit_scale=False,
                object_types=set(type_export),
                mesh_smooth_type='FACE',
                use_mesh_modifiers=True,
                bake_space_transform=uee_props.y_up
            )

        elif uee_props.export_format == "OBJ":
            bpy.ops.wm.obj_export(
                filepath=file_path,
                check_existing=True
            )

        self.report({'INFO'}, f"Exported: {bpy.path.clean_name(main_obj.name)}.{uee_props.export_format.lower()}")
        return True

    except Exception as e:
        self.report({'ERROR'}, f"Export failed for {file_path}: {str(e)}")
        return False
    
def convert_to_mesh(objects):
    
    if isinstance(objects, bpy.types.Object):
        objects = [objects]

    converted_objects = []
    for obj in objects:
        try:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target='MESH')
            converted_objects.append(obj)
        except Exception as e:
            print(f"Conversion to mesh failed for {obj.name}: {str(e)}")
    return converted_objects

def find_top_parent_in_one_hierarchy(hierarchy_objects):
    for obj in hierarchy_objects:
        if not obj.parent:
            parent = obj
            break
    return parent

def restore_selection(selection):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selection:
        obj.select_set(True)

def set_collision_objects_selectable(context):
    ct_props = context.scene.ct_properties
    if not ct_props.selectable :
        setattr(ct_props, "selectable", True)
        return False
    else:
        return True
    
def reset_collision_objects_selectable(context, previous_state):
    ct_props = context.scene.ct_properties
    setattr(ct_props, "selectable", previous_state)