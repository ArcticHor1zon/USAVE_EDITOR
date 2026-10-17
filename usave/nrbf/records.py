"""NRBF record types.

Each NRBF record is a typed structure preceded by a single-byte
RecordType discriminator. This module defines the dataclasses for
every record type the ULTRAKILL save format uses, plus their
parse/serialize methods.

Ports `records.rs` and `common.rs` from the Rust `ms-nrbf` crate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .primitives import (
    AdditionalInfo,
    BinaryArrayType,
    BinaryType,
    Primitive,
    PrimitiveArray,
    PrimitiveType,
    RecordType,
)
from .reader import NrbfReader
from .writer import NrbfWriter


# ---------------------------------------------------------------------------
# Common sub-structures (ports of `common.rs`)
# ---------------------------------------------------------------------------


@dataclass
class ClassInfo:
    object_id: int
    name: str
    member_count: int
    member_names: list[str] = field(default_factory=list)

    @classmethod
    def read(cls, r: NrbfReader) -> "ClassInfo":
        object_id = r.read_i32()
        name = r.read_string()
        member_count = r.read_i32()
        names = [r.read_string() for _ in range(member_count)]
        return cls(object_id, name, member_count, names)

    def write(self, w: NrbfWriter) -> None:
        w.write_i32(self.object_id)
        w.write_string(self.name)
        w.write_i32(self.member_count)
        for n in self.member_names:
            w.write_string(n)


@dataclass
class ClassTypeInfo:
    type_name: str
    library_id: int

    @classmethod
    def read(cls, r: NrbfReader) -> "ClassTypeInfo":
        return cls(r.read_string(), r.read_i32())

    def write(self, w: NrbfWriter) -> None:
        w.write_string(self.type_name)
        w.write_i32(self.library_id)


@dataclass
class ArrayInfo:
    object_id: int
    length: int

    @classmethod
    def read(cls, r: NrbfReader) -> "ArrayInfo":
        return cls(r.read_i32(), r.read_i32())

    def write(self, w: NrbfWriter) -> None:
        w.write_i32(self.object_id)
        w.write_i32(self.length)


@dataclass
class MemberTypeInfo:
    member_types: list[BinaryType] = field(default_factory=list)
    additional_info: list[AdditionalInfo] = field(default_factory=list)

    @classmethod
    def read(cls, r: NrbfReader, member_count: int) -> "MemberTypeInfo":
        member_types = [BinaryType(r.read_u8()) for _ in range(member_count)]
        additional_info: list[AdditionalInfo] = []
        for mt in member_types:
            info = _read_additional_info(r, mt)
            if info is not None:
                additional_info.append(info)
        return cls(member_types, additional_info)

    def write(self, w: NrbfWriter) -> None:
        for mt in self.member_types:
            w.write_u8(int(mt))
        for info in self.additional_info:
            _write_additional_info(w, info)


def _read_additional_info(r: NrbfReader, bt: BinaryType) -> Optional[AdditionalInfo]:
    if bt == BinaryType.Primitive:
        return AdditionalInfo.Primitive(value=PrimitiveType(r.read_u8()))
    if bt == BinaryType.PrimitiveArray:
        return AdditionalInfo.PrimitiveArray(value=PrimitiveType(r.read_u8()))
    if bt == BinaryType.SystemClass:
        return AdditionalInfo.SystemClass(value=r.read_string())
    if bt == BinaryType.Class:
        return AdditionalInfo.Class(value=ClassTypeInfo.read(r))
    return None


def _write_additional_info(w: NrbfWriter, info: AdditionalInfo) -> None:
    if info.kind == "Primitive":
        w.write_u8(int(info.value))
    elif info.kind == "PrimitiveArray":
        w.write_u8(int(info.value))
    elif info.kind == "SystemClass":
        w.write_string(info.value)
    elif info.kind == "Class":
        info.value.write(w)
    else:
        raise ValueError(f"unknown additional info: {info!r}")


# ---------------------------------------------------------------------------
# Records (ports of `records.rs`)
# ---------------------------------------------------------------------------


@dataclass
class SerializationHeaderRecord:
    root_id: int
    header_id: int
    major_version: int
    minor_version: int

    @classmethod
    def read(cls, r: NrbfReader) -> "SerializationHeaderRecord":
        return cls(r.read_i32(), r.read_i32(), r.read_i32(), r.read_i32())

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.SerializedStreamHeader))
        w.write_i32(self.root_id)
        w.write_i32(self.header_id)
        w.write_i32(self.major_version)
        w.write_i32(self.minor_version)


@dataclass
class BinaryLibraryRecord:
    library_id: int
    library_name: str

    @classmethod
    def read(cls, r: NrbfReader) -> "BinaryLibraryRecord":
        return cls(r.read_i32(), r.read_string())

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.BinaryLibrary))
        w.write_i32(self.library_id)
        w.write_string(self.library_name)


@dataclass
class BinaryObjectStringRecord:
    object_id: int
    value: str

    @classmethod
    def read(cls, r: NrbfReader) -> "BinaryObjectStringRecord":
        return cls(r.read_i32(), r.read_string())

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.BinaryObjectString))
        w.write_i32(self.object_id)
        w.write_string(self.value)


@dataclass
class ArraySinglePrimitiveRecord:
    array_info: ArrayInfo
    primitive_type: PrimitiveType
    members: list[Primitive]

    @classmethod
    def read(cls, r: NrbfReader) -> "ArraySinglePrimitiveRecord":
        array_info = ArrayInfo.read(r)
        ptype = PrimitiveType(r.read_u8())
        members = [Primitive(ptype, r.read_primitive(ptype)) for _ in range(array_info.length)]
        return cls(array_info, ptype, members)

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.ArraySinglePrimitive))
        self.array_info.write(w)
        w.write_u8(int(self.primitive_type))
        for m in self.members:
            w.write_primitive(m)


@dataclass
class ClassWithMembersAndTypesRecord:
    class_info: ClassInfo
    member_type_info: MemberTypeInfo
    library_id: int
    member_references: list = field(default_factory=list)

    @classmethod
    def read(cls, r: NrbfReader) -> "ClassWithMembersAndTypesRecord":
        class_info = ClassInfo.read(r)
        member_type_info = MemberTypeInfo.read(r, class_info.member_count)
        library_id = r.read_i32()
        refs = _read_references(r, member_type_info.additional_info)
        return cls(class_info, member_type_info, library_id, refs)

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.ClassWithMembersAndTypes))
        self.class_info.write(w)
        self.member_type_info.write(w)
        w.write_i32(self.library_id)
        for ref in self.member_references:
            _write_member_reference(w, ref)


@dataclass
class SystemClassWithMembersAndTypesRecord:
    class_info: ClassInfo
    member_type_info: MemberTypeInfo
    member_references: list = field(default_factory=list)

    @classmethod
    def read(cls, r: NrbfReader) -> "SystemClassWithMembersAndTypesRecord":
        class_info = ClassInfo.read(r)
        member_type_info = MemberTypeInfo.read(r, class_info.member_count)
        refs = _read_references(r, member_type_info.additional_info)
        return cls(class_info, member_type_info, refs)

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.SystemClassWithMembersAndTypes))
        self.class_info.write(w)
        self.member_type_info.write(w)
        for ref in self.member_references:
            _write_member_reference(w, ref)


@dataclass
class ClassWithIdRecord:
    object_id: int
    metadata_id: int

    @classmethod
    def read(cls, r: NrbfReader) -> "ClassWithIdRecord":
        return cls(r.read_i32(), r.read_i32())

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.ClassWithId))
        w.write_i32(self.object_id)
        w.write_i32(self.metadata_id)


@dataclass
class MemberReferenceRecord:
    id: int

    @classmethod
    def read(cls, r: NrbfReader) -> "MemberReferenceRecord":
        return cls(r.read_i32())

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.MemberReference))
        w.write_i32(self.id)


@dataclass
class ObjectNullRecord:
    @classmethod
    def read(cls, r: NrbfReader) -> "ObjectNullRecord":
        return cls()

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.ObjectNull))


@dataclass
class ObjectNullMultiple256Record:
    null_count: int

    @classmethod
    def read(cls, r: NrbfReader) -> "ObjectNullMultiple256Record":
        return cls(r.read_u8())

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.ObjectNullMultiple256))
        w.write_u8(self.null_count)


@dataclass
class ObjectNullMultipleRecord:
    null_count: int

    @classmethod
    def read(cls, r: NrbfReader) -> "ObjectNullMultipleRecord":
        return cls(r.read_i32())

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.ObjectNullMultiple))
        w.write_i32(self.null_count)


@dataclass
class MessageEndRecord:
    @classmethod
    def read(cls, r: NrbfReader) -> "MessageEndRecord":
        return cls()

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.MessageEnd))


@dataclass
class ArraySingleObjectRecord:
    array_info: ArrayInfo
    members: list  # list of Record (member references / nulls)

    @classmethod
    def read(cls, r: NrbfReader) -> "ArraySingleObjectRecord":
        array_info = ArrayInfo.read(r)
        members = [read_record(r) for _ in range(array_info.length)]
        return cls(array_info, members)

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.ArraySingleObject))
        self.array_info.write(w)
        for m in self.members:
            m.write(w)


@dataclass
class ArraySingleStringRecord:
    array_info: ArrayInfo
    members: list  # list of Record (BinaryObjectString / nulls)

    @classmethod
    def read(cls, r: NrbfReader) -> "ArraySingleStringRecord":
        array_info = ArrayInfo.read(r)
        members = [read_record(r) for _ in range(array_info.length)]
        return cls(array_info, members)

    def write(self, w: NrbfWriter) -> None:
        w.write_u8(int(RecordType.ArraySingleString))
        self.array_info.write(w)
        for m in self.members:
            m.write(w)


# ---------------------------------------------------------------------------
# Member reference handling
# ---------------------------------------------------------------------------

# Inline primitive values in member_references are stored as bare `Primitive`
# objects (no record wrapper). When writing, we emit them WITHOUT a record-type
# byte and WITHOUT a leading PrimitiveType byte (the type is in AdditionalInfo).
# When a record-typed value (MemberReference, ObjectNull, ArraySingle*,
# BinaryObjectString, etc.) is in member_references, we emit it WITH its
# record-type byte.


def _write_member_reference(w: NrbfWriter, ref) -> None:
    if isinstance(ref, Primitive):
        # inline primitive value (no prefix bytes — type is in AdditionalInfo)
        w.write_primitive(ref)
    else:
        # full record (writes its own record-type byte)
        ref.write(w)


def _read_references(r: NrbfReader, additional_info: list[AdditionalInfo]) -> list:
    """Read the member reference list that follows a ClassWithMembers* record."""
    refs: list = []
    for info in additional_info:
        if info.kind == "Primitive":
            # inline primitive value (no record-type prefix, no type byte —
            # type comes from AdditionalInfo)
            refs.append(Primitive(info.value, r.read_primitive(info.value)))
        else:
            refs.append(read_record(r))
    return refs


# ---------------------------------------------------------------------------
# Record dispatch (ports the `Record` enum + parse logic from `enums.rs`)
# ---------------------------------------------------------------------------

Record = object  # any of the *Record dataclasses above, or Primitive


def read_record(r: NrbfReader) -> Record:
    """Read one record, dispatching on its leading RecordType byte."""
    rt = RecordType(r.read_u8())
    if rt == RecordType.SerializedStreamHeader:
        return SerializationHeaderRecord.read(r)
    if rt == RecordType.ClassWithId:
        return ClassWithIdRecord.read(r)
    if rt == RecordType.SystemClassWithMembersAndTypes:
        return SystemClassWithMembersAndTypesRecord.read(r)
    if rt == RecordType.ClassWithMembersAndTypes:
        return ClassWithMembersAndTypesRecord.read(r)
    if rt == RecordType.BinaryObjectString:
        return BinaryObjectStringRecord.read(r)
    if rt == RecordType.MemberPrimitiveUnTyped:
        # Standalone MemberPrimitiveUnTyped record (record type 8).
        # The Rust code calls this "MemberTypedPrimitive" and reads a
        # PrimitiveType byte then the value.
        ptype = PrimitiveType(r.read_u8())
        return Primitive(ptype, r.read_primitive(ptype))
    if rt == RecordType.MemberReference:
        return MemberReferenceRecord.read(r)
    if rt == RecordType.ObjectNull:
        return ObjectNullRecord.read(r)
    if rt == RecordType.MessageEnd:
        return MessageEndRecord.read(r)
    if rt == RecordType.BinaryLibrary:
        return BinaryLibraryRecord.read(r)
    if rt == RecordType.ObjectNullMultiple256:
        return ObjectNullMultiple256Record.read(r)
    if rt == RecordType.ObjectNullMultiple:
        return ObjectNullMultipleRecord.read(r)
    if rt == RecordType.ArraySinglePrimitive:
        return ArraySinglePrimitiveRecord.read(r)
    if rt == RecordType.ArraySingleObject:
        return ArraySingleObjectRecord.read(r)
    if rt == RecordType.ArraySingleString:
        return ArraySingleStringRecord.read(r)
    raise NotImplementedError(f"record type {rt!r} ({int(rt)}) not implemented")


def read_all_records(r: NrbfReader) -> list[Record]:
    """Read records until MessageEnd is encountered."""
    records: list[Record] = []
    while True:
        rec = read_record(r)
        records.append(rec)
        if isinstance(rec, MessageEndRecord):
            break
    return records
