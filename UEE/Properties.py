import bpy
from bpy.props import (BoolProperty, FloatVectorProperty, EnumProperty, PointerProperty, IntProperty, StringProperty, FloatProperty)
from bpy.types import PropertyGroup


def update_export_path(self, context): 
    if self.export_path: 
        abspath = bpy.path.abspath(self.export_path) 
        self["export_path"] = abspath.strip()

def update_saved_paths_enum(self, context):
    items = [(str(i), path.name, "") for i, path in enumerate(self.saved_paths)]
    return items

class UEE_SavedPathItem(PropertyGroup):
    name: StringProperty(name="Saved Path")


class UEE_Properties(PropertyGroup):
    export_path: StringProperty(
        name="Export Path", 
        description="Directory where exported files will be saved", 
        default="", 
        maxlen=1024, 
        subtype='DIR_PATH',
        update=update_export_path
    )
    export_format: EnumProperty(
        name="Export Format",
        description="Choose export format", 
        items=[('FBX', 'FBX', 'Export as FBX file'), ('OBJ', 'OBJ', 'Export as OBJ file')], 
        default='FBX' 
    )
    saved_paths: bpy.props.CollectionProperty(
        type=UEE_SavedPathItem
    )
    saved_paths_enum: EnumProperty(
        items=update_saved_paths_enum,
        name="Saved Path",
        description="Select a saved path",
    )
    export_collision: BoolProperty(
        name="Export Collision",
        description="Export Collision object linked to selected obejcts",
        default=True,
    )
    export_sockets: BoolProperty(
        name="Export Sockets",
        description="Export Socket objects linked to selected obejcts",
        default=True,
    )
    enable_experimental_features: BoolProperty(
        name="Enable Experimental Features",
        description="Enable Experimental features, be crafeul those might not be fully shipped, but none of them can alter your blend file or work",
        default=False,
    )
    
    #panel bools
    path_options: BoolProperty(
        name="Path Options", 
        description="Toggle path options dropdown", 
        default=False 
    )
    advanced_options: BoolProperty(
        name="Advanced Options", 
        description="Toggle advanced export options", 
        default=False 
    )

    #option bools
    include_curve: BoolProperty(
        name="Include Curve Geometry",
        description="Allow export of curve geometry (if it has extrusion or other geometry)",
        default=False
    )
    y_up: BoolProperty(
        name="Y up",
        description="Pass the mesh through transform matrix to set Y as up axis",
        default=False
    )
    join_meshes: BoolProperty(
        name="Join Meshes",
        description="Join all selected meshes into the top parent before exporting. Work only with export Hierarchy. /!\ Warning this might take time depending of your modifier as it apply them all before exporting.",
        default=False
    )
    include_transform: BoolProperty(
        name="Include transform",
        description="Include location in the export (not recommended — pivot will not be at origin)", 
        default=False
    )
    #rig and animation settings
    export_rig: BoolProperty(
        name="Export Rig",
        description="Export Armature modifiers as Unreal Engine compatible rig",
        default=False,
    )
    rigged_asset_name: StringProperty(
        name="Rigged Asset Name",
        description="Name of the rigged asset to be exported",
        default=""
    )
    export_rigged_settings: EnumProperty(
        name="Rigged Asset Export Settings",
        description="Choose export settings for rigged assets",
        items=[
            ('UNREAL_SPACE', 'Unreal Space', 'Export rig in Unreal Engine space (Z up, X forward), centimeters scale'),
            ('BLENDER_SPACE', 'Blender Space', 'Export rig in Blender space (Z up, Y forward), metters scale'),
        ],
        default='BLENDER_SPACE'
    )
    rig_face_y: BoolProperty(
        name="Rig Face Y",
        description="Make the rig face Y forward (instead of X forward) when exporting in Unreal Space. Only works if 'Unreal Space' is selected in Rigged Asset Export Settings.",
        default=True,
    )
    export_only_rig: BoolProperty(
        name="Export Only Rig",
        description="Only export the rig (armature) without any mesh data",
        default=False,
    )


_classes = (
    UEE_SavedPathItem,
    UEE_Properties,
    )

def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.uee_properties = PointerProperty(type=UEE_Properties)


def unregister():
    del bpy.types.Scene.uee_properties
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)