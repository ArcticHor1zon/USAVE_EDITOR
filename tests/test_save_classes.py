"""Smoke tests for the save classes and save manager.

Verifies that:
  - Each of the 4 save classes (LevelData, DifficultyData, GeneralData,
    CybergrindData) round-trips through save -> load.
  - The save manager (Classes) loads and saves all 4 file types.
  - The YAML game data loads without errors and has expected counts.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from usave.data.schema import GAME_DATA
from usave.save_classes import (
    CybergrindData,
    DifficultyData,
    GeneralData,
    LevelData,
)
from usave.save_manager import Classes


# ---------------------------------------------------------------------------
# YAML game data sanity
# ---------------------------------------------------------------------------


def test_game_data_loads() -> None:
    """The YAML files should load without errors."""
    # 5 acts: Prelude, Act I, Act II, Act III, Encore
    # (PRIME SANCTUMS is a separate section, not an act)
    assert len(GAME_DATA.acts) == 5
    assert len(GAME_DATA.prime_sanctums) == 2
    assert len(GAME_DATA.encore_levels) == 2
    assert len(GAME_DATA.enemies) == 44
    assert len(GAME_DATA.weapon_types) == 6
    assert len(GAME_DATA.difficulties) == 5
    assert len(GAME_DATA.unlockables) == 2


def test_levels_have_unique_ids() -> None:
    """All levels (regular + prime + encore) should have unique ids."""
    ids = [lev.id for lev in GAME_DATA.iter_all_levels()]
    assert len(ids) == len(set(ids)), f"duplicate level ids: {ids}"


def test_level_lookup() -> None:
    """Looking up a level by id should return the right definition."""
    lev = GAME_DATA.get_level(1)
    assert lev is not None
    assert lev.name == "0-1: INTO THE FIRE"
    assert lev.secrets == 5

    prime = GAME_DATA.get_level(666)
    assert prime is not None
    assert prime.is_prime
    assert prime.prime_index == 0


# ---------------------------------------------------------------------------
# LevelData
# ---------------------------------------------------------------------------


def test_level_data_roundtrip() -> None:
    level = GAME_DATA.get_level(1)
    assert level is not None

    data = LevelData.create_new(level)
    data.ranks = [-1, 0, 1, 2, 3, 12]  # last is P
    data.secrets_found = [True, True, True, True, True]
    data.challenge = True
    data.major_assists = [False, True, False, True, False, True]
    data.file_exists = True

    with tempfile.TemporaryDirectory() as td:
        save_dir = Path(td)
        data.save_to(level, save_dir)

        loaded = LevelData.load_one(level, save_dir)
        assert loaded.file_exists
        assert loaded.decoded
        assert loaded.ranks == [-1, 0, 1, 2, 3, 12]
        assert loaded.secrets_found == [True, True, True, True, True]
        assert loaded.challenge is True
        assert loaded.major_assists == [False, True, False, True, False, True]


def test_level_data_secret_count() -> None:
    """create_new should populate secrets_found based on the level's secret count."""
    for level in GAME_DATA.iter_all_levels():
        data = LevelData.create_new(level)
        assert len(data.secrets_found) == level.secrets, (
            f"level {level.name}: expected {level.secrets} secrets, "
            f"got {len(data.secrets_found)}"
        )


# ---------------------------------------------------------------------------
# DifficultyData
# ---------------------------------------------------------------------------


def test_difficulty_data_roundtrip() -> None:
    diff = GAME_DATA.get_difficulty(2)  # Standard
    assert diff is not None

    data = DifficultyData.create_new(diff)
    data.current_level = 5  # Cerberus
    data.prime_levels = [1, 2]  # Unlocked, Completed
    data.file_exists = True

    with tempfile.TemporaryDirectory() as td:
        save_dir = Path(td)
        data.save_to(diff, save_dir)

        loaded = DifficultyData.load_one(diff, save_dir)
        assert loaded.file_exists
        assert loaded.decoded
        assert loaded.current_level == 5
        assert loaded.prime_levels == [1, 2]


# ---------------------------------------------------------------------------
# GeneralData
# ---------------------------------------------------------------------------


def test_general_data_roundtrip() -> None:
    data = GeneralData()
    data.money = "99999"
    data.intro_seen = True
    data.tutorial_beat = True
    data.clash_mode_unlocked = True
    data.unlocked_weapons["Piercer Revolver"] = True
    data.unlocked_weapons["Knuckleblaster"] = True
    data.enemies_discovered["Cerberus"] = 2  # Completed
    data.unlockables_found["Florp"] = True
    data.weapons_customizable["Revolver"] = True
    data.file_exists = True

    with tempfile.TemporaryDirectory() as td:
        save_dir = Path(td)
        data.save_to(save_dir)

        loaded = GeneralData.load(save_dir)
        assert loaded.file_exists
        assert loaded.decoded
        assert loaded.money == "99999"
        assert loaded.intro_seen is True
        assert loaded.tutorial_beat is True
        assert loaded.clash_mode_unlocked is True
        assert loaded.unlocked_weapons["Piercer Revolver"] is True
        assert loaded.unlocked_weapons["Knuckleblaster"] is True
        assert loaded.enemies_discovered["Cerberus"] == 2
        assert loaded.unlockables_found["Florp"] is True
        assert loaded.weapons_customizable["Revolver"] is True


def test_general_data_defaults() -> None:
    """A fresh GeneralData should have entries for every weapon/enemy/unlockable."""
    data = GeneralData()
    # 20 weapon variants across 6 weapon types
    total_variants = sum(len(w.variants) for w in GAME_DATA.weapon_types)
    assert len(data.unlocked_weapons) == total_variants
    # 5 customizable weapon types (Arm is not customizable)
    assert len(data.weapons_customizable) == 5
    assert len(data.enemies_discovered) == len(GAME_DATA.enemies)
    assert len(data.unlockables_found) == len(GAME_DATA.unlockables)


# ---------------------------------------------------------------------------
# CybergrindData
# ---------------------------------------------------------------------------


def test_cybergrind_data_roundtrip() -> None:
    data = CybergrindData()
    data.waves[2] = "99.5"  # Standard
    data.kills[2] = "300"
    data.style[2] = "25000"
    data.times[2] = "180.5"
    data.file_exists = True

    with tempfile.TemporaryDirectory() as td:
        save_dir = Path(td)
        data.save_to(save_dir)

        loaded = CybergrindData.load(save_dir)
        assert loaded.file_exists
        assert loaded.decoded
        assert float(loaded.waves[2]) == 99.5
        assert float(loaded.kills[2]) == 300
        assert float(loaded.style[2]) == 25000
        assert float(loaded.times[2]) == 180.5


# ---------------------------------------------------------------------------
# Save manager (Classes)
# ---------------------------------------------------------------------------


def test_classes_load_empty_dir() -> None:
    """Loading from an empty dir should produce all defaults."""
    with tempfile.TemporaryDirectory() as td:
        save_dir = Path(td)
        classes = Classes.load(save_dir)
        assert len(classes.levels) == len(list(GAME_DATA.iter_all_levels()))
        assert len(classes.difficulty) == len(GAME_DATA.difficulties)
        assert classes.general.file_exists is False
        assert classes.cybergrind.file_exists is False
        for data in classes.levels.values():
            assert data.file_exists is False
            assert data.decoded is False


def test_classes_save_dirty() -> None:
    """save_dirty should only write entries marked dirty AND decoded."""
    with tempfile.TemporaryDirectory() as td:
        save_dir = Path(td)

        classes = Classes.load(save_dir)
        # Make level 1 dirty
        classes.levels[1].ranks = [-1, 0, 1, 2, 3, 12]
        classes.levels[1].file_exists = True
        classes.levels[1].dirty = True
        classes.levels[1].decoded = True

        # Make general dirty
        classes.general.money = "12345"
        classes.general.file_exists = True
        classes.general.dirty = True
        classes.general.decoded = True

        classes.save_dirty(save_dir)
        classes.clear_dirty()

        # Verify the right files were created
        assert (save_dir / "lvl1progress.bepis").exists()
        assert (save_dir / "generalprogress.bepis").exists()
        # Other levels should NOT have files
        assert not (save_dir / "lvl2progress.bepis").exists()
        assert not (save_dir / "endlessprogress.bepis").exists()

        # Reload and verify
        classes2 = Classes.load(save_dir)
        assert classes2.levels[1].ranks == [-1, 0, 1, 2, 3, 12]
        assert classes2.general.money == "12345"
