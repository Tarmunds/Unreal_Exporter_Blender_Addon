from multiprocessing import context
import bpy
from bpy.types import Operator
from .Functions import *
from ..UEE.Functions import restore_selection, convert_to_mesh, find_top_parent_in_one_hierarchy

class CT_AddCollisionToSelected(Operator):
    bl_idname = "ct.add_collision_to_selected"
    bl_label = "Add Collision to Selected"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Add a simple collision primitive to the selected object(s)"

    volume_type: bpy.props.EnumProperty(
        name="Collision Volume Type",
        items=[
            ("BOX", "Box", ""),
            ("SPHERE", "Sphere", ""),
            ("CAPSULE", "Capsule", ""),
        ],
        default="BOX"
    )

    def execute(self, context):
        ct_props = context.scene.ct_properties
        selection = context.selected_objects
        if not selection:
            self.report({"WARNING"}, "No objects selected.")
            return {"CANCELLED"}
        
        match self.volume_type:
            case "BOX":
                spawn_box_collision(context, self)
            case "SPHERE":
                spawn_sphere_collision(context, self)
            case "CAPSULE":
                spawn_capsule_collision(context, self)
        
        return {"FINISHED"}


  
class CT_GenerateConvexCollisionToSelected(Operator):
    bl_idname = "ct.generate_convex_collision_to_selected"
    bl_label = "Generate Convex Collision to Selected"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Generate a convex collision mesh for the selected object(s) using the convex hull algorithm. Be aware of the performance gain of a k-dop collision over a convex hull and try to use the k-dop option when possible. For complex objects consider simplifying them before generating the collision mesh."
    
    def execute(self, context):
        ct_props = context.scene.ct_properties
        selection = context.selected_objects
        if not selection:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        if ct_props.multiple_selection_behavior == "ONE_COLLISION":
            c = [1]
            multiple = False
        elif ct_props.multiple_selection_behavior == "MULTIPLE_COLLISIONS":
            c = []
            multiple = True
            for obj in selection:
                c.append(obj)
        final_collision_objects = []
        for c in c:
            if multiple :
                bpy.ops.object.select_all(action='DESELECT')
                c.select_set(True)

            active_obj = context.view_layer.objects.active
            #getting name of active or first of the list
            if active_obj and not multiple and active_obj in selection: 
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

            joined_obj.name = find_available_collision_name(name, prefix="UCX")
            set_display(joined_obj, context)

            if ct_props.convex_parent:
                # Save world transform BEFORE parenting
                mw = joined_obj.matrix_world.copy()

                joined_obj.parent = source_obj
                joined_obj.matrix_parent_inverse = source_obj.matrix_world.inverted_safe()

                # Restore world transform so parenting never moves it
                joined_obj.matrix_world = mw

            final_collision_objects.append(joined_obj)
        
        bpy.ops.object.select_all(action="DESELECT")
        for obj in final_collision_objects:
            obj.select_set(True)
        return {'FINISHED'}

class CT_Regenerate_Capsule_Collision(Operator):
    bl_idname = "ct.regenerate_capsule_collision"
    bl_label = "Regenerate Capsule Collision"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Regenerate capsule collision for the selected capsule collision object(s) using the current radius and height settings. This is useful to quickly update the collision mesh after changing the radius or height properties, without having to delete and re-add new capsule collisions."

    def execute(self, context):
        collision_objects = get_collision_objects()
        selection = context.selected_objects
        ct_props = context.scene.ct_properties
        final_capsule = []
        for obj in selection:
            if obj not in collision_objects or not obj.name.startswith("UCP_"):
                self.report({'WARNING'}, f"{obj.name} is not a collision object. Please select only capsule collision objects to regenerate.")
                continue
            
            active_obj = obj

            world_mx = active_obj.matrix_world.copy()
            parent_obj = active_obj.parent
            parent_inv = active_obj.matrix_parent_inverse.copy()

            capsule = add_capsule_collision(context, self)

            target_name = active_obj.name
            bpy.data.objects.remove(active_obj, do_unlink=True)
            capsule.parent = parent_obj
            capsule.matrix_parent_inverse = parent_inv
            capsule.matrix_world = world_mx
            capsule.name = target_name
            set_display(capsule, context)
            final_capsule.append(capsule)
        set_selection(final_capsule)        
        return {"FINISHED"}

class CT_KDOP_generate_collision(bpy.types.Operator):
    bl_idname = "ct.kdop_generate_collision"
    bl_label = "Generate k-DOP Collision Hull"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Generate a k-DOP collision hull for the selected object(s). k-DOPs (Discrete Oriented Polytopes) are a type of bounding volume that can provide a good balance between accuracy and performance for collision detection. The 'Inside Epsilon' setting can be increased if you find that the generated hull is missing parts of the original mesh, or decreased if the hull is too bloated."
    
    def execute(self, context):
        ct_props = context.scene.ct_properties
        selection = context.selected_objects
        if not selection or selection[0].type != "MESH":
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}
        

        if ct_props.multiple_selection_behavior == "ONE_COLLISION":
            c = [1]
            multiple = False
        elif ct_props.multiple_selection_behavior == "MULTIPLE_COLLISIONS":
            c = []
            multiple = True
            for obj in selection:
                c.append(obj)
        final_collision_objects = []
        for c in c:
            if multiple :
                bpy.ops.object.select_all(action='DESELECT')
                c.select_set(True)

            active_obj = context.view_layer.objects.active
            if active_obj and not multiple and active_obj in selection: 
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
            final_collision_objects.append(col_obj)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in final_collision_objects:
            obj.select_set(True)
        return {"FINISHED"}
    
class CT_SetCollisionVisibility(Operator):
    bl_idname = "ct.set_collision_visibility"
    bl_label = "Set Collision Visibility"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Toggle visibility of all collision objects in the viewport. This does not affect render visibility or export, it's just a helper to quickly hide/show all collision objects while working in the viewport without having to set up custom collections or manually hide them."

    visibility: bpy.props.BoolProperty(
        name="Visible",
        default=True,
        description="Set collision objects visibility in viewport",
    )

    def execute(self, context):
        set_collision_objects_visibility(self.visibility, context)
        return {"FINISHED"}

class CT_DeleteCollision(Operator):
    bl_idname = "ct.delete_collision"
    bl_label = "Delete Collision"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Delete all collision objects from the scene. If 'Selected Hierarchy' is enabled, it will only delete collision objects that are in the same hierarchy as the selected objects, which is useful to quickly clean up collision for specific assets without affecting the whole scene. Use with caution, especially if not using 'Selected Hierarchy', as this will permanently delete all collision objects in the scene without confirmation."

    selected_hierarchy: bpy.props.BoolProperty(
        name="Selected Hierarchy",
        default=False,
        description="Delete collision objects in the selected hierarchy instead of the whole scene",
    )

    def execute(self, context):
        collision_objects = get_collision_objects()
        if not collision_objects:
            self.report({"WARNING"}, "No collision objects detected.")
            return {"CANCELLED"}
        
        num_deleted = 0
        if not self.selected_hierarchy :
            for obj in collision_objects:
                bpy.data.objects.remove(obj, do_unlink=True)
                num_deleted += 1
        else :
            obj = get_top_parents(context.selected_objects)
            for obj in obj:
                for child in obj.children_recursive:
                    if child in collision_objects:
                        bpy.data.objects.remove(child, do_unlink=True)
                        num_deleted += 1

        self.report({"INFO"}, f"Deleted {num_deleted} collision objects.")
        return {"FINISHED"}

class CT_ConvertToUCX(Operator):
    bl_idname = "ct.convert_to_ucx"
    bl_label = "Convert to UCX Collision"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Convert the selected mesh object(s) to a convex collision mesh with a name starting with 'UCX'. This is useful for quickly creating collision meshes from existing geometry. The original mesh objects will be left in place, and the new collision meshes will be created as separate objects with the same transforms. Use with caution, as this can create very high-poly collision meshes if the original geometry is complex, which may not perform well in real-time applications."

    def execute(self, context):
        selection = context.selected_objects
        col_objects = get_collision_objects()
        if not selection:
            self.report({"WARNING"}, "No objects selected.")
            return {"CANCELLED"}

        final_collision_objects = []
        for obj in selection :            
            parent_mesh = obj.parent if (obj.parent and obj.parent.type == "MESH" and obj.parent not in col_objects) else None
            if not parent_mesh:
                self.report({"WARNING"}, f"{obj.name} is not attached to any mesh parent, skipped.")
                continue
            if obj in col_objects:
                self.report({"WARNING"}, f"{obj.name} is already a collision object, skipped.")
                continue
            base = parent_mesh.name
            obj.name = find_available_collision_name(base, prefix="UCX")
            set_display(obj, context)

        return {"FINISHED"}

_classes = (
    CT_AddCollisionToSelected,
    CT_GenerateConvexCollisionToSelected,
    CT_KDOP_generate_collision,
    CT_SetCollisionVisibility,
    CT_DeleteCollision,
    CT_Regenerate_Capsule_Collision,
    CT_ConvertToUCX,
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)