bl_info = {
    "name": "GEM2 Engine PLY",
    "author": "1Lt. Muhammad",
    "version": (0, 4, 0),
    "blender": (4, 5, 4),
    "location": "File > Import-Export",
    "description": "GEM2 Engine O PLY Files",
    "warning": "",
    "doc_url": "",
    "support": 'Community',
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    if "ply_export" in locals():
        importlib.reload(ply_export)

import bpy
from bpy.app.translations import pgettext_tip as tip_
from bpy.props import (
    StringProperty,
    CollectionProperty,
)
from bpy_extras.io_utils import (
    ExportHelper,
    poll_file_object_drop,
)


class ExportGEM2PLY(bpy.types.Operator, ExportHelper):
    """Export a GEM2 Engine PLY file"""
    bl_idname = "export_scene.gem2ply"
    bl_label = "Export PLY"
    bl_options = {'UNDO'}

    directory: StringProperty(
        subtype='DIR_PATH',
        options={'HIDDEN'},
    )

    filename_ext = ""

    def execute(self, context):
        keywords = self.as_keywords(ignore=("filter_glob", "directory", "ui_tab"))

        from . import ply_export

        if self.directory:
            return ply_export.export(self.directory, self)


class IO_FH_gem2ply(bpy.types.FileHandler):
    bl_idname = "IO_FH_gem2ply"
    bl_label = "PLY"
    bl_export_operator = "export_scene.gem2ply"
    bl_file_extensions = ".ply"

    @classmethod
    def poll_drop(cls, context):
        return poll_file_object_drop(context)


def menu_func_export(self, context):
    self.layout.operator(ExportGEM2PLY.bl_idname, text="GEM2 Engine (.ply)")


classes = (
    ExportGEM2PLY,
    IO_FH_gem2ply,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
