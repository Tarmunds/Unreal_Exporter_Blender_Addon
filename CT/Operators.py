from multiprocessing import context
import bpy
from bpy.types import Operator
from .Functions import *
from ..UEE.Functions import restore_selection, convert_to_mesh, find_top_parent_in_one_hierarchy

class CT_AddCollisionToSelected(Operator):
    bl_idname = "ct.add_collision_to_selected"
    bl_label = "Add Collision to Selected"
    bl_options = {"REGISTER", "UNDO"}

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
        if not selection:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}


        active_obj = context.view_layer.objects.active

        #getting name of active or first of the list
        if active_obj : 
            name = bpy.path.clean_name(active_obj.name) 
            source_obj = active_obj
        else: 
            name = bpy.path.clean_name(context.selected_objects[0].name)
            source_obj = context.selected_objects[0]

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
        set_display(joined_obj, context)
        if ct_props.convex_parent:
            joined_obj.parent = source_obj
            joined_obj.matrix_parent_inverse = source_obj.matrix_world.inverted_safe()

        return {'FINISHED'}

class CT_KDOP_generate_collision(bpy.types.Operator):
    bl_idname = "ct.kdop_generate_collision"
    bl_label = "Generate k-DOP Collision Hull"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ct_props = context.scene.ct_properties
        selection = context.selected_objects
        if not selection or selection[0].type != "MESH":
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}
        


        active_obj = context.view_layer.objects.active
        if active_obj : 
            source_obj = active_obj
        else: 
            source_obj = context.selected_objects[0]

        if len(selection) > 1:
            bpy.ops.object.duplicate()
            duplicate_objects = context.selected_objects
            convert_to_mesh(duplicate_objects)
            bpy.ops.object.join()
            obj = context.selected_objects[0]
            should_cleanup = True
        else :
            obj = selection[0]
            should_cleanup = False
            

        # Sample verts in requested space
        verts = get_object_vertices(obj, use_evaluated_mesh=ct_props.kdop_use_evaluated_mesh, space=ct_props.kdop_space)
        if not verts:
            self.report({"ERROR"}, "Object has no vertices")
            return {"CANCELLED"}

        dirs = kdop_directions(ct_props.kdop_mode)
        planes = build_kdop_planes(verts, dirs)

        points = generate_kdop_points(planes, inside_eps=ct_props.kdop_inside_epsilon)
        if len(points) < 4:
            self.report(
                {"ERROR"},
                f"Not enough hull points generated ({len(points)}). Try another DOP type or increase Inside Epsilon.",
            )
            return {"CANCELLED"}

        # If we computed in WORLD space, convert points back to LOCAL space so the hull mesh is local
        if ct_props.kdop_space == "WORLD":
            inv = obj.matrix_world.inverted_safe()
            points = [inv @ p for p in points]

        hull_mesh = build_convex_hull_mesh_from_points(points, name=f"{obj.name}_{ct_props.kdop_mode}_MESH")
        if hull_mesh is None:
            self.report({"ERROR"}, "Failed to build convex hull mesh")
            return {"CANCELLED"}
        
        #suffix
        mode_name = ct_props.kdop_mode.replace("_", "")
        num = 1
        while True:
            name_exists = any(o.name == f"{ct_props.kdop_name_prefix}{obj.name}_{mode_name}-{num:02}" for o in bpy.data.objects)
            if not name_exists:
                break
            num += 1
        col_name = f"{ct_props.kdop_name_prefix}{source_obj.name}_{mode_name}-{num:02}"

        col_obj = create_collision_object(
            source_obj,
            hull_mesh,
            col_name,
            display_wire=ct_props.wire_display,
            parent=ct_props.kdop_parent_to_source,
            context=context,
        )

        # Match transforms of duplicate if we created one, otherwise match source
        col_obj.matrix_world = obj.matrix_world.copy()
        # set parent
        if ct_props.kdop_parent_to_source:
            col_obj.parent = source_obj
            col_obj.matrix_parent_inverse = source_obj.matrix_world.inverted_safe()
        # Select the created hull
        bpy.ops.object.select_all(action="DESELECT")
        col_obj.select_set(True)
        context.view_layer.objects.active = col_obj

        if should_cleanup:
            bpy.data.objects.remove(obj, do_unlink=True)

        self.report(
            {"INFO"},
            f"Generated {ct_props.kdop_mode} collision hull: {col_obj.name} (points: {len(points)}, planes: {len(planes)})",
        )
        return {"FINISHED"}
    
class CT_SetCollisionVisibility(Operator):
    bl_idname = "ct.set_collision_visibility"
    bl_label = "Set Collision Visibility"
    bl_options = {"REGISTER", "UNDO"}

    visibility: bpy.props.BoolProperty(
        name="Visible",
        default=True,
        description="Set collision objects visibility in viewport",
    )

    def execute(self, context):
        set_collision_objects_visibility(self.visibility, context)
        return {"FINISHED"}



_classes = (
    CT_AddCollisionToSelected,
    CT_GenerateConvexCollisionToSelected,
    CT_KDOP_generate_collision,
    CT_SetCollisionVisibility,
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)