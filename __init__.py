import importlib
import bpy

bl_info = {
    "name": "Unreal Exporter",
    "author": "Tarmunds",
    "version": (5,1,0),
    "blender": (4, 5, 0),
    "location": "View3D > Tarmunds Addons > Export Unreal",
    "description": "Exports selected objects or hierarchies into separate files at the provided path. Include some other engine features. Now support collision primitives and rig export.",
    "doc_url": "https://tarmunds.gumroad.com/l/UnrealExporter",
    "tracker_url": "https://discord.gg/h39W5s5ZbQ",
    "category": "Import-Export",
}

_SubModules = [
    "Utils.PanelUtils",
    "UEE.Functions",
    "CT.Functions",
    "UEE.Properties",
    "UEE.Operators",
    "UEE.Panels",
    "CT.Properties",
    "CT.Operators",
    "CT.Panels",
] 

_modules = tuple(importlib.import_module(f".{name}", __name__) for name in _SubModules)

for module in _modules:
    importlib.reload(module)


class UEE_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_collision_tools: bpy.props.BoolProperty(
        name="Show Collision Tools Panel",
        default=True,
        description="Display the Collision Tools panel in the sidebar",
    )

    def draw(self, context):
        self.layout.prop(self, "show_collision_tools")


def register():
    bpy.utils.register_class(UEE_AddonPreferences)
    for module in _modules:
        if hasattr(module, "register"):
            module.register()

def unregister():
    for module in reversed(_modules):
        if hasattr(module, "unregister"):
            module.unregister()
    bpy.utils.unregister_class(UEE_AddonPreferences)