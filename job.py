from dataclasses import dataclass, field
from enum import IntFlag
from typing import Optional, List, Tuple

from .common import Vector3
from .file_utils import Buffer, BufferSlice


def read_sstring(buffer: Buffer):
    return buffer.read_ascii_string(buffer.read_uint32())


@dataclass
class Record:
    buffer: BufferSlice
    name: str

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        size = buffer.read_uint32()
        data = buffer.slice(size=size - 4)
        name = read_sstring(data)
        buffer.skip(size - 4)
        return cls(data, name)


@dataclass
class StreamInfo:
    record_count: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls(record.buffer.read_uint32())


@dataclass
class FileInfo:
    unk: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        return cls(record.buffer.read_uint32())


@dataclass
class Settings:
    unk0: float
    unk1: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        return cls(record.buffer.read_float(), record.buffer.read_uint32())


@dataclass(repr=False)
class Editor:
    name: str

    def __repr__(self):
        return f"Editor({self.name!r})"


@dataclass
class Type:
    name: str

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        return cls(read_sstring(record.buffer))

    def __repr__(self):
        return self.name


class TypeList(List[Type]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        count = record.buffer.read_uint32()
        self = cls()
        for _ in range(count):
            self.append(Type.from_buffer(record.buffer))
        assert record.buffer.is_empty()
        return self


@dataclass
class Member:
    type_id: int = field(repr=False)
    type: Type = field(init=False)
    name: str
    offset: int
    unk0: int
    unk1: int

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        return cls(buffer.read_uint32(), read_sstring(buffer), *buffer.read_fmt("3I"))


@dataclass
class Class:
    name: str
    members: List[Member]

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        name = read_sstring(record.buffer)
        member_count = record.buffer.read_uint32()
        members = []
        for _ in range(member_count):
            members.append(Member.from_buffer(record.buffer))
        assert record.buffer.is_empty()
        return cls(name, sorted(members, key=lambda a: a.offset))


class ClassList(List[Class]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        count = record.buffer.read_uint32()
        self = cls()
        for _ in range(count):
            self.append(Class.from_buffer(record.buffer))
        assert record.buffer.is_empty()
        return self


@dataclass
class Object:
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        raise NotImplementedError()


class ObjectList(List[Object]):
    name: str

    def __repr__(self):
        return f"{self.name}({list.__repr__(self)})"

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        count = record.buffer.read_uint32()
        self = cls()
        self.name = record.name
        for _ in range(count):
            self.append(Object.from_buffer(record.buffer))
        assert record.buffer.is_empty()
        return self


@dataclass(repr=False)
class ClassEditor(Editor):
    types: TypeList
    classes: ClassList

    object_list0: ObjectList
    object_list1: ObjectList
    object_list2: ObjectList

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        type_list = TypeList.from_buffer(record.buffer)
        class_list = ClassList.from_buffer(record.buffer)
        for clazz in class_list:
            for member in clazz.members:
                member.type = type_list[member.type_id]
        return cls(record.name, type_list, class_list,
                   ObjectList.from_buffer(record.buffer),
                   ObjectList.from_buffer(record.buffer),
                   ObjectList.from_buffer(record.buffer))


class InstFlags(IntFlag):
    Die_when_stopped = 0x1
    Collide_with_Characters = 0x2
    Interact_only_with_Active_Chars = 0x4
    Damage_Characters = 0x8
    Dont_die_when_off_screen = 0x10
    Is_a_Collectible = 0x20
    Rotate_Randomly = 0x40
    Ordered_Rotate_Randomly = 0x80
    No_Bounce = 0x100
    Slot_Cannot_be_Stolen = 0x200
    Ignore_Terrain = 0x400
    Face_Direction_of_Movement = 0x800
    Disable_Draw = 0x1000
    Real_Time_Lighting = 0x2000
    Ignore_Creature = 0x4000
    Thrown = 0x8000
    Can_Damage_Owner = 0x10000


@dataclass
class Spline:
    name: str
    flags: InstFlags
    unk1: int
    unk2: int
    unk3: float
    unk4: float
    points: List[Tuple[Vector3, Vector3, Vector3, float]]

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        name = read_sstring(record.buffer)
        point_count, flags, unk1, unk2, unk3, unk4 = record.buffer.read_fmt("5If")
        points = []
        for _ in range(point_count):
            points.append((Vector3.from_buffer(record.buffer), Vector3.from_buffer(record.buffer),
                           Vector3.from_buffer(record.buffer), record.buffer.read_float()))
        return cls(name, InstFlags(flags), unk1, unk2, unk3, unk4, points)


@dataclass
class SplineList:
    name: str
    splines: List[Spline]
    points: List[Tuple[Vector3, Tuple[int, int, int, int]]]

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        spline_count = record.buffer.read_uint32()
        point_count = record.buffer.read_uint32()
        unk1 = record.buffer.read_uint32()
        splines = []
        points = []
        for _ in range(spline_count):
            splines.append(Spline.from_buffer(record.buffer))
        points_record = Record.from_buffer(record.buffer)
        for _ in range(point_count):
            points.append((Vector3.from_buffer(points_record.buffer), points_record.buffer.read_fmt("4B")))
        assert points_record.buffer.is_empty()
        assert record.buffer.is_empty()
        return cls(record.name, splines, points)


@dataclass(repr=False)
class SplineEditor(Editor):
    splines: SplineList

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        item_record = Record.from_buffer(record.buffer)
        if item_record.name != "Splines":
            print(f"Unexpected spline editor record({item_record.name!r})")
        spline_list = SplineList.from_record(item_record)
        assert record.buffer.is_empty()
        return cls(record.name, spline_list)


class Editors(List[Editor]):
    @classmethod
    def from_buffer(cls, buffer: Buffer):
        record = Record.from_buffer(buffer)
        return cls.from_record(record)

    @classmethod
    def from_record(cls, record: Record):
        count = record.buffer.read_uint32()
        self = cls()
        for _ in range(count):
            editor_record = Record.from_buffer(record.buffer)
            if editor_record.name == "Class Editor":
                self.append(ClassEditor.from_record(editor_record))
            elif editor_record.name == "Splines":
                self.append(SplineEditor.from_record(editor_record))
            else:
                print(f"Unhandled Editor({editor_record.name!r})")
        assert record.buffer.is_empty()
        return self


@dataclass
class Job:
    stream_info: StreamInfo
    file_info: Optional[FileInfo]
    settings: Optional[Settings]
    editors: Optional[Editors]

    @classmethod
    def from_buffer(cls, buffer: Buffer):
        stream_info = StreamInfo.from_buffer(buffer)
        file_info: Optional[FileInfo] = None
        settings: Optional[Settings] = None
        editors: Optional[Editors] = None
        for _ in range(stream_info.record_count):
            record = Record.from_buffer(buffer)
            if record.name == "FileInfo":
                file_info = FileInfo.from_record(record)
            elif record.name == "Settings":
                settings = Settings.from_record(record)
            elif record.name == "Editors":
                editors = Editors.from_record(record)
            else:
                print(f"Unhandled record({record.name!r})!")
            assert record.buffer.is_empty()
        return cls(stream_info, file_info, settings, editors)
