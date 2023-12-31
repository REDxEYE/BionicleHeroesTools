from dataclasses import dataclass, field
from typing import Optional

from BionicleHeroesTools.common import Vector3
from BionicleHeroesTools.file_utils import Buffer
from BionicleHeroesTools.nup import Material, TST0Chunk, VBIBChunk, Texture, DataBuffer, NupMesh, Container


@dataclass
class Bone:
    matrix: tuple[tuple[float, ...], ...]
    unk_f: Vector3
    name: str
    parent: int
    flags: int
    unk_i: tuple[int, int, int, int]
    matrix1: tuple[tuple[float, ...], ...] = field(init=False)
    matrix2: tuple[tuple[float, ...], ...] = field(init=False)

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        matrix = buffer.read_fmt("4f"), buffer.read_fmt("4f"), buffer.read_fmt("4f"), buffer.read_fmt("4f")
        unk = Vector3.from_buffer(buffer)
        with buffer.read_from_offset(buffer.read_uint32()):
            name = buffer.read_ascii_string()
        parent, flags, *unk2 = buffer.read_fmt("bBH3I")
        return cls(matrix, unk, name, parent, flags, unk2)


@dataclass
class Model:
    gap0: int
    field_4: int
    field_8: int
    meshes: list[NupMesh]
    field_10: int
    bbox_max: Vector3
    bbox_min: Vector3
    floats: tuple[float, ...]
    field_48: int
    field_4C: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        gap0, field_4, field_8, model_entry_offset, field_10 = buffer.read_fmt("5I")
        bbox_max, bbox_min = Vector3.from_buffer(buffer), Vector3.from_buffer(buffer)
        *floats, field_48, field_4C = buffer.read_fmt("7f")
        meshes = []
        with buffer.read_from_offset(model_entry_offset):
            next_offset = model_entry_offset
            while True:
                buffer.seek(next_offset)
                next_offset = buffer.read_uint32()
                mesh = NupMesh.from_hgp_buffer(buffer)
                meshes.append(mesh)
                if not next_offset:
                    break
        return cls(gap0, field_4, field_8, meshes, field_10, bbox_max, bbox_min, floats, field_48, field_4C)


class Layer:
    @staticmethod
    def from_buffer(buffer: Buffer, bone_count: int):
        field_0, bone_models_offset, model_entry_offset, bone_models2_offset, model_entry2_offset = buffer.read_fmt(
            "5I")
        models = []
        bone_models = []
        if bone_models_offset:
            bone_model = []
            bone_models.append(bone_model)
            with buffer.read_from_offset(bone_models_offset):
                offsets = buffer.read_fmt(f"{bone_count}I")
                for offset in offsets:
                    if not offset:
                        bone_model.append(None)
                        continue
                    buffer.seek(offset)
                    bone_model.append(Container.from_hgp_buffer(buffer))
        if model_entry_offset:
            with buffer.read_from_offset(model_entry_offset):
                models.append(Container.from_hgp_buffer(buffer))

        if bone_models2_offset:
            bone_model = []
            bone_models.append(bone_model)
            with buffer.read_from_offset(bone_models2_offset):
                offsets = buffer.read_fmt(f"{bone_count}I")
                for offset in offsets:
                    if not offset:
                        bone_model.append(None)
                        continue
                    buffer.seek(offset)
                    bone_model.append(Container.from_hgp_buffer(buffer))
        if model_entry2_offset:
            with buffer.read_from_offset(model_entry2_offset):
                models.append(Container.from_hgp_buffer(buffer))
        return models, bone_models


@dataclass
class Attachment:
    name: str
    matrix: tuple[tuple[float, ...], ...]
    unk0: int
    unk1: int
    unk2: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        matrix = buffer.read_fmt("4f"), buffer.read_fmt("4f"), buffer.read_fmt("4f"), buffer.read_fmt("4f")
        name_offset, unk0, unk1, unk2 = buffer.read_fmt("4I")
        with buffer.read_from_offset(name_offset):
            name = buffer.read_ascii_string()
        return cls(name, matrix, unk0, unk1, unk2)


@dataclass
class HGPModel:
    materials: list[Material]
    textures: list[Texture]
    vertex_buffers: list[DataBuffer]
    index_buffers: list[DataBuffer]
    bones: list[Bone]
    attachments: list[Attachment]
    layers: list[tuple[list[Container], list[list[Optional[Container]]]]]

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        filesize = buffer.read_uint32()
        ident = buffer.read_ascii_string(4)
        assert ident == "NU20"
        (version, chunks_offset, materials_count,
         materials_offset, bone_count, bone_offset,
         matrices_offset, matrices2_offset, unk2, unk3, name_table,
         unk4, unk5, unk6, attachment_count, attachment_offset,
         layer_count, layer_offset) = buffer.read_fmt("18I")
        materials = []
        with buffer.read_from_offset(materials_offset):
            material_offsets = buffer.read_fmt(f"{materials_count}I")
            for material_offset in material_offsets:
                buffer.seek(material_offset)
                materials.append(Material.from_buffer(buffer, 532))
        with buffer.read_from_offset(chunks_offset):
            tst0_offset = buffer.read_uint32()
            vbib_offset = buffer.read_uint32()
            buffer.seek(tst0_offset)
            tst = TST0Chunk.from_buffer(buffer)
            buffer.seek(vbib_offset)
            vbib = VBIBChunk.from_buffer(buffer)
        bones = []
        with buffer.read_from_offset(bone_offset):
            for _ in range(bone_count):
                bones.append(Bone.from_buffer(buffer))
        with buffer.read_from_offset(matrices_offset):
            for i in range(bone_count):
                bones[i].matrix1 = buffer.read_fmt("4f"), buffer.read_fmt("4f"), buffer.read_fmt("4f"), buffer.read_fmt(
                    "4f")
        with buffer.read_from_offset(matrices2_offset):
            for i in range(bone_count):
                bones[i].matrix2 = buffer.read_fmt("4f"), buffer.read_fmt("4f"), buffer.read_fmt("4f"), buffer.read_fmt(
                    "4f")
        attachments = []
        with buffer.read_from_offset(attachment_offset):
            for _ in range(attachment_count):
                attachments.append(Attachment.from_buffer(buffer))
        layers = []
        with buffer.read_from_offset(layer_offset):
            for _ in range(layer_count):
                layers.append(Layer.from_buffer(buffer, bone_count))
        return cls(materials, tst, vbib.vertex_buffers, vbib.index_buffers, bones, attachments, layers)
