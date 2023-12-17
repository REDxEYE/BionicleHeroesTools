from dataclasses import dataclass, field
from typing import List, Optional

from .file_utils import Buffer


@dataclass
class Chunk:
    name: str
    data: Buffer


@dataclass
class NU20:
    chunks: List[Chunk]

    @classmethod
    def from_buffer(cls, buffer: Buffer) -> 'NU20':
        ident = buffer.read_fourcc()
        assert ident == "NU20", f"Expected \"NU20\" got {ident!r}"
        fsize = -buffer.read_int32()
        assert fsize == buffer.size()
        assert buffer.read_uint32() == 1
        assert buffer.read_uint32() == 0
        chunks = []
        while True:
            name = buffer.read_fourcc()
            if not name:
                break
            size = buffer.read_uint32()
            if name == "VBIB" and size == 16:
                size = 48

            chunks.append(Chunk(name, buffer.slice(size=size - 8)))
            buffer.skip(size - 8)
        return cls(chunks)

    def find_chunk(self, name: str) -> Optional[Chunk]:
        for chunk in self.chunks:
            if chunk.name == name:
                return chunk
        return None
