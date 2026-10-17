"""ms-nrbf — .NET Binary Format (NRBF) parser/serializer for Python.

A pure-Python port of the `ms-nrbf` Rust crate from the original
ULTRAKILL Save Editor. Reads and writes the binary serialization
format used by .NET's `BinaryFormatter`, which ULTRAKILL uses for
its `.bepis` save files.

Public API:
    Stream          — top-level container with a single root Class
    Class           — a decoded .NET class instance (library_name, name, fields)
    Field           — Primitive | PrimitiveArray | Class
    Primitive       — a single primitive value (typed)
    PrimitiveArray  — a typed array of primitives
    PrimitiveType   — enum of the 17 NRBF primitive type codes
"""

from .primitives import (
    AdditionalInfo,
    BinaryType,
    Primitive,
    PrimitiveArray,
    PrimitiveType,
)
from .stream import Class, Field, Stream

__all__ = [
    "Stream",
    "Class",
    "Field",
    "Primitive",
    "PrimitiveArray",
    "PrimitiveType",
    "BinaryType",
    "AdditionalInfo",
]
