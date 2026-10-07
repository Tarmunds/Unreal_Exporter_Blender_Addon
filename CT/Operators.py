from multiprocessing import context
import bpy
import gpu
from bpy.types import Operator
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from .Functions import *
from ..UEE.Functions import restore_selection, convert_to_mesh, find_top_parent_in_one_hierarchy

class CT_AddCollisionToSelected(Operator):
    bl_idname = "ct.add_collision_to_selected"
    bl_label = "Add Collision to Selected"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Add a simple collision primitive to the selected object(s)"

    @classmethod
    def poll(cls, context):
        return method_object_not_collision(context)
    
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
    
    @classmethod
    def poll(cls, context):
        return method_object_not_collision(context)

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
            bpy.ops.mesh.select_all(action='SELECT')
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
        for obj in final_collision_objects:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)
            mesh = obj_eval.to_mesh()
            polygon_count = len(mesh.polygons)
            obj_eval.to_mesh_clear()
            self.report({'INFO'}, f"Generated {obj.name} convex collision object(s) with {polygon_count} polygons.")
        return {'FINISHED'}

class CT_Regenerate_Capsule_Collision(Operator):
    bl_idname = "ct.regenerate_capsule_collision"
    bl_label = "Regenerate Capsule Collision"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Regenerate capsule collision for the selected capsule collision object(s) using the current radius and height settings. This is useful to quickly update the collision mesh after changing the radius or height properties, without having to delete and re-add new capsule collisions."

    @classmethod
    def poll(cls, context):
        return method_is_capsule(context)
    
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
    
    @classmethod
    def poll(cls, context):
        return method_object_not_collision(context)

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
    socket_objects: bpy.props.BoolProperty(
        name="Delete Socket Objects",
        default=False,
        description="Delete sockets object instead of collision objects. This is useful to quickly clean up socket empties for specific assets without affecting the whole scene. Use with caution, as this will permanently delete all socket objects in the scene without confirmation.",
    )

    def execute(self, context):
        if not self.socket_objects:
            deletable_list = get_collision_objects()
        else:
            deletable_list = [o for o in bpy.data.objects if o.name.startswith("SOCKET_") and o.type == 'EMPTY']
        
        if not deletable_list:
            self.report({"WARNING"}, f"No {'socket' if self.socket_objects else 'collision'} objects detected.")
            return {"CANCELLED"}
        
        num_deleted = 0
        if not self.selected_hierarchy :
            for obj in deletable_list:
                bpy.data.objects.remove(obj, do_unlink=True)
                num_deleted += 1
        else :
            obj = get_top_parents(context.selected_objects)
            for obj in obj:
                for child in obj.children_recursive:
                    if child in deletable_list:
                        bpy.data.objects.remove(child, do_unlink=True)
                        num_deleted += 1

        self.report({"INFO"}, f"Deleted {num_deleted} {'socket' if self.socket_objects else 'collision'} objects.")
        return {"FINISHED"}

class CT_ConvertToUCX(Operator):
    bl_idname = "ct.convert_to_ucx"
    bl_label = "Convert / Rebind Collision"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Name the selected mesh object(s) after their mesh parent, so Unreal binds them as collision of that asset. Objects that already carry a collision prefix are renamed too whenever their name no longer matches their parent, which rebinds a collision that ended up on the wrong asset (the existing UBX/USP/UCP prefix is kept, plain meshes become UCX). Make a non-collision mesh the active object to reparent the selected collisions onto it in the same click"

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        selection = context.selected_objects
        col_objects = get_collision_objects()
        active = context.active_object
        # An active non-collision mesh is an explicit rebind target, but only when collisions
        # are selected alongside it. Otherwise a lone mesh child still converts against its
        # own parent instead of being treated as its own target.
        target = None
        if active and active.type == "MESH" and not check_if_collision(active):
            if any(o is not active and check_if_collision(o) for o in selection):
                target = active

        renamed = 0
        for obj in selection:
            if obj is target or obj.type != "MESH":
                continue

            if target and check_if_collision(obj) and obj.parent is not target:
                mw = obj.matrix_world.copy()
                obj.parent = target
                obj.matrix_parent_inverse = target.matrix_world.inverted_safe()
                obj.matrix_world = mw

            parent_mesh = obj.parent if (obj.parent and obj.parent.type == "MESH" and obj.parent not in col_objects) else None
            if not parent_mesh:
                self.report({"WARNING"}, f"{obj.name} is not attached to any mesh parent, skipped.")
                continue
            if name_matches_parent(obj, parent_mesh):
                continue
            obj.name = find_available_collision_name(parent_mesh.name, prefix=collision_prefix(obj) or "UCX")
            set_display(obj, context)
            renamed += 1

        self.report({"INFO"}, f"{renamed} collision object(s) bound to their parent.")
        return {"FINISHED"}

class CT_CollisionFromSelection(Operator):
    bl_idname = "ct.collision_from_selection"
    bl_label = "Collision from Selection"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Generate a collision hull from the vertices selected in Edit Mode, parented to the edited object. Slice an asset into several collision pieces by selecting one part, generating, then moving on to the next part"

    hull_type: bpy.props.EnumProperty(
        name="Hull Type",
        items=[
            ("CONVEX", "Convex", "Convex hull of the selected vertices"),
            ("KDOP", "k-DOP", "k-DOP hull of the selected vertices, using the k-DOP Mode setting"),
        ],
        default="CONVEX",
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.edit_object is not None

    def execute(self, context):
        ct_props = context.scene.ct_properties
        source_obj = context.edit_object
        verts = get_selected_verts(source_obj, space=ct_props.kdop_space)
        if len(verts) < 4:
            self.report({"WARNING"}, "Select at least 4 vertices.")
            return {"CANCELLED"}

        if self.hull_type == "KDOP":
            planes = build_kdop_planes(verts, kdop_directions(ct_props.kdop_mode))
            points = generate_kdop_points(planes, inside_eps=ct_props.kdop_inside_epsilon)
            if len(points) < 4:
                self.report({"ERROR"}, f"Not enough hull points generated ({len(points)}). Try another DOP type or increase Inside Epsilon.")
                return {"CANCELLED"}
        else:
            points = verts

        if ct_props.kdop_space == "WORLD":
            inv = source_obj.matrix_world.inverted_safe()
            points = [inv @ p for p in points]

        hull_mesh = build_convex_hull_mesh_from_points(points, name=f"{source_obj.name}_COL_MESH")
        if hull_mesh is None:
            self.report({"ERROR"}, "Failed to build convex hull mesh")
            return {"CANCELLED"}

        col_name = find_available_collision_name(source_obj.name, prefix="UCX")
        col_obj = create_collision_object(source_obj, hull_mesh, col_name, context=context)
        col_obj.matrix_world = source_obj.matrix_world.copy()
        col_obj.parent = source_obj
        col_obj.matrix_parent_inverse = source_obj.matrix_world.inverted_safe()

        self.report({"INFO"}, f"Generated {col_obj.name} from {len(verts)} selected vertices.")
        return {"FINISHED"}

def _draw_slice_line(op, context):
    if not op.dragging:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')
    gpu.state.line_width_set(2.0)
    batch = batch_for_shader(shader, 'LINES', {"pos": [op.start, op.end]})
    shader.bind()
    shader.uniform_float("color", (1.0, 0.55, 0.1, 1.0))
    batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


class CT_SliceCollision(Operator):
    bl_idname = "ct.slice_collision"
    bl_label = "Slice Collision"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Carve the active mesh into convex collision pieces by drawing cuts in the viewport. Drag a line to cut along the plane you see, orbit with the middle mouse between cuts and keep drawing. Each piece is rebuilt from the source geometry inside it, so pieces hug the asset instead of inheriting one bloated hull. C and W toggle the collision colour and wireframe, + and - retune the face budget live. Enter or Esc ends the session and keeps the pieces"

    # Drag shorter than this is a misclick, not a cut.
    MIN_DRAG_PX = 8

    DISPLAY_KEYS = {'C': "color_display", 'W': "wire_display"}
    # Letters only: bracket and numpad keys need AltGr on AZERTY, and numpad +/- is zoom.
    BUDGET_KEY = 'F'
    BUDGET_STEP = 5

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            context.mode == 'OBJECT'
            and context.area is not None
            and context.area.type == 'VIEW_3D'
            and obj is not None
            and obj.type == 'MESH'
            and not check_if_collision(obj)
            and not obj.name.startswith("SOCKET_")
        )

    def invoke(self, context, event):
        self.source = context.active_object
        self.region = next((r for r in context.area.regions if r.type == 'WINDOW'), None)
        self.rv3d = self.region.data if self.region else None
        if self.region is None or self.rv3d is None:
            self.report({"ERROR"}, "No 3D viewport region to draw in.")
            return {"CANCELLED"}

        self.dragging = False
        self.start = Vector((0.0, 0.0))
        self.end = Vector((0.0, 0.0))
        self.cuts = 0
        # One entry per cut: the regions as they were before it, bmeshes included, so
        # Ctrl+Z restores a state instead of re-slicing the source from the plane list.
        self.history = []

        # A previous session's pieces are replaced, hand made collisions are left alone.
        for piece in get_slice_pieces(self.source):
            bpy.data.objects.remove(piece, do_unlink=True)

        # One region per piece: the planes that bound it, the clipped source geometry
        # cached as a bmesh, and the collision object showing it.
        base = source_bmesh(self.source, context)
        self.regions = [{"planes": [], "bm": base, "obj": None}]
        self.rebuild(context, self.regions)
        if self.regions[0]["obj"] is None:
            base.free()
            self.report({"ERROR"}, f"{self.source.name} has no hullable geometry.")
            return {"CANCELLED"}

        self._handler = bpy.types.SpaceView3D.draw_handler_add(
            _draw_slice_line, (self, context), 'WINDOW', 'POST_PIXEL'
        )
        context.window_manager.modal_handler_add(self)
        self.set_header(context)
        return {"RUNNING_MODAL"}

    def set_header(self, context):
        context.area.header_text_set(
            "Slice: drag to cut  |  Ctrl+Z undo cut  |  C color  |  W wireframe"
            f"  |  F / Shift+F face budget ({context.scene.ct_properties.target_face_count})"
            "  |  Enter or Esc to finish"
        )

    def snapshot(self):
        return [{"planes": list(r["planes"]), "bm": r["bm"].copy()} for r in self.regions]

    def undo_cut(self, context):
        if not self.history:
            self.report({"INFO"}, "No cut to undo.")
            return
        for region in self.regions:
            if region["obj"] is not None:
                bpy.data.objects.remove(region["obj"], do_unlink=True)
            region["bm"].free()
        self.regions = [{"planes": r["planes"], "bm": r["bm"], "obj": None} for r in self.history.pop()]
        self.rebuild(context, self.regions)
        self.cuts -= 1
        self.region.tag_redraw()

    def rebuild(self, context, regions):
        """Give every listed region a fresh collision object."""
        for region in regions:
            if region["obj"] is not None:
                bpy.data.objects.remove(region["obj"], do_unlink=True)
            region["obj"] = slice_collision_piece(region["bm"], self.source, context)

    def apply_cut(self, context):
        plane = view_cut_plane(self.region, self.rv3d, self.start, self.end)
        if plane is None:
            return
        co, normal = world_plane_to_local(self.source, *plane)

        before = self.snapshot()
        regions, retired = split_slice_regions(self.regions, co, normal)
        fresh = [r for r in regions if r["obj"] is None]
        if not fresh:                       # the plane missed the asset entirely
            for region in before:
                region["bm"].free()
            return
        self.history.append(before)

        for obj in retired:
            bpy.data.objects.remove(obj, do_unlink=True)
        self.regions = regions
        self.rebuild(context, fresh)
        self.cuts += 1

        for region in self.regions:         # drop regions whose hull came out degenerate
            if region["obj"] is None:
                region["bm"].free()
        self.regions = [r for r in self.regions if r["obj"] is not None]

    def in_region(self, event):
        x = event.mouse_x - self.region.x
        y = event.mouse_y - self.region.y
        return 0 <= x <= self.region.width and 0 <= y <= self.region.height

    def mouse(self, event):
        return Vector((event.mouse_x - self.region.x, event.mouse_y - self.region.y))

    def modal(self, context, event):
        if event.type in {'RET', 'NUMPAD_ENTER', 'ESC'}:
            if event.value == 'PRESS':
                return self.finish(context)
            return {'RUNNING_MODAL'}

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} or event.type.startswith('NUMPAD_'):
            return {'PASS_THROUGH'}

        # Display toggles, so the pieces can be read while carving. Their property update
        # callbacks re-run set_display over every collision object, slices included.
        if event.value == 'PRESS' and event.type in self.DISPLAY_KEYS:
            prop = self.DISPLAY_KEYS[event.type]
            ct_props = context.scene.ct_properties
            setattr(ct_props, prop, not getattr(ct_props, prop))
            self.region.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.value == 'PRESS' and event.type == 'Z' and event.ctrl:
            self.undo_cut(context)
            return {'RUNNING_MODAL'}

        # Face budget, retuned live: the hulls do not change, only their decimate ratio,
        # so this is a modifier tweak per piece rather than a re-slice.
        if event.value == 'PRESS' and event.type == self.BUDGET_KEY:
            ct_props = context.scene.ct_properties
            step = -self.BUDGET_STEP if event.shift else self.BUDGET_STEP
            ct_props.target_face_count = ct_props.target_face_count + step   # property clamps
            for region in self.regions:
                if region["obj"] is not None:
                    budget_collision_faces(region["obj"], ct_props.target_face_count)
            self.set_header(context)
            self.region.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            if self.dragging:
                self.end = self.mouse(event)
                self.region.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                if not self.in_region(event):
                    return {'PASS_THROUGH'}
                self.dragging = True
                self.start = self.mouse(event)
                self.end = self.start.copy()
            elif event.value == 'RELEASE' and self.dragging:
                self.dragging = False
                self.end = self.mouse(event)
                if (self.end - self.start).length >= self.MIN_DRAG_PX:
                    self.apply_cut(context)
                self.region.tag_redraw()
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
        context.area.header_text_set(None)
        self.region.tag_redraw()
        pieces = [r["obj"] for r in self.regions if r["obj"] is not None]
        for region in self.regions:
            region["bm"].free()
        for state in self.history:
            for region in state:
                region["bm"].free()
        self.history.clear()
        set_selection(pieces)
        self.report({"INFO"}, f"{self.cuts} cut(s), {len(pieces)} collision piece(s) on {self.source.name}.")
        return {"FINISHED"}


class CT_AddSocketToSelected(Operator):
    bl_idname = "ct.add_socket_to_selected"
    bl_label = "Add Socket to Selected"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects and all(obj.type == "MESH" for obj in context.selected_objects if obj not in get_collision_objects())

    def execute(self, context):
        ct_props = context.scene.ct_properties
        selection = context.selected_objects
        if not selection:
            self.report({"WARNING"}, "No objects selected.")
            return {"CANCELLED"}

        target = context.active_object if context.active_object in selection else selection[0]
        if target.type != "MESH" or target in get_collision_objects() or target.name.startswith("SOCKET_"):
            self.report({"WARNING"}, "Active object must be a mesh and not a collision or socket object.")
            return {"CANCELLED"}

        socket_name = find_available_collision_name(target.name, prefix="SOCKET_")

        if ct_props.socket_at_cursor:
            desired_world_pos = context.scene.cursor.location.copy()
        else:
            desired_world_pos = target.matrix_world.translation.copy()

        bpy.ops.object.empty_add(type='PLAIN_AXES', location=desired_world_pos)
        socket = context.view_layer.objects.active
        socket.name = socket_name

        socket.parent = target
        socket.matrix_parent_inverse = target.matrix_world.inverted_safe()

        socket.rotation_euler = (0.0, 0.0, 0.0)
        socket.scale = (1.0, 1.0, 1.0)

        set_display_socket(socket, context)
        return {"FINISHED"}


_classes = (
    CT_AddCollisionToSelected,
    CT_AddSocketToSelected,
    CT_GenerateConvexCollisionToSelected,
    CT_KDOP_generate_collision,
    CT_SetCollisionVisibility,
    CT_DeleteCollision,
    CT_Regenerate_Capsule_Collision,
    CT_ConvertToUCX,
    CT_CollisionFromSelection,
    CT_SliceCollision,
)

def register():
    for c in _classes: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_classes): bpy.utils.unregister_class(c)