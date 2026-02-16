import importlib

bl_info = {
    "name": "Unreal Exporter",
    "author": "Tarmunds",
    "version": (5,0,0),
    "blender": (4, 5, 0),
    "location": "View3D > Tarmunds Addons > Export Unreal",
    "description": "Exports selected objects or hierarchies into separate files at the provided path. Also include some option for Yup engine, and to join meshes before export.",
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

def register():
    for module in _modules:
        if hasattr(module, "register"):
            module.register()

def unregister():
    for module in reversed(_modules):
        if hasattr(module, "unregister"):
            module.unregister()