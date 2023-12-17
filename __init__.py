from .operators import OPERATOR_CLASSES, BH_OT_NupImport

bl_info = {
    "name": "Bionicle:Heroes toolkit",
    "author": "REDxEYE,",
    "version": (0, 0, 1),
    "blender": (3, 1, 0),
    "description": "Import Bionicle:Heroes assets.",
    "category": "Import-Export"
}

import bpy

ALL_CLASSES = OPERATOR_CLASSES  # + UI_CLASSES

register_, unregister_ = bpy.utils.register_classes_factory(ALL_CLASSES)


def menu_import(self, context):
    self.layout.operator(BH_OT_NupImport.bl_idname, text="Bionicle Model (.nup/.hgp)")


def register():
    register_()
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    # bpy.types.TOPBAR_MT_file_export.append(menu_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    # bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    unregister_()
