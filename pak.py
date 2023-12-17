import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from BionicleHeroesTools.file_utils import FileBuffer, Buffer


@dataclass
class Entry:
    name: str
    offset: int
    size: int


class Pak:

    def __init__(self, path: Path):
        self._path = path
        self._buffer = FileBuffer(path)

        ident, file_count = self._buffer.read_fmt("2I")
        if ident != 305419898:
            raise ValueError("Not a pak file")
        self._entries: dict[str, Entry] = {}
        self._buffer.seek(0x18)
        for _ in range(file_count):
            name_offset, file_offset, file_size = self._buffer.read_fmt("3I")
            self._buffer.skip(0x10)
            with self._buffer.read_from_offset(name_offset):
                name = self._buffer.read_ascii_string()
            self._entries[name] = Entry(name, file_offset, file_size)

    def get(self, name: str) -> Optional[Buffer]:
        if name in self._entries:
            entry = self._entries[name]
            return self._buffer.slice(entry.offset, entry.size)
        return None

    def glob(self, pattern: str):
        for name, entry in self._entries.items():
            if fnmatch.fnmatch(name, pattern):
                yield name, self.get(name)

    def files(self):
        for name, entry in self._entries.items():
            yield name, self.get(name)
