"""Smoke tests for the NRBF library.

Verifies that:
  - Each PrimitiveType round-trips through encode -> decode.
  - A Class with mixed Primitive and PrimitiveArray fields round-trips.
  - A Class with a nested Class field round-trips.
  - Encode -> decode -> encode is byte-stable.
"""

from __future__ import annotations

import io
from datetime import datetime, time, timezone

import pytest

from usave.nrbf import (
    Class,
    Primitive,
    PrimitiveArray,
    PrimitiveType,
    Stream,
)


def _roundtrip_stream(stream: Stream) -> Stream:
    buf = io.BytesIO()
    stream.encode(buf)
    buf.seek(0)
    return Stream.decode(buf)


def _byte_stable(stream: Stream) -> bool:
    buf1 = io.BytesIO()
    stream.encode(buf1)
    data1 = buf1.getvalue()

    s2 = Stream.decode(io.BytesIO(data1))
    buf2 = io.BytesIO()
    s2.encode(buf2)
    data2 = buf2.getvalue()

    return data1 == data2


# ---------------------------------------------------------------------------
# Single primitive round-trips
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "primitive",
    [
        Primitive.Boolean(True),
        Primitive.Boolean(False),
        Primitive.Byte(0),
        Primitive.Byte(255),
        Primitive.Char("A"),
        Primitive.Char("\u00e9"),  # é
        Primitive.Char("\u4e2d"),  # 中
        Primitive.Decimal("3.14"),
        Primitive.Double(3.141592653589793),
        Primitive.Int16(-32768),
        Primitive.Int16(32767),
        Primitive.Int32(-2147483648),
        Primitive.Int32(2147483647),
        Primitive.Int64(-(2**63)),
        Primitive.Int64(2**63 - 1),
        Primitive.SByte(-128),
        Primitive.SByte(127),
        Primitive.Single(3.14),
        Primitive.Single(-0.5),
        Primitive.UInt16(0),
        Primitive.UInt16(65535),
        Primitive.UInt32(0),
        Primitive.UInt32(4294967295),
        Primitive.UInt64(0),
        Primitive.UInt64(2**64 - 1),
        Primitive.String(""),
        Primitive.String("Hello, ULTRAKILL!"),
        Primitive.String("Unicode: \u4e2d\u6587"),
        Primitive.Null(),
    ],
)
def test_primitive_roundtrip(primitive: Primitive) -> None:
    """Each primitive value should survive a single-field class round-trip."""
    klass = Class(
        library_name="TestLib",
        name="TestClass",
        fields={"value": primitive},
    )
    decoded = _roundtrip_stream(Stream(root=klass)).root
    assert "value" in decoded.fields
    field = decoded.fields["value"]
    assert isinstance(field, Primitive)
    assert field.type == primitive.type
    if primitive.type != PrimitiveType.Single and primitive.type != PrimitiveType.Double:
        assert field.value == primitive.value
    else:
        # floats: compare with tolerance
        assert field.value == pytest.approx(primitive.value)


def test_timespan_roundtrip() -> None:
    klass = Class(
        library_name="TestLib",
        name="TestClass",
        fields={"value": Primitive.TimeSpan(time(14, 30, 45, 123000))},
    )
    decoded = _roundtrip_stream(Stream(root=klass)).root
    field = decoded.fields["value"]
    assert isinstance(field, Primitive)
    assert field.type == PrimitiveType.TimeSpan
    assert field.value.hour == 14
    assert field.value.minute == 30
    assert field.value.second == 45


def test_datetime_roundtrip() -> None:
    dt = datetime(2024, 1, 15, 12, 30, 45, 123000, tzinfo=timezone.utc)
    klass = Class(
        library_name="TestLib",
        name="TestClass",
        fields={"value": Primitive.DateTime(dt)},
    )
    decoded = _roundtrip_stream(Stream(root=klass)).root
    field = decoded.fields["value"]
    assert isinstance(field, Primitive)
    assert field.type == PrimitiveType.DateTime
    assert field.value.year == 2024
    assert field.value.month == 1
    assert field.value.day == 15


# ---------------------------------------------------------------------------
# Mixed-field class round-trips
# ---------------------------------------------------------------------------


def test_mixed_class_roundtrip() -> None:
    """A class with bool, i32, f32, and array fields should round-trip."""
    klass = Class(
        library_name="Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null",
        name="RankData",
        fields={
            "ranks": PrimitiveArray.of(PrimitiveType.Int32, [-1, 0, 1, 2, 3, 4]),
            "secretsAmount": Primitive.Int32(5),
            "secretsFound": PrimitiveArray.of(
                PrimitiveType.Boolean, [True, False, True, True, False]
            ),
            "challenge": Primitive.Boolean(True),
            "levelNumber": Primitive.Int32(1),
            "majorAssists": PrimitiveArray.of(PrimitiveType.Boolean, [False] * 6),
        },
    )
    decoded = _roundtrip_stream(Stream(root=klass)).root
    assert decoded.name == "RankData"
    assert (
        decoded.library_name
        == "Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null"
    )
    assert list(decoded.fields.keys()) == [
        "ranks",
        "secretsAmount",
        "secretsFound",
        "challenge",
        "levelNumber",
        "majorAssists",
    ]
    assert decoded.fields["ranks"].values == (-1, 0, 1, 2, 3, 4)
    assert decoded.fields["secretsAmount"].value == 5
    assert decoded.fields["secretsFound"].values == (True, False, True, True, False)
    assert decoded.fields["challenge"].value is True
    assert decoded.fields["levelNumber"].value == 1
    assert decoded.fields["majorAssists"].values == (False,) * 6


def test_empty_array_roundtrip() -> None:
    """Empty arrays should round-trip correctly."""
    klass = Class(
        library_name="TestLib",
        name="TestClass",
        fields={
            "empty_bools": PrimitiveArray.of(PrimitiveType.Boolean, []),
            "empty_i32s": PrimitiveArray.of(PrimitiveType.Int32, []),
            "empty_f32s": PrimitiveArray.of(PrimitiveType.Single, []),
        },
    )
    decoded = _roundtrip_stream(Stream(root=klass)).root
    assert decoded.fields["empty_bools"].values == ()
    assert decoded.fields["empty_i32s"].values == ()
    assert decoded.fields["empty_f32s"].values == ()


def test_nested_class_roundtrip() -> None:
    """A class with a nested Class field should round-trip."""
    nested = Class(
        library_name="TestLib",
        name="Nested",
        fields={
            "x": Primitive.Int32(42),
            "y": PrimitiveArray.of(PrimitiveType.Int32, [1, 2, 3]),
        },
    )
    outer = Class(
        library_name="TestLib",
        name="Outer",
        fields={
            "flag": Primitive.Boolean(True),
            "nested": nested,
            "arr": PrimitiveArray.of(PrimitiveType.Single, [1.5, 2.5]),
        },
    )
    decoded = _roundtrip_stream(Stream(root=outer)).root
    assert decoded.fields["flag"].value is True
    assert isinstance(decoded.fields["nested"], Class)
    assert decoded.fields["nested"].name == "Nested"
    assert decoded.fields["nested"].fields["x"].value == 42
    assert decoded.fields["nested"].fields["y"].values == (1, 2, 3)
    assert decoded.fields["arr"].values == (1.5, 2.5)


# ---------------------------------------------------------------------------
# Byte stability
# ---------------------------------------------------------------------------


def test_byte_stable_mixed_class() -> None:
    """Encoding should be deterministic: encode-decode-encode yields identical bytes."""
    klass = Class(
        library_name="Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null",
        name="RankData",
        fields={
            "ranks": PrimitiveArray.of(PrimitiveType.Int32, [-1, 0, 1, 2, 3, 12]),
            "secretsAmount": Primitive.Int32(5),
            "secretsFound": PrimitiveArray.of(
                PrimitiveType.Boolean, [True, False, True, True, False]
            ),
            "challenge": Primitive.Boolean(False),
            "levelNumber": Primitive.Int32(6),
            "majorAssists": PrimitiveArray.of(PrimitiveType.Boolean, [True] * 6),
        },
    )
    assert _byte_stable(Stream(root=klass))
