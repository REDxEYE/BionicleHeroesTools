import abc
import binascii
import contextlib
import io
import os
import struct
from pathlib import Path
from struct import calcsize, pack, unpack
from typing import Optional, Protocol, Union, TypeVar, Type


class Buffer(abc.ABC, io.RawIOBase):
    def __init__(self):
        io.RawIOBase.__init__(self)
        self._endian = '<'

    @contextlib.contextmanager
    def save_current_offset(self):
        entry = self.tell()
        yield
        self.seek(entry)

    @contextlib.contextmanager
    def read_from_offset(self, offset: int):
        entry = self.tell()
        self.seek(offset)
        yield
        self.seek(entry)

    @property
    @abc.abstractmethod
    def data(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def size(self):
        raise NotImplementedError()

    def remaining(self):
        return self.size() - self.tell()

    def is_empty(self):
        return self.remaining() == 0

    @property
    def preview(self):
        with self.save_current_offset():
            return binascii.hexlify(self.read(64), sep=' ', bytes_per_sep=4).decode('ascii').upper()

    def align(self, align_to):
        value = self.tell()
        padding = (align_to - value % align_to) % align_to
        self.seek(padding, io.SEEK_CUR)

    def skip(self, size):
        self.seek(size, io.SEEK_CUR)

    def read_fmt(self, fmt):
        return unpack(self._endian + fmt, self.read(calcsize(self._endian + fmt)))

    def _read(self, fmt):
        return unpack(self._endian + fmt, self.read(calcsize(self._endian + fmt)))[0]

    def read_relative_offset32(self):
        return self.tell() + self.read_uint32()

    def read_uint64(self):
        return self._read('Q')

    def read_int64(self):
        return self._read('q')

    def read_uint32(self):
        return self._read('I')

    def read_int32(self):
        return self._read('i')

    def read_uint16(self):
        return self._read('H')

    def read_int16(self):
        return self._read('h')

    def read_uint8(self):
        return self._read('B')

    def read_int8(self):
        return self._read('b')

    def read_float(self):
        return self._read('f')

    def read_double(self):
        return self._read('d')

    def read_ascii_string(self, length=None):
        if length is not None:
            buffer = self.read(length).strip(b'\x00').rstrip(b'\x00')
            if b'\x00' in buffer:
                buffer = buffer[:buffer.index(b'\x00')]
            return buffer.decode('latin', errors='replace')

        buffer = bytearray()

        while True:
            char = self.read(1)
            if not char or char == b"\x00":
                return buffer.decode('latin', errors='replace')
            buffer+=char

    def read_fourcc(self):
        return self.read_ascii_string(4)

    def write_fmt(self, fmt: str, *values):
        self.write(pack(self._endian + fmt, *values))

    def write_uint64(self, value):
        self.write_fmt('Q', value)

    def write_int64(self, value):
        self.write_fmt('q', value)

    def write_uint32(self, value):
        self.write_fmt('I', value)

    def write_int32(self, value):
        self.write_fmt('i', value)

    def write_uint16(self, value):
        self.write_fmt('H', value)

    def write_int16(self, value):
        self.write_fmt('h', value)

    def write_uint8(self, value):
        self.write_fmt('B', value)

    def write_int8(self, value):
        self.write_fmt('b', value)

    def write_float(self, value):
        self.write_fmt('f', value)

    def write_double(self, value):
        self.write_fmt('d', value)

    def write_ascii_string(self, string, zero_terminated=False, length=-1):
        pos = self.tell()
        for c in string:
            self.write(c.encode('ascii'))
        if zero_terminated:
            self.write(b'\x00')
        elif length != -1:
            to_fill = length - (self.tell() - pos)
            if to_fill > 0:
                for _ in range(to_fill):
                    self.write_uint8(0)

    def write_fourcc(self, fourcc):
        self.write_ascii_string(fourcc)

    def peek(self, size):
        with self.save_current_offset():
            return self.read(size)

    def peek_uint32(self):
        with self.save_current_offset():
            return self.read_uint32()

    def set_big_endian(self):
        self._endian = '>'

    def set_little_endian(self):
        self._endian = '<'

    def __bool__(self):
        return self.tell() < self.size()

    def slice(self, offset: Optional[int] = None, size: int = -1) -> 'BufferSlice':
        raise NotImplementedError

    def read_structure_array(self, offset, count, data_class: Type['Readable']):
        if count == 0:
            return []
        self.seek(offset)
        object_list = []
        for _ in range(count):
            obj = data_class.from_buffer(self)
            object_list.append(obj)
        return object_list


class BufferSlice(Buffer):
    def __init__(self, parent_offset: int):
        Buffer.__init__(self)
        self._parent_offset = parent_offset

    def abs_tell(self):
        return self.tell() + self._parent_offset


class MemoryBuffer(Buffer):

    def __init__(self, buffer: Union[bytes, bytearray, memoryview]):
        super().__init__()
        self._buffer = memoryview(buffer)
        self._offset = 0

    @property
    def data(self) -> memoryview:
        return self._buffer

    def size(self):
        return len(self._buffer)

    def _read(self, fmt: str):
        data = struct.unpack_from(self._endian + fmt, self._buffer, self._offset)
        self._offset += struct.calcsize(self._endian + fmt)
        return data[0]

    def read_fmt(self, fmt):
        data = struct.unpack_from(self._endian + fmt, self._buffer, self._offset)
        self._offset += struct.calcsize(self._endian + fmt)
        return data

    def write(self, _b: Union[bytes, bytearray]) -> Optional[int]:
        if self._offset + len(_b) > self.size():
            raise BufferError(f"Not enough space left({self.remaining()}) in buffer to write {len(_b)} bytes")
        self._buffer[self._offset:self._offset + len(_b)] = _b
        self._offset += len(_b)
        return len(_b)

    def read(self, _size: int = -1) -> Optional[bytes]:
        if _size == -1:
            data = self._buffer[self._offset:]
            self._offset += len(data)
            return data.tobytes()
        data = self._buffer[self._offset:self._offset + _size]
        self._offset += _size
        return data.tobytes()

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self._offset = offset
        elif whence == io.SEEK_CUR:
            self._offset += offset
        elif whence == io.SEEK_END:
            self._offset = self.size() - offset
        else:
            raise ValueError("Invalid whence argument")

        if self._offset > self.size():
            raise BufferError('Offset is out of bounds')

        return self._offset

    def __str__(self) -> str:
        return f'<MemoryBuffer {self.tell()}/{self.size()}>'

    def tell(self) -> int:
        return self._offset

    @property
    def closed(self) -> bool:
        return self._buffer is None

    def close(self) -> None:
        self._buffer = None

    def slice(self, offset: Optional[int] = None, size: int = -1) -> 'Buffer':
        if offset is None:
            offset = self._offset
        parent_offset = 0
        if isinstance(self, BufferSlice):
            parent_offset = self.abs_tell()
        if size == -1:
            return MemorySliceBuffer(self._buffer[offset:], offset + parent_offset)
        return MemorySliceBuffer(self._buffer[offset:offset + size], offset + parent_offset)


class MemorySliceBuffer(BufferSlice, MemoryBuffer):

    def __init__(self, buffer: Union[bytes, bytearray, memoryview], parent_offset: int):
        BufferSlice.__init__(self, parent_offset)
        MemoryBuffer.__init__(self, buffer)

    def __repr__(self):
        return f"MemorySliceBuffer(cursor={self.tell()}, size={self.size()})"


class WritableMemoryBuffer(io.BytesIO, Buffer):
    def __init__(self, initial_bytes=None):
        io.BytesIO.__init__(self, initial_bytes)
        Buffer.__init__(self)

    @property
    def data(self):
        return self.getbuffer()

    def size(self):
        return len(self.getbuffer())

    def slice(self, offset: Optional[int] = None, size: int = -1) -> 'Buffer':
        if offset is None:
            offset = self.tell()
        parent_offset = 0
        if isinstance(self, BufferSlice):
            parent_offset = self.abs_tell()
        if size == -1:
            return WritableMemorySliceBuffer(offset + parent_offset, self.data[offset:])
        return WritableMemorySliceBuffer(offset + parent_offset, self.data[offset:offset + size])


class WritableMemorySliceBuffer(BufferSlice, WritableMemoryBuffer):

    def __init__(self, parent_offset: int, initial_bytes: Optional[Union[bytes, memoryview, bytearray]] = None):
        BufferSlice.__init__(self, parent_offset)
        WritableMemoryBuffer.__init__(self, initial_bytes)


class FileBuffer(io.FileIO, Buffer):

    def __init__(self, file: Union[str, Path, int], mode: str = 'r', closefd: bool = True, opener=None) -> None:
        io.FileIO.__init__(self, file, mode, closefd, opener)
        Buffer.__init__(self)
        self._cached_size = None
        self._is_read_only = mode == "r" or mode == "rb"

    def size(self):
        if self._is_read_only:
            if self._cached_size is None:
                self._cached_size = os.fstat(self.fileno()).st_size
            return self._cached_size
        with self.save_current_offset():
            self.seek(0, io.SEEK_END)
            size = self.tell()
            return size

    def remaining(self):
        return self.size() - self.tell()

    @property
    def data(self):
        offset = self.tell()
        self.seek(0)
        _data = self.read()
        self.seek(offset)
        return _data

    def __str__(self) -> str:
        return f'<FileBuffer: {self.name!r} {self.tell()}/{self.size()}>'

    def slice(self, offset: Optional[int] = None, size: int = -1) -> 'Buffer':
        with self.save_current_offset():
            tell = self.tell()
            if offset is not None:
                self.seek(offset)

            if size == -1:
                return MemorySliceBuffer(self.read(), tell)
            return MemorySliceBuffer(self.read(size), tell)


T = TypeVar("T")


class Readable(Protocol):
    @classmethod
    def from_buffer(cls: Type[T], buffer: Buffer) -> T:
        ...


__all__ = ['Buffer', 'BufferSlice', 'MemoryBuffer', 'MemorySliceBuffer', 'WritableMemoryBuffer',
           'WritableMemorySliceBuffer', 'FileBuffer', 'Readable']
