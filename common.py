from typing import Tuple

from .file_utils import Buffer


class Vector3(Tuple[float, float, float]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(buffer.read_fmt("3f"))

    def __repr__(self):
        return f"Vec3({self[0]:.3f}, {self[1]:.3f}, {self[2]:.3f})"


class Vector4(Tuple[float, float, float, float]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(buffer.read_fmt("4f"))

    def __repr__(self):
        return f"Vec3({self[0]:.3f}, {self[1]:.3f}, {self[2]:.3f}, {self[3]:.3f})"
