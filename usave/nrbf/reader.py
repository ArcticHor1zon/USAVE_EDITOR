"""Binary reader for the NRBF format.

Reads little-endian primitives, 7-bit-encoded length-prefixed UTF-8 strings,
single UTF-8 characters, .NET TimeSpan (ticks since midnight), and
.NET DateTime (ticks since 0001-01-01 with kind bits).

Ports `parse.rs` from the Rust `ms-nrbf` crate.
"""

from __future__ import annotations

import struct
from datetime import datetime, time, timezone
from typing import BinaryIO

from .primitives import PrimitiveType

# .NET DateTime: ticks (100ns) since 0001-01-01.
# Unix epoch 1970-01-01 is 621,355,968,000,000,000 ticks after 0001-01-01.
_TICKS_PER_SECOND = 10_000_000
_DOTNET_UNIX_DIFF_TICKS = 621_355_968_000_000_000


class NrbfReader:
    """Reads NRBF primitive values from a binary stream.

    All multi-byte integers are little-endian, matching the NRBF spec.
    """

    def __init__(self, stream: BinaryIO):
        self._s = stream

    # --- raw byte reads -------------------------------------------------

    def read_bytes(self, n: int) -> bytes:
        buf = self._s.read(n)
        if len(buf) != n:
            raise EOFError(
                f"expected {n} bytes, got {len(buf)}"
            )
        return buf

    def read_u8(self) -> int:
        return self.read_bytes(1)[0]

    def read_u16(self) -> int:
        return struct.unpack("<H", self.read_bytes(2))[0]

    def read_u32(self) -> int:
        return struct.unpack("<I", self.read_bytes(4))[0]

    def read_u64(self) -> int:
        return struct.unpack("<Q", self.read_bytes(8))[0]

    # --- signed ints (two's complement of the unsigned form) ------------

    def read_i8(self) -> int:
        v = self.read_u8()
        return v - 256 if v >= 128 else v

    def read_i16(self) -> int:
        v = self.read_u16()
        return v - 0x10000 if v >= 0x8000 else v

    def read_i32(self) -> int:
        v = self.read_u32()
        return v - 0x100000000 if v >= 0x80000000 else v

    def read_i64(self) -> int:
        v = self.read_u64()
        return v - 0x10000000000000000 if v >= 0x8000000000000000 else v

    # --- floats ---------------------------------------------------------

    def read_f32(self) -> float:
        return struct.unpack("<f", self.read_bytes(4))[0]

    def read_f64(self) -> float:
        return struct.unpack("<d", self.read_bytes(8))[0]

    # --- text -----------------------------------------------------------

    def read_char(self) -> str:
        """Read a single UTF-8 character (variable-length)."""
        first = self.read_u8()
        if first & 0x80 == 0:
            return chr(first)
        # figure out how many continuation bytes follow
        if first & 0xE0 == 0xC0:
            n = 1
        elif first & 0xF0 == 0xE0:
            n = 2
        else:
            n = 3
        buf = bytearray([first])
        buf.extend(self.read_bytes(n))
        return buf.decode("utf-8")

    def read_string(self) -> str:
        """Read a 7-bit-encoded length-prefixed UTF-8 string.

        Matches `System.IO.BinaryReader.ReadString`:
        length is encoded in 1-5 bytes, 7 bits each, MSB as continuation.
        """
        length = 0
        shift = 0
        for _ in range(5):
            b = self.read_u8()
            length |= (b & 0x7F) << shift
            shift += 7
            if b & 0x80 == 0:
                break
        return self.read_bytes(length).decode("utf-8")

    # --- typed primitive dispatch --------------------------------------

    def read_primitive(self, ptype: PrimitiveType) -> object:
        """Read a primitive value of the given NRBF PrimitiveType."""
        if ptype == PrimitiveType.Boolean:
            return self.read_u8() != 0
        if ptype == PrimitiveType.Byte:
            return self.read_u8()
        if ptype == PrimitiveType.Char:
            return self.read_char()
        if ptype == PrimitiveType.Decimal:
            # .NET Decimal serializes as a string in NRBF
            return self.read_string()
        if ptype == PrimitiveType.Double:
            return self.read_f64()
        if ptype == PrimitiveType.Int16:
            return self.read_i16()
        if ptype == PrimitiveType.Int32:
            return self.read_i32()
        if ptype == PrimitiveType.Int64:
            return self.read_i64()
        if ptype == PrimitiveType.SByte:
            return self.read_i8()
        if ptype == PrimitiveType.Single:
            return self.read_f32()
        if ptype == PrimitiveType.TimeSpan:
            return self.read_timespan()
        if ptype == PrimitiveType.DateTime:
            return self.read_datetime()
        if ptype == PrimitiveType.UInt16:
            return self.read_u16()
        if ptype == PrimitiveType.UInt32:
            return self.read_u32()
        if ptype == PrimitiveType.UInt64:
            return self.read_u64()
        if ptype == PrimitiveType.Null:
            return None
        if ptype == PrimitiveType.String:
            return self.read_string()
        raise ValueError(f"unknown primitive type: {ptype!r}")

    def read_timespan(self) -> time:
        """Read a .NET TimeSpan as a `datetime.time`.

        .NET TimeSpan is a duration; we store it as the time-of-day
        it represents when interpreted as time since midnight, matching
        the original Rust behavior.
        """
        ticks = abs(self.read_i64())
        total_seconds, rem = divmod(ticks, _TICKS_PER_SECOND)
        nano = (rem * 100)
        sec = total_seconds % 60
        minute = (total_seconds // 60) % 60
        hour = (total_seconds // 3600) % 24
        return time(hour=hour, minute=minute, second=sec, microsecond=nano // 1000)

    def read_datetime(self) -> datetime:
        """Read a .NET DateTime as a UTC `datetime.datetime`.

        .NET DateTime is a 64-bit tick count with a 2-bit DateTimeKind
        in the top bits. We strip the kind bits and convert ticks to
        Unix epoch.
        """
        raw = self.read_i64()
        raw_ticks = raw & 0x3FFFFFFFFFFFFFFF  # clear kind bits
        unix_ticks = raw_ticks - _DOTNET_UNIX_DIFF_TICKS
        unix_seconds, rem = divmod(unix_ticks, _TICKS_PER_SECOND)
        unix_nanos = rem * 100
        return datetime.fromtimestamp(
            unix_seconds, tz=timezone.utc
        ).replace(microsecond=unix_nanos // 1000)
