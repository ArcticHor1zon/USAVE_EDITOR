"""Save manager — orchestrates loading and saving all four save file types.

The `Classes` dataclass is the top-level container the GUI works with.
It holds:
  - levels: dict[int, LevelData]       (one per LevelDef in the schema)
  - difficulty: dict[int, DifficultyData]  (one per DifficultyDef)
  - general: GeneralData
  - cybergrind: CybergrindData

Each entry tracks its own `dirty` flag; `save_dirty()` writes only the
entries that changed since the last save.

Ports `class/classes.rs` and the dirty-tracking logic from `app.rs`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .data.schema import GAME_DATA, DifficultyDef, LevelDef
from .save_classes import (
    CybergrindData,
    DifficultyData,
    GeneralData,
    LevelData,
)


@dataclass
class Classes:
    """Container for all loaded save data."""

    levels: dict[int, LevelData] = field(default_factory=dict)
    difficulty: dict[int, DifficultyData] = field(default_factory=dict)
    general: GeneralData = field(default_factory=GeneralData)
    cybergrind: CybergrindData = field(default_factory=CybergrindData)

    @classmethod
    def load(cls, save_dir: Path) -> "Classes":
        """Load all four save file types from `save_dir`.

        Missing files produce default instances with `file_exists=False`
        and `decoded=False`, matching the original Rust behavior.
        """
        levels: dict[int, LevelData] = {}
        for level in GAME_DATA.iter_all_levels():
            levels[level.id] = LevelData.load_one(level, save_dir)

        difficulty: dict[int, DifficultyData] = {}
        for d in GAME_DATA.difficulties:
            difficulty[d.id] = DifficultyData.load_one(d, save_dir)

        general = GeneralData.load(save_dir)
        cybergrind = CybergrindData.load(save_dir)

        return cls(
            levels=levels,
            difficulty=difficulty,
            general=general,
            cybergrind=cybergrind,
        )

    def save_all(self, save_dir: Path) -> None:
        """Save every entry, regardless of dirty flag."""
        for level_id, data in self.levels.items():
            level = GAME_DATA.get_level(level_id)
            if level is not None:
                data.save_to(level, save_dir)
        for d in GAME_DATA.difficulties:
            data = self.difficulty.get(d.id)
            if data is not None:
                data.save_to(d, save_dir)
        self.general.save(save_dir)
        self.cybergrind.save(save_dir)

    def save_dirty(self, save_dir: Path) -> None:
        """Save only entries marked dirty AND decoded (matches original behavior)."""
        if self.general.dirty and self.general.decoded:
            try:
                self.general.save_to(save_dir)
            except Exception as e:
                print(f"[ERROR] Save generalprogress.bepis failed: {e}")

        if self.cybergrind.dirty and self.cybergrind.decoded:
            try:
                self.cybergrind.save_to(save_dir)
            except Exception as e:
                print(f"[ERROR] Save endlessprogress.bepis failed: {e}")

        for d in GAME_DATA.difficulties:
            data = self.difficulty.get(d.id)
            if data is None:
                continue
            if data.dirty and data.decoded:
                try:
                    data.save_to(d, save_dir)
                except Exception as e:
                    print(f"[ERROR] Save difficulty{d.id}progress.bepis failed: {e}")

        for level_id, data in self.levels.items():
            if not (data.dirty and data.decoded):
                continue
            level = GAME_DATA.get_level(level_id)
            if level is None:
                continue
            try:
                data.save_to(level, save_dir)
            except Exception as e:
                print(f"[ERROR] Save lvl{level_id}progress.bepis failed: {e}")

    def clear_dirty(self) -> None:
        """Clear the dirty flag on every entry (call after save_dirty)."""
        self.general.dirty = False
        self.cybergrind.dirty = False
        for data in self.difficulty.values():
            data.dirty = False
        for data in self.levels.values():
            data.dirty = False

    def mark_dirty_if_loaded(self) -> None:
        """Mark general/cybergrind dirty if their files exist (matches original).

        Used by the GUI after any interaction — the original egui app did this
        every frame where input was detected.
        """
        if self.general.file_exists:
            self.general.dirty = True
        if self.cybergrind.file_exists:
            self.cybergrind.dirty = True
