from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict

import numpy as np

from .common import Vector3
from .file_utils import Buffer, BufferSlice
from .nu20 import NU20


@dataclass
class Strip:
    unk2: int
    indices_count: int
    unk3: int
    unk4: int
    unk5: int
    indices_offset: int
    unk6: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        unk2 = buffer.read_uint32()
        indices_count = buffer.read_uint16()
        indices_count_dup = buffer.read_uint16()
        assert indices_count == indices_count_dup
        assert sum(buffer.read(44)) == 0
        unk3 = buffer.read_uint32()
        unk4 = buffer.read_uint32()
        assert buffer.read_uint32() == 0
        unk5 = buffer.read_uint32()
        indices_offset = buffer.read_uint32()
        unk6 = buffer.read_uint32()
        return cls(unk2, indices_count, unk3, unk4, unk5, indices_offset, unk6)


@dataclass
class Entry:
    strips: List[Strip]
    vertex_block_ids: List[int]

    material_id: int
    vertex_count: int
    vertex_size: int

    unk_0: int
    unk_1: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        assert buffer.read_uint32() == 0  # next
        assert buffer.read_uint32() == 0  # material
        material_id = buffer.read_uint32()
        assert buffer.read_uint32() == 0  # field_C
        vertex_count = buffer.read_uint32()
        vertex_count_dup = buffer.read_uint32()
        assert vertex_count_dup == vertex_count
        unk0 = buffer.read_uint32()
        # assert buffer.read_uint32() == 0  # field_18
        assert buffer.read_uint32() == 0  # field_1C
        assert buffer.read_uint32() == 0  # field_20
        assert buffer.read_uint32() == 0  # field_24
        assert buffer.read_uint32() == 0  # field_28
        next_offset = buffer.tell() + buffer.read_uint32()
        unk1 = buffer.read_uint32()
        # assert buffer.read_uint32() == 0  # field_30
        assert buffer.read_uint32() == 0  # field_34
        some_offset = buffer.read_uint32()
        assert some_offset == 0
        field_3c = buffer.read_uint32()  # potentially index block id
        assert field_3c == 0
        assert buffer.read_uint32() == 0  # field_40
        field_44 = buffer.read_uint32()
        vertex_block_ids = [buffer.read_int32() for _ in range(9)][:field_44]
        assert sum(buffer.read(28)) == 0
        vertex_size = buffer.read_uint32()
        assert sum(buffer.read(12)) == 0

        strips: List[Strip] = []
        assert next_offset != 0, "We should have at least one strip"
        buffer.seek(next_offset)
        if next_offset:
            while next_offset:
                next_offset = buffer.read_uint32()
                strips.append(Strip.from_buffer(buffer))

        return cls(strips, vertex_block_ids,
                   material_id, vertex_count, vertex_size, unk0, unk1)


@dataclass
class EntryV2:
    unk_0: int
    unk_1: int
    material_id: int
    unk_vec0: List[Tuple[float, float, float]] = field(repr=False)
    unk_vec1: List[Tuple[float, float, float]] = field(repr=False)

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        assert buffer.read_uint32() == 0, "This is internal engine \"next\" item pointer, should be zero in serialized data"
        assert buffer.read_uint32() == 0, "This is internal engine material pointer, should be zero in serialized data"
        material_id = buffer.read_uint32()
        unk0 = buffer.read_uint32()
        unk1 = buffer.read_uint32()
        count = buffer.read_uint32()
        assert buffer.read_uint32() == 0
        positions = []
        scale_and_color = []
        for _ in range(count):
            positions.append(buffer.read_fmt("3f"))
            scale_and_color.append(buffer.read_fmt("2f4B"))
        return cls(unk0, unk1, material_id, positions, scale_and_color)


@dataclass
class Container:
    type: int
    entries: List[Entry]
    entries_v2: List[EntryV2]
    bbox_min: Tuple[float, float, float]
    bbox_max: Tuple[float, float, float]
    unk_vec: Optional[Tuple[float, float, float]]

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        c_type = buffer.read_uint32()
        buffer.skip(12)
        flags = buffer.read_uint32()
        models = []
        billboards = []
        unk_vec = None
        if flags:
            if 0 < flags <= 2:
                something_count = buffer.read_uint32()
                unk_vec = [0, 0, 0]
                if c_type & 2 != 0:
                    unk_vec[0] = buffer.read_float()
                    unk_vec[1] = buffer.read_float()
                else:
                    buffer.skip(8)
                billboards = [EntryV2.from_buffer(buffer) for _ in range(something_count)]
        else:
            entry_count = buffer.read_uint32()
            unk_vec = buffer.read_fmt("3f")
            # assert unk_vec == (.0, .0, .0)
            buffer.skip(12)
            for _ in range(entry_count):
                models.append(Entry.from_buffer(buffer))
        bbox_min = Vector3.from_buffer(buffer)
        bbox_max = Vector3.from_buffer(buffer)
        buffer.skip(8)
        return cls(c_type, models, billboards, bbox_min, bbox_max, unk_vec)


class Obj0Chunk(List[Container]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        container_count = buffer.read_uint32()
        assert buffer.read_uint32() == 0
        containers = []
        for _ in range(container_count):
            containers.append(Container.from_buffer(buffer))
        return cls(containers)


@dataclass
class DataBuffer:
    buffer: BufferSlice
    id: int

    @classmethod
    def from_buffer(cls, buffer: Buffer, g_buffer_offset: int):
        buffer_size, buffer_id, buffer_offset = buffer.read_fmt("3I")
        return cls(buffer.slice(g_buffer_offset + buffer_offset, buffer_size), buffer_id)

    def read_vertices(self, vertex_dtype: np.dtype, count: int):
        self.buffer.seek(0)
        return np.frombuffer(self.buffer.read(), vertex_dtype, count)

    def read_indices(self, offset: int, count: int):
        self.buffer.seek(offset * 2)
        return self.buffer.read_fmt(f"{count}H")


@dataclass
class VBIBChunk:
    vertex_buffers: List[DataBuffer]
    index_buffers: List[DataBuffer]

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        entry = buffer.tell()
        vertex_blocks_count = buffer.read_uint32()
        index_blocks_count = buffer.read_uint32()
        total_buffer_size = buffer.read_uint32()

        vertex_blocks_offset, vertex_buffer_offset, vertex_buffer_size = buffer.read_fmt("3I")
        index_blocks_offset, index_buffer_offset, index_buffer_size = buffer.read_fmt("3I")
        assert buffer.read_uint32() == 0
        buffer.seek(entry + vertex_blocks_offset)
        vertex_buffers = [DataBuffer.from_buffer(buffer, entry + vertex_buffer_offset) for _ in
                          range(vertex_blocks_count)]
        buffer.seek(entry + index_blocks_offset)
        index_buffers = [DataBuffer.from_buffer(buffer, entry + index_buffer_offset) for _ in range(index_blocks_count)]
        return cls(vertex_buffers, index_buffers)


@dataclass
class Texture:
    width: int
    height: int
    unk2: int
    pixel_format: int
    offset: int
    data: bytes = field(init=False, repr=False)

    @classmethod
    def from_buffer(cls, buffer: BufferSlice):
        return cls(*buffer.read_fmt("2i3I"))


class TST0Chunk(List[Texture]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        entry = buffer.slice()
        texture_count, data_size, index_offset, texture_data_offset, raw_texture_size = entry.read_fmt("5I")
        entry.seek(index_offset)
        self = cls()
        for _ in range(texture_count):
            texture = Texture.from_buffer(entry)
            self.append(texture)
        texture_data = entry.slice(texture_data_offset, raw_texture_size)
        for i in range(texture_count):
            if i == texture_count - 1:
                size = raw_texture_size - self[i].offset
            else:
                size = self[i + 1].offset - self[i].offset
            texture_data.seek(self[i].offset)
            self[i].data = texture_data.read(size)
        return self


class NTBLChunk(Dict[int, str]):

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        size = buffer.read_uint32()
        data = buffer.slice(size=size)
        self = cls()
        while data:
            offset = data.tell()
            self[offset] = data.read_ascii_string()
        return self


@dataclass
class Instance:
    matrix: Tuple[Tuple[float, ...], ...] = field(repr=False)
    mesh_id: int
    flags: int
    unk0: int
    unk1: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls((buffer.read_fmt("4f"), buffer.read_fmt("4f"),
                    buffer.read_fmt("4f"), buffer.read_fmt("4f")),
                   *buffer.read_fmt("4I"))


class INSTChunk(List[Instance]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        count = buffer.read_uint32()
        assert buffer.read_uint32() == 0
        return cls([Instance.from_buffer(buffer) for _ in range(count)])


@dataclass
class Spec:
    matrix: Tuple[Tuple[float, ...], ...] = field(repr=False)
    instance_id: int
    name_offset: int
    unk0: int
    unk1: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls((buffer.read_fmt("4f"), buffer.read_fmt("4f"),
                    buffer.read_fmt("4f"), buffer.read_fmt("4f")), *buffer.read_fmt("2I2i"))


class SPECChunk(List[Spec]):

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        count = buffer.read_uint32()
        assert buffer.read_uint32() == 0
        return cls([Spec.from_buffer(buffer) for _ in range(count)])


@dataclass
class AnimatedTexture:
    unk: int
    unk1: int
    tex_id_offset: int
    frame_count: int
    unk2: int
    material_id: int
    unk3: int
    name_offset: str
    other_name_offset: str

    frames: List[int]

    @classmethod
    def from_buffer(cls, buffer: Buffer, buffer2: Buffer):
        items = buffer.read_fmt("3IHH4I")
        offset, count = items[2:4]
        buffer2.seek(offset * 2)
        return cls(*items, buffer2.read_fmt(f"{count}H"))


class TAS0Chunk(List[AnimatedTexture]):

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        count = buffer.read_uint32()
        assert buffer.read_uint32() == 0
        entry = buffer.slice(size=count * 32)
        buffer.skip(count * 32)
        count2 = buffer.read_uint32()
        entry2 = buffer.slice(size=count2 * 2)
        return cls([AnimatedTexture.from_buffer(entry, entry2) for _ in range(count)])


@dataclass
class DNO0Item:
    matrix: Tuple[Tuple[float, ...], ...] = field(repr=False)
    unk: Tuple[int, ...] = field(repr=False)

    @classmethod
    def from_buffer(cls, buffer_m: Buffer, buffer_d: Buffer):
        vec = (buffer_m.read_fmt("4f"), buffer_m.read_fmt("4f"),
               buffer_m.read_fmt("4f"), buffer_m.read_fmt("4f"))
        unk = buffer_d.read_fmt("30H")
        return cls(vec, unk)


class DNO0Chunk(List[DNO0Item]):

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        entry = buffer.slice()
        offset0 = buffer.read_uint32()
        entry.seek(offset0)
        count = entry.read_uint32()
        self = cls()
        tmp = []
        for i in range(count // 2):
            offset_m = entry.tell() + entry.read_int32()
            offset_d = entry.tell() + entry.read_int32()
            with entry.save_current_offset():
                entry.seek(offset_m)
                entry.seek(entry.tell() + entry.read_int32())
                tmp.append(entry.abs_tell())
                m_slice = entry.slice()
                entry.seek(offset_d)
                entry.seek(entry.tell() + entry.read_int32())
                tmp.append(entry.abs_tell())
                d_slice = entry.slice()
                self.append(DNO0Item.from_buffer(m_slice, d_slice))
        return self


class NKDTChunk(List[DNO0Item]):

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        entry = buffer.slice()
        offset0 = buffer.read_uint32()
        entry.seek(offset0)
        count = entry.read_uint32()
        self = cls()
        tmp = []
        for _ in range(count):
            offset = entry.tell() + entry.read_int32()
            with entry.save_current_offset():
                entry.seek(offset)
                entry.seek(entry.tell() + entry.read_int32())
                tmp.append(entry.abs_tell())
                m_slice = entry.slice()
        return self


@dataclass
class Material:
    flags: int
    color: Tuple[float, float, float]
    vertex_format: int
    texture_id0: int
    texture_id1: int
    texture_id2: int
    texture_id3: int
    texture_id4: int

    # @property
    # def transparent(self):
    #     return bool(self.flags & 1)

    # @property
    # def additive(self):
    #     return bool(self.flags & 2)

    @property
    def transparency(self):
        return bool(self.flags & 1)

    @property
    def transparent(self):
        return bool(self.flags & 0x2000)

    @property
    def additive(self):
        return bool(self.flags & 0x4000)

    # @property
    # def shiny(self):
    #     return bool(self.flags & 0x80000)

    @property
    def ignore_valpha(self):
        return bool(self.flags & 0x400000)

    @property
    def normal(self):
        return bool(self.vertex_format & 0x4)

    @property
    def packed_normal(self):
        return bool(self.vertex_format & 0x8 or self.vertex_format & 0x880000)

    @property
    def tangent(self):
        return bool(self.vertex_format & 0x10)

    @property
    def packed_tangent(self):
        return bool(self.vertex_format & 0x20 or self.vertex_format & 0x1000000)

    @property
    def binormal(self):
        return bool(self.vertex_format & 0x40)

    @property
    def packed_binormal(self):
        return bool(self.vertex_format & 0x80)

    @property
    def has_vcolors(self):
        return bool(self.vertex_format & 0x100)

    @property
    def has_vcolors2(self):
        return bool(self.vertex_format & 0x600)

    @property
    def uv_layer_count(self):
        return (self.vertex_format & 0x3800) >> 11

    @property
    def blend_weight(self):
        return bool(self.vertex_format & 0x4000)

    @property
    def packed_blend_weight(self):
        return bool(self.vertex_format & 0x8000)

    @property
    def blend_indices(self):
        return bool(self.vertex_format & 0x10000)

    @property
    def packed_blend_indices(self):
        return bool(self.vertex_format & 0x20000)

    @property
    def position2(self):
        return bool(self.vertex_format & 0x400000)

    @classmethod
    def from_buffer(cls, buffer: Buffer, approx_item_size: int):
        if approx_item_size == 180:
            entry = buffer.slice(size=180)
            entry.seek(64)
            texture_id0 = 0
            texture_id1, texture_id2, texture_id3, texture_id4 = 0, 0, 0, 0
            vertex_format = entry.read_uint32()
            buffer.skip(180)
            unk = 0
            vec = (1, 1, 1)
        else:
            entry = buffer.slice(size=532)
            entry.seek(0x40)
            unk = entry.read_uint32()
            texture_id0 = entry.read_uint32()
            assert sum(entry.read(12)) == 0
            vec = entry.read_fmt("3f")
            # assert sum(entry.read(20)) == 0
            entry.seek(0xBC)
            texture_id1, texture_id2, texture_id3, texture_id4 = entry.read_fmt("4I")
            entry.seek(0x1B8)
            vertex_format = entry.read_uint32()
            buffer.skip(532)
        return cls(unk, vec, vertex_format, texture_id0, texture_id1, texture_id2, texture_id3, texture_id4)

    def construct_vertex_dtype(self):

        vertex_dtype_items = [("pos", np.float32, (3,))]

        if self.packed_normal:
            vertex_dtype_items.append(("normal", np.uint8, (4,)))
        elif self.normal:
            vertex_dtype_items.append(("normal", np.float32, (3,)))

        if self.packed_tangent:
            vertex_dtype_items.append(("tangent", np.uint8, (4,)))
        elif self.tangent:
            vertex_dtype_items.append(("tangent", np.float32, (3,)))

        if self.packed_binormal:
            vertex_dtype_items.append(("binormal", np.uint8, (4,)))
        elif self.binormal:
            vertex_dtype_items.append(("binormal", np.float32, (3,)))

        if self.has_vcolors:
            vertex_dtype_items.append(("color", np.uint8, (4,)))
        if self.has_vcolors2:
            vertex_dtype_items.append(("color1", np.uint8, (4,)))

        for uv_layer in range(self.uv_layer_count):
            vertex_dtype_items.append((f"uv{uv_layer}", np.float32, (2,)))

        if self.packed_blend_weight:
            vertex_dtype_items.append(("weights", np.uint8, (4,)))
        elif self.blend_weight:
            vertex_dtype_items.append(("weights", np.float32, (2,)))

        if self.packed_blend_indices:
            vertex_dtype_items.append(("indices", np.uint8, (4,)))
        elif self.blend_indices:
            vertex_dtype_items.append(("indices", np.float32, (3,)))

        if self.position2:
            vertex_dtype_items.append(("pos1", np.float32, (3,)))

        return np.dtype(vertex_dtype_items)


class MS00Chunk(List[Material]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        count = buffer.read_uint32()
        assert buffer.read_uint32() == 0
        approx_item_size = buffer.remaining() // count
        self = cls()
        for _ in range(count):
            self.append(Material.from_buffer(buffer, approx_item_size))
        return self


@dataclass
class NupModel:
    nu20: NU20 = field(repr=False)
    ntbl: Optional[NTBLChunk] = field(repr=False)
    obj0: Optional[Obj0Chunk] = field(repr=False)
    vbib: Optional[VBIBChunk] = field(repr=False)
    tst0: Optional[TST0Chunk] = field(repr=False)
    inst: Optional[INSTChunk] = field(repr=False)
    spec: Optional[SPECChunk] = field(repr=False)
    tas0: Optional[TAS0Chunk] = field(repr=False)
    dno0: Optional[DNO0Chunk] = field(repr=False)
    nkdt: Optional[NKDTChunk] = field(repr=False)
    ms00: Optional[MS00Chunk] = field(repr=False)

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        nu20 = NU20.from_buffer(buffer)
        ntbl: Optional[NTBLChunk] = None
        obj0: Optional[Obj0Chunk] = None
        vbib: Optional[VBIBChunk] = None
        tst0: Optional[TST0Chunk] = None
        inst: Optional[INSTChunk] = None
        spec: Optional[SPECChunk] = None
        tas0: Optional[TAS0Chunk] = None
        dno0: Optional[DNO0Chunk] = None
        nkdt: Optional[NKDTChunk] = None
        ms00: Optional[MS00Chunk] = None
        ntbl_chunk = nu20.find_chunk("NTBL")
        if ntbl_chunk:
            ntbl = NTBLChunk.from_buffer(ntbl_chunk.data)
        obj0_chunk = nu20.find_chunk("OBJ0")
        if obj0_chunk:
            obj0 = Obj0Chunk.from_buffer(obj0_chunk.data)
        vbib_chunk = nu20.find_chunk("VBIB")
        if vbib_chunk:
            vbib = VBIBChunk.from_buffer(vbib_chunk.data)
        tst0_chunk = nu20.find_chunk("TST0") or nu20.find_chunk("TST2")
        if tst0_chunk:
            tst0 = TST0Chunk.from_buffer(tst0_chunk.data)
        inst_chunk = nu20.find_chunk("INST")
        if inst_chunk:
            inst = INSTChunk.from_buffer(inst_chunk.data)
        spec_chunk = nu20.find_chunk("SPEC")
        if spec_chunk:
            spec = SPECChunk.from_buffer(spec_chunk.data)
        tas0_chunk = nu20.find_chunk("TAS0")
        if tas0_chunk:
            tas0 = TAS0Chunk.from_buffer(tas0_chunk.data)
        # dno0_chunk = nu20.find_chunk("DNO2")
        # if dno0_chunk:
        #     dno0 = DNO0Chunk.from_buffer(dno0_chunk.data)
        # nkdt_chunk = nu20.find_chunk("NKDT")
        # if nkdt_chunk:
        #     nkdt = NKDTChunk.from_buffer(nkdt_chunk.data)
        ms00_chunk = nu20.find_chunk("MS00")
        if ms00_chunk:
            ms00 = MS00Chunk.from_buffer(ms00_chunk.data)

        return cls(nu20, ntbl, obj0, vbib, tst0, inst, spec, tas0, dno0, nkdt, ms00)
