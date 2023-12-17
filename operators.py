from pathlib import Path

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty, FloatProperty

from .load_hgp import import_hgp_from_path, import_hgp_from_buffer
from .load_nup import import_nup_from_path, import_nup_from_buffer
from .pak import Pak


class BH_OT_NupImport(bpy.types.Operator):
    bl_idname = "bh.nup_import"
    bl_label = "Import Bionicle:Heroes nup file"
    bl_options = {'UNDO'}

    filepath: StringProperty(subtype="FILE_PATH")
    files: CollectionProperty(name='File paths', type=bpy.types.OperatorFileListElement)
    filter_glob: StringProperty(default="*.nup;*.hgp", options={'HIDDEN'})

    def execute(self, context):
        if Path(self.filepath).is_file():
            directory = Path(self.filepath).parent.absolute()
        else:
            directory = Path(self.filepath).absolute()
        file = directory / self.filepath
        if file.suffix == ".nup":
            import_nup_from_path(file)
        else:
            import_hgp_from_path(file)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


class BH_OT_PakImport(bpy.types.Operator):
    bl_idname = "bh.pak_import"
    bl_label = "Import Bionicle:Heroes pak file"
    bl_options = {'UNDO'}

    filepath: StringProperty(subtype="FILE_PATH")
    files: CollectionProperty(name='File paths', type=bpy.types.OperatorFileListElement)
    filter_glob: StringProperty(default="*.pak", options={'HIDDEN'})

    def execute(self, context):
        if Path(self.filepath).is_file():
            directory = Path(self.filepath).parent.absolute()
        else:
            directory = Path(self.filepath).absolute()
        file = directory / self.filepath
        pak = Pak(file)
        for name, data in pak.files():
            if name.endswith("nup"):
                import_nup_from_buffer(file.parent, data)
            elif name.endswith("hgp"):
                import_hgp_from_buffer(Path(name).stem, file.parent, data)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


OPERATOR_CLASSES = (BH_OT_NupImport, BH_OT_PakImport)
