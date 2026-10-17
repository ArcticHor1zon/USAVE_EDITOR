"""Binary writer for the NRBF format.

Inverse of `reader.py`. Writes little-endian primitives, 7-bit-encoded
length-prefixed UTF-8 strings, single UTF-8 characters, .NET TimeSpan
(ticks since midnight), and .NET DateTime (ticks since 0001-01-01 with
kind bits).

Ports `unparse.rs` from the Rust `ms-nrbf` crate.
"""

from __future__ import annotations

import struct
from datetime import datetime, time, timezone
from typing import BinaryIO

from .primitives import Primitive, PrimitiveType

_TICKS_PER_SECOND = 10_000_000
_DOTNET_UNIX_DIFF_TICKS = 621_355_968_000_000_000


class NrbfWriter:
    """Writes NRBF primitive values to a binary stream.

    All multi-byte integers are written little-endian.
    """

    def __init__(self, stream: BinaryIO):
        self._s = stream

    # --- raw bytes ------------------------------------------------------

    def write_bytes(self, data: bytes) -> None:
        self._s.write(data)

    def write_u8(self, v: int) -> None:
        self._s.write(bytes([v & 0xFF]))

    def write_u16(self, v: int) -> None:
        self._s.write(struct.pack("<H", v & 0xFFFF))

    def write_u32(self, v: int) -> None:
        self._s.write(struct.pack("<I", v & 0xFFFFFFFF))

    def write_u64(self, v: int) -> None:
        self._s.write(struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF))

    def write_i8(self, v: int) -> None:
        self.write_u8(v & 0xFF)

    def write_i16(self, v: int) -> None:
        self.write_u16(v & 0xFFFF)

    def write_i32(self, v: int) -> None:
        self.write_u32(v & 0xFFFFFFFF)

    def write_i64(self, v: int) -> None:
        self.write_u64(v & 0xFFFFFFFFFFFFFFFF)

    def write_f32(self, v: float) -> None:
        self._s.write(struct.pack("<f", v))

    def write_f64(self, v: float) -> None:
        self._s.write(struct.pack("<d", v))

    # --- text -----------------------------------------------------------

    def write_char(self, v: str) -> None:
        self._s.write(v.encode("utf-8"))

    def write_string(self, v: str) -> None:
        """7-bit-encoded length prefix + UTF-8 bytes.

        Matches `System.IO.BinaryWriter.Write(string)`.
        """
        data = v.encode("utf-8")
        length = len(data)
        while True:
            byte = length & 0x7F
            length >>= 7
            if length == 0:
                self.write_u8(byte)
                break
            self.write_u8(byte | 0x80)
        self._s.write(data)

    # --- typed primitive dispatch --------------------------------------

    def write_primitive(self, p: Primitive) -> None:
        if p.type == PrimitiveType.Boolean:
            self.write_u8(1 if p.value else 0)
        elif p.type == PrimitiveType.Byte:
            self.write_u8(p.value)
        elif p.type == PrimitiveType.Char:
            self.write_char(p.value)
        elif p.type == PrimitiveType.Decimal:
            self.write_string(p.value)
        elif p.type == PrimitiveType.Double:
            self.write_f64(p.value)
        elif p.type == PrimitiveType.Int16:
            self.write_i16(p.value)
        elif p.type == PrimitiveType.Int32:
            self.write_i32(p.value)
        elif p.type == PrimitiveType.Int64:
            self.write_i64(p.value)
        elif p.type == PrimitiveType.SByte:
            self.write_i8(p.value)
        elif p.type == PrimitiveType.Single:
            self.write_f32(p.value)
        elif p.type == PrimitiveType.TimeSpan:
            self.write_timespan(p.value)
        elif p.type == PrimitiveType.DateTime:
            self.write_datetime(p.value)
        elif p.type == PrimitiveType.UInt16:
            self.write_u16(p.value)
        elif p.type == PrimitiveType.UInt32:
            self.write_u32(p.value)
        elif p.type == PrimitiveType.UInt64:
            self.write_u64(p.value)
        elif p.type == PrimitiveType.Null:
            pass
        elif p.type == PrimitiveType.String:
            self.write_string(p.value)
        else:
            raise ValueError(f"unknown primitive type: {p.type!r}")

    def write_timespan(self, v: time) -> None:
        """Write a `datetime.time` as a .NET TimeSpan tick count."""
        secs = v.hour * 3600 + v.minute * 60 + v.second
        ticks = secs * _TICKS_PER_SECOND + (v.microsecond * 1000) // 100
        self.write_i64(ticks)

    def write_datetime(self, v: datetime) -> None:
        """Write a `datetime` as a .NET DateTime tick count.

        Naive datetimes are assumed UTC. The DateTimeKind bits are set to
        0 (Unspecified) for byte-compatibility with the original Rust
        implementation, which ignored them.
        """
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        unix_seconds = int(v.timestamp())
        unix_nanos = v.microsecond * 1000
        unix_ticks = unix_seconds * _TICKS_PER_SECOND + (unix_nanos // 100)
        ticks = unix_ticks + _DOTNET_UNIX_DIFF_TICKS
        self.write_i64(ticks)
