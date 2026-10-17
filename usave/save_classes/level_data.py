"""LevelData — mirrors the .NET `RankData` class.

One `lvl{N}progress.bepis` file per level, containing:
  - ranks           : int[]   (one per difficulty, length 6)
  - secretsAmount   : int
  - secretsFound    : bool[]  (one per secret skull in the level)
  - challenge       : bool
  - levelNumber     : int
  - majorAssists    : bool[]  (one per difficulty, length 6)

Ports `class/level.rs` from the Rust project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..data.schema import GAME_DATA, LevelDef
from ..nrbf import Class
from .base import (
    FieldMap,
    ParsableClassKeyed,
    clone_fields,
    read_bool,
    read_bool_array,
    read_i32_array,
    write_bool,
    write_bool_array,
    write_i32,
    write_i32_array,
)


# Field name constants (match the .NET class field names).
RANKS_FIELD = "ranks"
SECRETS_AMOUNT_FIELD = "secretsAmount"
SECRETS_FOUND_FIELD = "secretsFound"
CHALLENGE_FIELD = "challenge"
LEVEL_NUMBER_FIELD = "levelNumber"
MAJOR_ASSISTS_FIELD = "majorAssists"


# LevelRank enum (ports the i8 LevelRank enum from `enums.rs`).
# Stored as an int. The .NET save uses i32; the conversion is:
#   <0  -> None (-1)
#   0   -> D
#   1   -> C
#   2   -> B
#   3   -> A
#   4-11 -> S
#   12  -> P
LEVEL_RANK_NONE = -1
LEVEL_RANK_D = 0
LEVEL_RANK_C = 1
LEVEL_RANK_B = 2
LEVEL_RANK_A = 3
LEVEL_RANK_S = 4  # any value 4-11 maps to S
LEVEL_RANK_P = 12
ALL_RANKS = [LEVEL_RANK_NONE, LEVEL_RANK_D, LEVEL_RANK_C, LEVEL_RANK_B, LEVEL_RANK_A, LEVEL_RANK_S, LEVEL_RANK_P]
RANK_LABELS = {
    LEVEL_RANK_NONE: "None",
    LEVEL_RANK_D: "D",
    LEVEL_RANK_C: "C",
    LEVEL_RANK_B: "B",
    LEVEL_RANK_A: "A",
    LEVEL_RANK_S: "S",
    LEVEL_RANK_P: "P",
}


def rank_from_i32(value: int) -> int:
    """Convert a raw i32 from the save file into a canonical LevelRank int."""
    if value < 0:
        return LEVEL_RANK_NONE
    if value == 1:
        return LEVEL_RANK_C
    if value == 2:
        return LEVEL_RANK_B
    if value == 3:
        return LEVEL_RANK_A
    if 4 <= value <= 11:
        return LEVEL_RANK_S
    if value == 12:
        return LEVEL_RANK_P
    return LEVEL_RANK_D


def rank_to_i32(rank: int) -> int:
    """Convert a canonical LevelRank int back to the raw i32 to write."""
    if rank == LEVEL_RANK_S:
        return 4  # write the lowest S-band value
    return rank


@dataclass
class LevelData(ParsableClassKeyed):
    """Save data for a single level."""

    ranks: list[int] = field(default_factory=list)  # one per difficulty (length 6)
    secrets_found: list[bool] = field(default_factory=list)
    challenge: bool = False
    major_assists: list[bool] = field(default_factory=list)  # one per difficulty (length 6)
    file_exists: bool = False
    original_fields: FieldMap = field(default_factory=dict)
    dirty: bool = False
    decoded: bool = False

    CLASS_NAME = "RankData"
    FILE_PREFIX = "lvl"
    FILE_SUFFIX = "progress.bepis"

    @classmethod
    def create_new(cls, key) -> "LevelData":
        # `key` is a LevelDef from our YAML schema.
        level: LevelDef = key if isinstance(key, LevelDef) else GAME_DATA.get_level(int(key))
        return cls(
            ranks=[LEVEL_RANK_NONE] * 6,
            secrets_found=[False] * level.secrets,
            challenge=False,
            major_assists=[False] * 6,
            file_exists=False,
            original_fields={},
            dirty=False,
            decoded=False,
        )

    @classmethod
    def parse(cls, klass: Class) -> "LevelData":
        fields = klass.fields
        return cls(
            ranks=[rank_from_i32(v) for v in read_i32_array(fields, RANKS_FIELD)],
            secrets_found=read_bool_array(fields, SECRETS_FOUND_FIELD),
            challenge=read_bool(fields, CHALLENGE_FIELD),
            major_assists=read_bool_array(fields, MAJOR_ASSISTS_FIELD),
            file_exists=True,
            original_fields=clone_fields(fields),
            dirty=False,
            decoded=True,
        )

    def unparse(self, key) -> Optional[FieldMap]:
        level: LevelDef = key if isinstance(key, LevelDef) else GAME_DATA.get_level(int(key))
        fields = clone_fields(self.original_fields)
        write_i32_array(fields, RANKS_FIELD, [rank_to_i32(r) for r in self.ranks])
        write_i32(fields, SECRETS_AMOUNT_FIELD, len(self.secrets_found))
        write_bool_array(fields, SECRETS_FOUND_FIELD, list(self.secrets_found))
        write_bool(fields, CHALLENGE_FIELD, self.challenge)
        write_i32(fields, LEVEL_NUMBER_FIELD, level.id)
        write_bool_array(fields, MAJOR_ASSISTS_FIELD, list(self.major_assists))
        return fields

    # Convenience wrappers that take a LevelDef directly.

    def save_to(self, level: LevelDef, dir_: Path) -> None:
        self.save_one(level, dir_)

    @classmethod
    def delete_from(cls, level: LevelDef, dir_: Path) -> None:
        cls.delete_one(level, dir_)
