"""High-level NRBF Stream API.

`Stream` is the top-level container: it wraps a single root `Class`.
Each `Class` has a `library_name`, a `name`, and an ordered `fields`
mapping (string -> `Field`).

A `Field` is one of:
  - `Primitive`       (a single primitive value)
  - `PrimitiveArray`  (a typed array of primitives)
  - `Class`           (a nested class instance)

`Stream.decode(reader)` parses a binary NRBF stream into a `Stream`.
`Stream.encode(writer)` serializes a `Stream` back to binary.

Ports `stream.rs` from the Rust `ms-nrbf` crate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import BinaryIO, Union

from .primitives import (
    AdditionalInfo,
    BinaryType,
    Primitive,
    PrimitiveArray,
    PrimitiveType,
    RecordType,
)
from .reader import NrbfReader
from .records import (
    ArrayInfo,
    ArraySinglePrimitiveRecord,
    BinaryLibraryRecord,
    ClassInfo,
    ClassTypeInfo,
    ClassWithIdRecord,
    ClassWithMembersAndTypesRecord,
    MemberTypeInfo,
    MemberReferenceRecord,
    MessageEndRecord,
    Record,
    SerializationHeaderRecord,
    read_all_records,
)
from .writer import NrbfWriter


@dataclass
class Class:
    """A decoded .NET class instance.

    `library_name` is the assembly-qualified name from the BinaryLibrary
    record that introduced this class's library. `name` is the
    unqualified class name (e.g. "RankData", "EndlessProgress").
    `fields` is an ordered mapping from field name to `Field` value.
    """

    library_name: str
    name: str
    fields: dict[str, "Field"] = field(default_factory=dict)


# A Field is one of: Primitive | PrimitiveArray | Class
Field = Union[Primitive, PrimitiveArray, Class]


@dataclass
class Stream:
    """Top-level NRBF container wrapping a single root Class."""

    root: Class

    @classmethod
    def decode(cls, stream: BinaryIO) -> "Stream":
        """Decode a binary NRBF stream into a `Stream`."""
        r = NrbfReader(stream)
        records = read_all_records(r)

        objects: dict[int, Record] = {}
        libraries: dict[int, str] = {}
        root_id: int | None = None
        root_record: ClassWithMembersAndTypesRecord | None = None

        for rec in records:
            if isinstance(rec, SerializationHeaderRecord):
                root_id = rec.root_id
            elif isinstance(rec, ClassWithIdRecord):
                objects[rec.object_id] = rec
            elif isinstance(rec, BinaryLibraryRecord):
                libraries[rec.library_id] = rec.library_name
            elif isinstance(rec, ClassWithMembersAndTypesRecord):
                if root_id is not None and rec.class_info.object_id == root_id:
                    root_record = rec
                objects[rec.class_info.object_id] = rec
            elif isinstance(rec, ArraySinglePrimitiveRecord):
                objects[rec.array_info.object_id] = rec
            elif isinstance(rec, MessageEndRecord):
                pass
            # other record types are collected by read_all_records but
            # not indexed here (matching the original Rust behavior).

        if root_record is None:
            raise ValueError("NRBF stream has no root class")

        state = _DecoderState(objects, libraries)
        return cls(state.decode_class(root_record))

    def encode(self, stream: BinaryIO) -> None:
        """Serialize this `Stream` to a binary NRBF stream."""
        w = NrbfWriter(stream)

        # 1. Serialization header
        SerializationHeaderRecord(
            root_id=1, header_id=-1, major_version=1, minor_version=0
        ).write(w)

        # 2. Encode the class tree, collecting library registrations
        state = _EncoderState()
        body_records = state.encode_class(self.root)

        # 3. Emit BinaryLibrary records (one per unique library name)
        for library_name, library_id in state.libraries.items():
            BinaryLibraryRecord(
                library_id=library_id, library_name=library_name
            ).write(w)

        # 4. Emit the body records (class + arrays + nested classes)
        for rec in body_records:
            rec.write(w)

        # 5. MessageEnd
        MessageEndRecord().write(w)


# ---------------------------------------------------------------------------
# Decoder (ports `StreamDecoderState` from `stream.rs`)
# ---------------------------------------------------------------------------


class _DecoderState:
    def __init__(self, objects: dict[int, Record], libraries: dict[int, str]):
        self.objects = objects
        self.libraries = libraries

    def decode_class(self, rec: ClassWithMembersAndTypesRecord) -> Class:
        field_count = rec.class_info.member_count
        fields: dict[str, Field] = {}

        # `ai` indexes into member_references and only advances for
        # Primitive / PrimitiveArray / Class members (matching the original).
        ai = 0
        for i in range(field_count):
            name = rec.class_info.member_names[i]
            bt = rec.member_type_info.member_types[i]
            value: Field | None = None

            if bt == BinaryType.Primitive:
                ref = rec.member_references[ai]
                if isinstance(ref, Primitive):
                    value = ref
                ai += 1
            elif bt == BinaryType.PrimitiveArray:
                ref = rec.member_references[ai]
                if isinstance(ref, MemberReferenceRecord):
                    target = self.objects.get(ref.id)
                    if isinstance(target, ArraySinglePrimitiveRecord):
                        value = PrimitiveArray.of(
                            target.primitive_type,
                            [m.value for m in target.members],
                        )
                ai += 1
            elif bt == BinaryType.Class:
                ref = rec.member_references[ai] if ai < len(rec.member_references) else None
                if isinstance(ref, MemberReferenceRecord):
                    target = self.objects.get(ref.id)
                    if isinstance(target, ClassWithMembersAndTypesRecord):
                        value = self.decode_class(target)
                ai += 1
            elif bt == BinaryType.String:
                ref = rec.member_references[ai] if ai < len(rec.member_references) else None
                if isinstance(ref, MemberReferenceRecord):
                    target = self.objects.get(ref.id)
                    from .records import BinaryObjectStringRecord
                    if isinstance(target, BinaryObjectStringRecord):
                        value = Primitive.String(target.value)
                ai += 1
            # other BinaryTypes (Object, SystemClass, ObjectArray, StringArray)
            # are not produced by ULTRAKILL saves — skip silently.

            if value is not None:
                fields[name] = value

        return Class(
            library_name=self.libraries.get(rec.library_id, ""),
            name=rec.class_info.name,
            fields=fields,
        )


# ---------------------------------------------------------------------------
# Encoder (ports `StreamEncoderState` from `stream.rs`)
# ---------------------------------------------------------------------------

# We must import this here (not at top) to avoid a circular import with
# records.py — actually `MemberReferenceRecord` is in records.py which is
# already imported above. The import below is a no-op but kept for clarity
# so readers of the encoder section know where MemberReferenceRecord lives.


class _EncoderState:
    def __init__(self):
        self.libraries: dict[str, int] = {}
        self.counter: int = 1

    def _register_library(self, library_name: str) -> int:
        """Register a library if not seen before; return its library_id."""
        if library_name not in self.libraries:
            self.counter += 1  # library_id is the next available counter value
            self.libraries[library_name] = self.counter
        return self.libraries[library_name]

    def encode_class(self, klass: Class) -> list[Record]:
        """Encode a Class into a list of records.

        Returns [ClassWithMembersAndTypes, ...array/nested class records...].
        The class record is always first so the decoder can find it before
        its referenced arrays/nested classes.
        """
        object_id = self.counter
        self.counter += 1
        library_id = self._register_library(klass.library_name)

        member_names: list[str] = []
        member_types: list[BinaryType] = []
        additional_info: list[AdditionalInfo] = []
        member_references: list = []
        body: list[Record] = []

        for field_name, field_value in klass.fields.items():
            member_names.append(field_name)
            if isinstance(field_value, Primitive):
                member_types.append(BinaryType.Primitive)
                additional_info.append(AdditionalInfo.Primitive(value=field_value.type))
                # inline primitive value (no record wrapper)
                member_references.append(field_value)
            elif isinstance(field_value, PrimitiveArray):
                ptype = field_value.type
                member_types.append(BinaryType.PrimitiveArray)
                additional_info.append(AdditionalInfo.PrimitiveArray(value=ptype))
                # the array lives in the body as its own record
                array_id = self.counter
                self.counter += 1
                member_references.append(MemberReferenceRecord(id=array_id))
                members = [Primitive(ptype, v) for v in field_value.values]
                body.append(
                    ArraySinglePrimitiveRecord(
                        array_info=ArrayInfo(
                            object_id=array_id, length=len(members)
                        ),
                        primitive_type=ptype,
                        members=members,
                    )
                )
            elif isinstance(field_value, Class):
                # capture the nested class's object_id BEFORE recursing
                nested_id = self.counter
                nested_body = self.encode_class(field_value)
                body.extend(nested_body)
                member_types.append(BinaryType.Class)
                additional_info.append(
                    AdditionalInfo.Class(
                        value=ClassTypeInfo(
                            type_name=field_value.name,
                            library_id=self.libraries[field_value.library_name],
                        )
                    )
                )
                member_references.append(MemberReferenceRecord(id=nested_id))
            else:
                raise TypeError(
                    f"unsupported field value type for {field_name!r}: {type(field_value).__name__}"
                )

        class_record = ClassWithMembersAndTypesRecord(
            class_info=ClassInfo(
                object_id=object_id,
                name=klass.name,
                member_count=len(member_names),
                member_names=member_names,
            ),
            member_type_info=MemberTypeInfo(
                member_types=member_types,
                additional_info=additional_info,
            ),
            library_id=library_id,
            member_references=member_references,
        )
        return [class_record, *body]
