"""GeneralData — mirrors the .NET `GameProgressMoneyAndGear` class.

One `generalprogress.bepis` file, containing money, tutorial state,
weapon unlocks, weapon customization unlocks, secret mission states,
enemy discovery states, and unlockable collection states.

The weapon/enemy/unlockable mappings are read from the YAML config
files in `usave/data/` (instead of being hardcoded as in the Rust
original), so adding new content when ULTRAKILL updates is just a
YAML edit.

Ports `class/general.rs` from the Rust project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..data.schema import (
    GAME_DATA,
    EnemyDef,
    LayerDef,
    SecretLevelDef,
    UnlockableDef,
    WeaponTypeDef,
    WeaponVariantDef,
)
from ..nrbf import Class, Field, PrimitiveArray, PrimitiveType
from .base import (
    FieldMap,
    ParsableClass,
    clone_fields,
    read_bool,
    read_bool_array,
    read_i32,
    read_i32_array,
    write_bool,
    write_i32,
    write_bool_array,
    write_i32_array,
)


# Field name constants — must match the .NET class field names exactly.
MONEY_FIELD = "money"
INTRO_SEEN_FIELD = "introSeen"
TUTORIAL_BEAT_FIELD = "tutorialBeat"
CLASH_MODE_UNLOCKED_FIELD = "clashModeUnlocked"
SECRET_MISSIONS_FIELD = "secretMissions"
LIMBO_SWITCHES_FIELD = "limboSwitches"
ENEMIES_DISCOVERED_FIELD = "newEnemiesFound"
UNLOCKABLES_FOUND_FIELD = "unlockablesFound"


# Lockable constants (re-exported from difficulty_data for convenience).
LOCKABLE_LOCKED = 0
LOCKABLE_UNLOCKED = 1
LOCKABLE_COMPLETED = 2


@dataclass
class GeneralData(ParsableClass):
    """General save data (money, weapons, enemies, unlockables, secrets)."""

    money: str = "0"
    intro_seen: bool = False
    tutorial_beat: bool = False
    clash_mode_unlocked: bool = False

    # Map of weapon variant name -> unlocked bool.
    # We key by name (not field) so the YAML can change field names
    # without breaking in-flight saves.
    unlocked_weapons: dict[str, bool] = field(default_factory=dict)
    # Map of secret level name -> Lockable int.
    secret_missions: dict[str, int] = field(default_factory=dict)
    # 4 limbo switches.
    limbo_switches: list[bool] = field(default_factory=lambda: [False] * 4)
    # Map of enemy name -> Lockable int.
    enemies_discovered: dict[str, int] = field(default_factory=dict)
    # Map of unlockable name -> found bool.
    unlockables_found: dict[str, bool] = field(default_factory=dict)
    # Map of weapon type name -> customizable bool.
    weapons_customizable: dict[str, bool] = field(default_factory=dict)

    file_exists: bool = False
    original_fields: FieldMap = field(default_factory=dict)
    dirty: bool = False
    decoded: bool = False

    CLASS_NAME = "GameProgressMoneyAndGear"
    FILE_NAME = "generalprogress.bepis"

    def __post_init__(self) -> None:
        # Initialize default state from the YAML schema so the GUI has
        # something to show even before a save file is loaded.
        if not self.unlocked_weapons:
            self.unlocked_weapons = {
                v.name: False for w in GAME_DATA.weapon_types for v in w.variants
            }
        if not self.secret_missions:
            self.secret_missions = {
                sl.name: LOCKABLE_LOCKED
                for act in GAME_DATA.acts
                for layer in act.layers
                if layer.secret_level and not layer.secret_level.is_prime and not layer.secret_level.is_encore
                for sl in [layer.secret_level]
            }
        if not self.enemies_discovered:
            self.enemies_discovered = {e.name: LOCKABLE_LOCKED for e in GAME_DATA.enemies}
        if not self.unlockables_found:
            self.unlockables_found = {u.name: False for u in GAME_DATA.unlockables}
        if not self.weapons_customizable:
            self.weapons_customizable = {
                w.name: False for w in GAME_DATA.weapon_types if w.is_customizable
            }

    @classmethod
    def _default(cls) -> "GeneralData":
        return cls()

    @classmethod
    def parse(cls, klass: Class) -> "GeneralData":
        fields = klass.fields

        # Parse secret_missions: int[] indexed by layer index -> Lockable.
        secret_missions_arr = read_i32_array(fields, SECRET_MISSIONS_FIELD)
        secret_missions: dict[str, int] = {}
        all_layers = [layer for act in GAME_DATA.acts for layer in act.layers]
        for i, lockable_raw in enumerate(secret_missions_arr):
            if i >= len(all_layers):
                break
            layer = all_layers[i]
            if layer.secret_level and not layer.secret_level.is_prime and not layer.secret_level.is_encore:
                if lockable_raw in (LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED):
                    secret_missions[layer.secret_level.name] = lockable_raw
                else:
                    secret_missions[layer.secret_level.name] = LOCKABLE_LOCKED

        # Parse enemies_discovered: int[] indexed by enemy id -> Lockable.
        enemies_arr = read_i32_array(fields, ENEMIES_DISCOVERED_FIELD)
        enemies_discovered: dict[str, int] = {}
        for i, lockable_raw in enumerate(enemies_arr):
            enemy = GAME_DATA.get_enemy(i)
            if enemy is None:
                continue
            if lockable_raw in (LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED):
                enemies_discovered[enemy.name] = lockable_raw
            else:
                enemies_discovered[enemy.name] = LOCKABLE_LOCKED

        # Parse unlockables_found: bool[] indexed by unlockable id -> bool.
        unlockables_arr = read_bool_array(fields, UNLOCKABLES_FOUND_FIELD)
        unlockables_found: dict[str, bool] = {}
        for i, found in enumerate(unlockables_arr):
            unlockable = GAME_DATA.get_unlockable(i)
            if unlockable is None:
                continue
            unlockables_found[unlockable.name] = bool(found)

        # Parse weapon customization unlocks (one bool field per customizable type).
        weapons_customizable: dict[str, bool] = {}
        for w in GAME_DATA.weapon_types:
            if w.is_customizable:
                weapons_customizable[w.name] = read_bool(fields, w.customization_field)

        # Parse weapon variant unlocks (one int field per variant, treated as bool).
        unlocked_weapons: dict[str, bool] = {}
        for w in GAME_DATA.weapon_types:
            for v in w.variants:
                unlocked_weapons[v.name] = read_i32(fields, v.field) != 0

        return cls(
            money=str(read_i32(fields, MONEY_FIELD)),
            intro_seen=read_bool(fields, INTRO_SEEN_FIELD),
            tutorial_beat=read_bool(fields, TUTORIAL_BEAT_FIELD),
            clash_mode_unlocked=read_bool(fields, CLASH_MODE_UNLOCKED_FIELD),
            unlocked_weapons=unlocked_weapons,
            secret_missions=secret_missions,
            limbo_switches=read_bool_array(fields, LIMBO_SWITCHES_FIELD) or [False] * 4,
            enemies_discovered=enemies_discovered,
            unlockables_found=unlockables_found,
            weapons_customizable=weapons_customizable,
            file_exists=True,
            original_fields=clone_fields(fields),
            dirty=False,
            decoded=True,
        )

    def unparse(self) -> Optional[FieldMap]:
        fields = clone_fields(self.original_fields)

        try:
            money_int = int(self.money)
        except (TypeError, ValueError):
            return None
        write_i32(fields, MONEY_FIELD, money_int)
        write_bool(fields, INTRO_SEEN_FIELD, self.intro_seen)
        write_bool(fields, TUTORIAL_BEAT_FIELD, self.tutorial_beat)
        write_bool(fields, CLASH_MODE_UNLOCKED_FIELD, self.clash_mode_unlocked)

        # secretMissions: one int per layer (in act/layer order), using
        # the layer's secret_level name as the lookup key.
        all_layers = [layer for act in GAME_DATA.acts for layer in act.layers]
        secret_arr = []
        for layer in all_layers:
            if layer.secret_level is None:
                secret_arr.append(LOCKABLE_LOCKED)
            else:
                secret_arr.append(self.secret_missions.get(layer.secret_level.name, LOCKABLE_LOCKED))
        write_i32_array(fields, SECRET_MISSIONS_FIELD, secret_arr)

        # limboSwitches: only write if non-empty (matches original behavior).
        if self.limbo_switches:
            write_bool_array(fields, LIMBO_SWITCHES_FIELD, list(self.limbo_switches))

        # newEnemiesFound: one int per enemy (in id order).
        enemies_arr = [
            self.enemies_discovered.get(e.name, LOCKABLE_LOCKED)
            for e in GAME_DATA.enemies
        ]
        write_i32_array(fields, ENEMIES_DISCOVERED_FIELD, enemies_arr)

        # unlockablesFound: one bool per unlockable (in id order).
        if self.unlockables_found:
            unlockables_arr = [
                self.unlockables_found.get(u.name, False)
                for u in GAME_DATA.unlockables
            ]
            write_bool_array(fields, UNLOCKABLES_FOUND_FIELD, unlockables_arr)

        # Weapon customization bools (one per customizable weapon type).
        for w in GAME_DATA.weapon_types:
            if w.is_customizable:
                write_bool(fields, w.customization_field, self.weapons_customizable.get(w.name, False))

        # Weapon variant unlock ints (one per variant).
        for w in GAME_DATA.weapon_types:
            for v in w.variants:
                write_i32(fields, v.field, 1 if self.unlocked_weapons.get(v.name, False) else 0)

        return fields

    def save_to(self, dir_: Path) -> None:
        """Instance convenience wrapper around ParsableClass.save."""
        self.save(dir_)
