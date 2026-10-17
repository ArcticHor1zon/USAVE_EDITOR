"""Base classes and helpers for save file data classes.

A "save class" is a Python dataclass that mirrors a .NET class found in
a `.bepis` save file. It knows:
  - its .NET class name (e.g. "RankData")
  - its save file name (e.g. "lvl1progress.bepis")
  - how to parse its fields from a decoded `Class`
  - how to serialize its fields back into a `FieldMap`

There are two flavors:
  - `ParsableClass`       — for single-file classes (generalprogress.bepis,
                            endlessprogress.bepis)
  - `ParsableClassKeyed`  — for keyed classes (lvl{N}progress.bepis,
                            difficulty{N}progress.bepis), where one Python
                            class is instantiated per enum value (Level,
                            Difficulty).

Ports the trait machinery from `class/traits.rs` and `class/helpers.rs`.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..nrbf import Class, Field, Primitive, PrimitiveArray, PrimitiveType, Stream

# The .NET assembly name ULTRAKILL saves use. Every class we serialize
# is tagged with this library name.
LIBRARY_NAME = "Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null"

# A FieldMap is an ordered dict of field name -> Field value.
# We preserve insertion order so re-serialization is byte-stable.
FieldMap = dict  # dict[str, Field]


# ---------------------------------------------------------------------------
# Field read/write helpers (ports `class/helpers.rs`)
# ---------------------------------------------------------------------------


def read_bool(fields: FieldMap, name: str) -> bool:
    f = fields.get(name)
    if isinstance(f, Primitive) and f.type == PrimitiveType.Boolean:
        return bool(f.value)
    return False


def read_i32(fields: FieldMap, name: str) -> int:
    f = fields.get(name)
    if isinstance(f, Primitive) and f.type == PrimitiveType.Int32:
        return int(f.value)
    return 0


def read_f32(fields: FieldMap, name: str) -> float:
    f = fields.get(name)
    if isinstance(f, Primitive) and f.type == PrimitiveType.Single:
        return float(f.value)
    return 0.0


def read_bool_array(fields: FieldMap, name: str) -> list[bool]:
    f = fields.get(name)
    if isinstance(f, PrimitiveArray) and f.type == PrimitiveType.Boolean:
        return [bool(v) for v in f.values]
    return []


def read_i32_array(fields: FieldMap, name: str) -> list[int]:
    f = fields.get(name)
    if isinstance(f, PrimitiveArray) and f.type == PrimitiveType.Int32:
        return [int(v) for v in f.values]
    return []


def read_f32_array(fields: FieldMap, name: str) -> list[float]:
    f = fields.get(name)
    if isinstance(f, PrimitiveArray) and f.type == PrimitiveType.Single:
        return [float(v) for v in f.values]
    return []


def write_bool(fields: FieldMap, name: str, value: bool) -> None:
    fields[name] = Primitive.Boolean(value)


def write_i32(fields: FieldMap, name: str, value: int) -> None:
    fields[name] = Primitive.Int32(value)


def write_f32(fields: FieldMap, name: str, value: float) -> None:
    fields[name] = Primitive.Single(value)


def write_bool_array(fields: FieldMap, name: str, value: list[bool]) -> None:
    fields[name] = PrimitiveArray.of(PrimitiveType.Boolean, value)


def write_i32_array(fields: FieldMap, name: str, value: list[int]) -> None:
    fields[name] = PrimitiveArray.of(PrimitiveType.Int32, value)


def write_f32_array(fields: FieldMap, name: str, value: list[float]) -> None:
    fields[name] = PrimitiveArray.of(PrimitiveType.Single, value)


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------


class ParsableClass(ABC):
    """Base for single-file save classes (one .bepis file per class instance).

    Subclasses must define CLASS_NAME and FILE_NAME class attributes and
    implement parse() and unparse().
    """

    CLASS_NAME: str = ""
    FILE_NAME: str = ""

    # Common state flags (mirrored from the Rust impl).
    file_exists: bool = False
    decoded: bool = False
    dirty: bool = False
    original_fields: FieldMap = field(default_factory=dict)

    @classmethod
    @abstractmethod
    def parse(cls, klass: Class) -> "ParsableClass":
        """Build an instance from a decoded NRBF Class."""

    @abstractmethod
    def unparse(self) -> Optional[FieldMap]:
        """Serialize this instance back to a FieldMap, or None to skip writing."""

    # ------------------------------------------------------------------
    # Load / save (ports the `LoadableSavable` impl)
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, save_dir: Path) -> "ParsableClass":
        """Load from `save_dir / FILE_NAME`. Returns a default instance if absent."""
        path = save_dir / cls.FILE_NAME
        if not path.exists():
            return cls._default()
        try:
            with path.open("rb") as f:
                stream = Stream.decode(f)
            instance = cls.parse(stream.root)
            return instance
        except Exception:
            # File exists but couldn't parse — return a default with file_exists=True
            instance = cls._default()
            instance.file_exists = True
            return instance

    def save(self, save_dir: Path) -> None:
        """Save to `save_dir / FILE_NAME`, or delete the file if it shouldn't exist."""
        path = save_dir / self.FILE_NAME
        if self.file_exists:
            fields = self.unparse()
            if fields is None:
                return
            klass = Class(library_name=LIBRARY_NAME, name=self.CLASS_NAME, fields=fields)
            with path.open("wb") as f:
                Stream(root=klass).encode(f)
        elif path.exists():
            path.unlink()

    @classmethod
    def delete_from(cls, save_dir: Path) -> None:
        path = save_dir / cls.FILE_NAME
        if path.exists():
            path.unlink()

    @classmethod
    def _default(cls) -> "ParsableClass":
        """Subclasses override to provide a fresh default instance."""
        raise NotImplementedError


class ParsableClassKeyed(ABC):
    """Base for keyed save classes (one .bepis file per enum value).

    Subclasses define CLASS_NAME, FILE_PREFIX, FILE_SUFFIX, and implement
    create_new(), parse(), and unparse(key).
    """

    CLASS_NAME: str = ""
    FILE_PREFIX: str = ""
    FILE_SUFFIX: str = ""

    file_exists: bool = False
    decoded: bool = False
    dirty: bool = False
    original_fields: FieldMap = field(default_factory=dict)

    @classmethod
    @abstractmethod
    def create_new(cls, key) -> "ParsableClassKeyed":
        """Build a fresh default instance for the given key."""

    @classmethod
    @abstractmethod
    def parse(cls, klass: Class) -> "ParsableClassKeyed":
        """Build an instance from a decoded NRBF Class."""

    @abstractmethod
    def unparse(self, key) -> Optional[FieldMap]:
        """Serialize this instance back to a FieldMap, or None to skip writing."""

    # ------------------------------------------------------------------
    # File path helpers
    # ------------------------------------------------------------------

    @classmethod
    def file_name_for(cls, key) -> str:
        return f"{cls.FILE_PREFIX}{_key_to_infix(key)}{cls.FILE_SUFFIX}"

    @classmethod
    def file_path_for(cls, key, save_dir: Path) -> Path:
        return save_dir / cls.file_name_for(key)

    # ------------------------------------------------------------------
    # Load / save single instance
    # ------------------------------------------------------------------

    @classmethod
    def load_one(cls, key, save_dir: Path) -> "ParsableClassKeyed":
        path = cls.file_path_for(key, save_dir)
        if not path.exists():
            return cls.create_new(key)
        try:
            with path.open("rb") as f:
                stream = Stream.decode(f)
            return cls.parse(stream.root)
        except Exception:
            instance = cls.create_new(key)
            instance.file_exists = True
            return instance

    def save_one(self, key, save_dir: Path) -> None:
        path = self.file_path_for(key, save_dir)
        if self.file_exists:
            fields = self.unparse(key)
            if fields is None:
                return
            klass = Class(library_name=LIBRARY_NAME, name=self.CLASS_NAME, fields=fields)
            with path.open("wb") as f:
                Stream(root=klass).encode(f)
        elif path.exists():
            path.unlink()

    @classmethod
    def delete_one(cls, key, save_dir: Path) -> None:
        path = cls.file_path_for(key, save_dir)
        if path.exists():
            path.unlink()


def _key_to_infix(key) -> str:
    """Convert a key (Level/Difficulty) to its filename infix.

    Mirrors the `IntoFileInfix` trait from the Rust impl:
      - Difficulty (u8)  -> str(int)
      - Level (u16)      -> str(int)
    """
    if hasattr(key, "value"):  # IntEnum
        return str(int(key.value))
    if hasattr(key, "id"):  # our dataclass defs
        return str(int(key.id))
    return str(int(key))


# ---------------------------------------------------------------------------
# Helpers for subclasses
# ---------------------------------------------------------------------------


def clone_fields(fields: FieldMap) -> FieldMap:
    """Deep-copy a FieldMap so the subclass can mutate its working copy
    without disturbing the `original_fields` snapshot.
    """
    return copy.deepcopy(fields)
