"""DifficultyData — mirrors the .NET `GameProgressMoneyAndGearDifficulty` class.

One `difficulty{N}progress.bepis` file per difficulty, containing:
  - levelNum     : int   (the current level the player is on)
  - primeLevels  : int[] (Lockable state for each Prime Sanctum)

Ports `class/difficulty.rs` from the Rust project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..data.schema import GAME_DATA, DifficultyDef, LevelDef
from ..nrbf import Class
from .base import (
    FieldMap,
    ParsableClassKeyed,
    clone_fields,
    read_i32,
    read_i32_array,
    write_i32,
    write_i32_array,
)


CURRENT_LEVEL_FIELD = "levelNum"
PRIME_LEVELS_FIELD = "primeLevels"


# Lockable enum (ports the u8 Lockable enum from `enums.rs`).
LOCKABLE_LOCKED = 0
LOCKABLE_UNLOCKED = 1
LOCKABLE_COMPLETED = 2
LOCKABLE_LABELS = {
    LOCKABLE_LOCKED: "Locked",
    LOCKABLE_UNLOCKED: "Unlocked",
    LOCKABLE_COMPLETED: "Completed",
}


@dataclass
class DifficultyData(ParsableClassKeyed):
    """Save data for a single difficulty slot."""

    current_level: int = 1  # Level id (default: Into The Fire = 1)
    prime_levels: list[int] = field(default_factory=list)  # one Lockable per prime sanctum
    file_exists: bool = False
    original_fields: FieldMap = field(default_factory=dict)
    dirty: bool = False
    decoded: bool = False

    CLASS_NAME = "GameProgressMoneyAndGearDifficulty"
    FILE_PREFIX = "difficulty"
    FILE_SUFFIX = "progress.bepis"

    @classmethod
    def create_new(cls, key) -> "DifficultyData":
        # Default: 2 prime levels, both Locked; current level = 1 (Into The Fire).
        return cls(
            current_level=1,
            prime_levels=[LOCKABLE_LOCKED] * 2,
            file_exists=False,
            original_fields={},
            dirty=False,
            decoded=False,
        )

    @classmethod
    def parse(cls, klass: Class) -> "DifficultyData":
        fields = klass.fields
        level_num = read_i32(fields, CURRENT_LEVEL_FIELD)
        # Validate the level id exists in our schema; default to 1 if not.
        if GAME_DATA.get_level(level_num) is None:
            level_num = 1
        prime_levels_raw = read_i32_array(fields, PRIME_LEVELS_FIELD)
        prime_levels = []
        for v in prime_levels_raw:
            if v in (LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED):
                prime_levels.append(v)
            else:
                prime_levels.append(LOCKABLE_LOCKED)
        return cls(
            current_level=level_num,
            prime_levels=prime_levels,
            file_exists=True,
            original_fields=clone_fields(fields),
            dirty=False,
            decoded=True,
        )

    def unparse(self, key) -> Optional[FieldMap]:
        fields = clone_fields(self.original_fields)
        write_i32(fields, CURRENT_LEVEL_FIELD, self.current_level)
        write_i32_array(fields, PRIME_LEVELS_FIELD, list(self.prime_levels))
        return fields

    def save_to(self, difficulty: DifficultyDef, dir_: Path) -> None:
        self.save_one(difficulty, dir_)

    @classmethod
    def delete_from(cls, difficulty: DifficultyDef, dir_: Path) -> None:
        cls.delete_one(difficulty, dir_)
