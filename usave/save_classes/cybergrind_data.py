"""CybergrindData — mirrors the .NET `EndlessProgress` class.

One `endlessprogress.bepis` file, containing per-difficulty Cyber Grind stats:
  - preciseWavesByDifficulty  : single[]  (highest wave reached, with decimals)
  - bestKillsByDifficulty      : int32[]  (best kill count)
  - bestStyleByDifficulty      : int32[]  (best style score)
  - bestTimesByDifficulty      : single[] (best clear time in seconds)
  - wave                       : int32    (current wave — written as 0)

The GUI displays these as strings (so the user can type any value); we
parse them back to numbers when serializing.

Ports `class/cybergrind.rs` from the Rust project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..nrbf import Class
from .base import (
    FieldMap,
    ParsableClass,
    clone_fields,
    read_f32_array,
    read_i32_array,
    write_f32_array,
    write_i32,
    write_i32_array,
)


WAVES_FIELD = "preciseWavesByDifficulty"
KILLS_FIELD = "bestKillsByDifficulty"
STYLE_FIELD = "bestStyleByDifficulty"
TIMES_FIELD = "bestTimesByDifficulty"
WAVE_INT_FIELD = "wave"

NUM_DIFFICULTIES = 6  # the save file always has 6 slots (one per difficulty + 1 spare)


def _f32_to_str(v: float) -> str:
    """Format a float the way Rust's `f32::to_string` does.

    Rust prints floats with the minimal representation that round-trips,
    using lowercase `e` notation for very large/small numbers. Python's
    `repr(float(v))` is close enough for our purposes (we re-parse on load).
    """
    return repr(float(v))


def _str_to_f32(s: str) -> Optional[float]:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _str_to_i32(s: str) -> Optional[int]:
    try:
        return int(float(s))  # accept "3.0" as 3 like the Rust impl
    except (TypeError, ValueError):
        return None


@dataclass
class CybergrindData(ParsableClass):
    """Cyber Grind stats, one entry per difficulty."""

    waves: list[str] = field(default_factory=lambda: ["0.0"] * NUM_DIFFICULTIES)
    kills: list[str] = field(default_factory=lambda: ["0"] * NUM_DIFFICULTIES)
    style: list[str] = field(default_factory=lambda: ["0"] * NUM_DIFFICULTIES)
    times: list[str] = field(default_factory=lambda: ["0.0"] * NUM_DIFFICULTIES)
    file_exists: bool = False
    original_fields: FieldMap = field(default_factory=dict)
    dirty: bool = False
    decoded: bool = False

    CLASS_NAME = "EndlessProgress"
    FILE_NAME = "endlessprogress.bepis"

    @classmethod
    def _default(cls) -> "CybergrindData":
        return cls()

    @classmethod
    def parse(cls, klass: Class) -> "CybergrindData":
        fields = klass.fields
        waves_f = read_f32_array(fields, WAVES_FIELD)
        kills_f = read_i32_array(fields, KILLS_FIELD)
        style_f = read_i32_array(fields, STYLE_FIELD)
        times_f = read_f32_array(fields, TIMES_FIELD)
        return cls(
            waves=[_f32_to_str(v) for v in waves_f] or ["0.0"] * NUM_DIFFICULTIES,
            kills=[_f32_to_str(float(v)) for v in kills_f] or ["0"] * NUM_DIFFICULTIES,
            style=[_f32_to_str(float(v)) for v in style_f] or ["0"] * NUM_DIFFICULTIES,
            times=[_f32_to_str(v) for v in times_f] or ["0.0"] * NUM_DIFFICULTIES,
            file_exists=True,
            original_fields=clone_fields(fields),
            dirty=False,
            decoded=True,
        )

    def unparse(self) -> Optional[FieldMap]:
        fields = clone_fields(self.original_fields)
        write_i32(fields, WAVE_INT_FIELD, 0)
        write_f32_array(fields, WAVES_FIELD, [_str_to_f32(s) or 0.0 for s in self.waves])
        write_i32_array(fields, KILLS_FIELD, [_str_to_i32(s) or 0 for s in self.kills])
        write_i32_array(fields, STYLE_FIELD, [_str_to_i32(s) or 0 for s in self.style])
        write_f32_array(fields, TIMES_FIELD, [_str_to_f32(s) or 0.0 for s in self.times])
        return fields

    def save_to(self, dir_: Path) -> None:
        """Instance convenience wrapper around ParsableClass.save."""
        self.save(dir_)

    # CybergrindData inherits `delete_from(dir_)` as a classmethod from
    # ParsableClass — no override needed.
