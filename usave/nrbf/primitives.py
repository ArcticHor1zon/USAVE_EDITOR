"""Primitive types and values for the .NET Binary Format (NRBF).

This module ports the `enums.rs` and parts of `common.rs` from the original
Rust `ms-nrbf` crate. The NRBF format is the binary serialization format
used by .NET (`System.Runtime.Serialization.Formatters.Binary.BinaryFormatter`),
which ULTRAKILL uses for its `.bepis` save files.

Reference: [MS-NRBF] . NET Remoting: Binary Format Data Structure
https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-nrbf/
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import IntEnum
from typing import Union


class PrimitiveType(IntEnum):
    """The 17 primitive type codes used in NRBF (MS-NRBF §2.1.2)."""

    Boolean = 1
    Byte = 2
    Char = 3
    # 4 is reserved
    Decimal = 5
    Double = 6
    Int16 = 7
    Int32 = 8
    Int64 = 9
    SByte = 10
    Single = 11
    TimeSpan = 12
    DateTime = 13
    UInt16 = 14
    UInt32 = 15
    UInt64 = 16
    Null = 17
    String = 18


class BinaryType(IntEnum):
    """The BinaryType enum (MS-NRBF §2.1.2) describing member types."""

    Primitive = 0
    String = 1
    Object = 2
    SystemClass = 3
    Class = 4
    ObjectArray = 5
    StringArray = 6
    PrimitiveArray = 7


class BinaryArrayType(IntEnum):
    """BinaryArrayType enum (MS-NRBF §2.1.2.2)."""

    Single = 0
    Jagged = 1
    Rectangular = 2
    SingleOffset = 3
    JaggedOffset = 4
    RectangularOffset = 5


class RecordType(IntEnum):
    """Record type codes (MS-NRBF §2.3)."""

    SerializedStreamHeader = 0
    ClassWithId = 1
    SystemClassWithMembers = 2
    ClassWithMembers = 3
    SystemClassWithMembersAndTypes = 4
    ClassWithMembersAndTypes = 5
    BinaryObjectString = 6
    BinaryArray = 7
    MemberPrimitiveUnTyped = 8  # NOTE: not in the Rust impl; we treat 8 as MemberTypedPrimitive per spec
    MemberReference = 9
    ObjectNull = 10
    MessageEnd = 11
    BinaryLibrary = 12
    ObjectNullMultiple256 = 13
    ObjectNullMultiple = 14
    ArraySinglePrimitive = 15
    ArraySingleObject = 16
    ArraySingleString = 17
    MethodCall = 21
    MethodReturn = 22


# The Rust impl renames the byte 8 record "MemberTypedPrimitive" and parses
# it as (PrimitiveType, Primitive). The MS-NRBF spec actually calls byte 8
# "MemberPrimitiveUnTyped" but the Rust code uses "MemberTypedPrimitive"
# semantics. We follow the Rust behavior for byte compatibility.


@dataclass(frozen=True)
class Primitive:
    """A single primitive value.

    The `type` field discriminates which `value` payload is active.
    Stored as a frozen dataclass so it can be hashed and compared, which
    makes round-trip testing trivial.
    """

    type: PrimitiveType
    value: object  # bool | int | float | str | datetime | time | None

    @classmethod
    def Boolean(cls, v: bool) -> "Primitive":
        return cls(PrimitiveType.Boolean, bool(v))

    @classmethod
    def Byte(cls, v: int) -> "Primitive":
        return cls(PrimitiveType.Byte, int(v))

    @classmethod
    def Char(cls, v: str) -> "Primitive":
        return cls(PrimitiveType.Char, str(v))

    @classmethod
    def Decimal(cls, v: str) -> "Primitive":
        return cls(PrimitiveType.Decimal, str(v))

    @classmethod
    def Double(cls, v: float) -> "Primitive":
        return cls(PrimitiveType.Double, float(v))

    @classmethod
    def Int16(cls, v: int) -> "Primitive":
        return cls(PrimitiveType.Int16, int(v))

    @classmethod
    def Int32(cls, v: int) -> "Primitive":
        return cls(PrimitiveType.Int32, int(v))

    @classmethod
    def Int64(cls, v: int) -> "Primitive":
        return cls(PrimitiveType.Int64, int(v))

    @classmethod
    def SByte(cls, v: int) -> "Primitive":
        return cls(PrimitiveType.SByte, int(v))

    @classmethod
    def Single(cls, v: float) -> "Primitive":
        return cls(PrimitiveType.Single, float(v))

    @classmethod
    def TimeSpan(cls, v: time) -> "Primitive":
        return cls(PrimitiveType.TimeSpan, v)

    @classmethod
    def DateTime(cls, v: datetime) -> "Primitive":
        return cls(PrimitiveType.DateTime, v)

    @classmethod
    def UInt16(cls, v: int) -> "Primitive":
        return cls(PrimitiveType.UInt16, int(v))

    @classmethod
    def UInt32(cls, v: int) -> "Primitive":
        return cls(PrimitiveType.UInt32, int(v))

    @classmethod
    def UInt64(cls, v: int) -> "Primitive":
        return cls(PrimitiveType.UInt64, int(v))

    @classmethod
    def Null(cls) -> "Primitive":
        return cls(PrimitiveType.Null, None)

    @classmethod
    def String(cls, v: str) -> "Primitive":
        return cls(PrimitiveType.String, str(v))


@dataclass(frozen=True)
class PrimitiveArray:
    """A typed array of primitives.

    The `type` field discriminates which list type `values` holds.
    All entries in `values` must match the declared primitive type.
    """

    type: PrimitiveType
    values: tuple  # tuple of the underlying Python values

    @classmethod
    def of(cls, ptype: PrimitiveType, values) -> "PrimitiveArray":
        return cls(ptype, tuple(values))


# ---------------------------------------------------------------------------
# AdditionalInfo (ports the `AdditionalInfo` enum from `enums.rs`)
# ---------------------------------------------------------------------------


class AdditionalInfo:
    """Tagged union for the per-member AdditionalInfo field in MemberTypeInfo.

    The MS-NRBF spec calls this "AdditionalInfo" and its shape depends on
    the BinaryType of the member:

    * Primitive       -> PrimitiveType enum value
    * PrimitiveArray  -> PrimitiveType enum value
    * SystemClass     -> type name string
    * Class           -> ClassTypeInfo (type_name + library_id)
    * others          -> None

    We use a small frozen dataclass per variant for clarity. The `kind`
    attribute lets callers pattern-match without isinstance chains.
    """

    kind: str
    value: object

    @dataclass(frozen=True)
    class _Primitive:
        kind: str = "Primitive"
        value: PrimitiveType = PrimitiveType.Null

    @dataclass(frozen=True)
    class _PrimitiveArray:
        kind: str = "PrimitiveArray"
        value: PrimitiveType = PrimitiveType.Null

    @dataclass(frozen=True)
    class _SystemClass:
        kind: str = "SystemClass"
        value: str = ""

    @dataclass(frozen=True)
    class _Class:
        kind: str = "Class"
        value: object = None  # ClassTypeInfo, defined in records.py

    Primitive = _Primitive
    PrimitiveArray = _PrimitiveArray
    SystemClass = _SystemClass
    Class = _Class
