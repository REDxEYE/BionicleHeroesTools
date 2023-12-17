from dataclasses import dataclass, field
from typing import Optional

from BionicleHeroesTools.file_utils import Buffer
from BionicleHeroesTools.nu20 import NU20
from BionicleHeroesTools.nup import Texture, NTBLChunk, TST0Chunk


@dataclass
class GHGModel:
    textures: list[Texture]
    nu20: NU20 = field(repr=False)
    ntbl: Optional[NTBLChunk] = field(repr=False)
    tst0: Optional[TST0Chunk] = field(repr=False)

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        nup_offset = buffer.read_uint32()
        count = buffer.read_uint16()
        textures = []
        # for _ in range(count):
        #     texture = Texture.from_buffer(buffer)
        #     texture.data = buffer.read(buffer.read_uint32())
        #     textures.append(texture)
        buffer.seek(nup_offset)
        buffer.skip(4)
        nu20 = NU20.from_buffer(buffer.slice())
        ntbl: Optional[NTBLChunk] = None
        tst0: Optional[TST0Chunk] = None
        ntbl_chunk = nu20.find_chunk("NTBL")
        if ntbl_chunk:
            ntbl = NTBLChunk.from_buffer(ntbl_chunk.data)
        # tst0_chunk = nu20.find_chunk("TST0") or nu20.find_chunk("TST2")
        # if tst0_chunk:
        #     tst0 = TST0Chunk.from_buffer(tst0_chunk.data)
        return cls(textures, nu20, ntbl,tst0)
