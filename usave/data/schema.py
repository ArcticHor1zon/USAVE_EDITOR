"""Game data schema and YAML loader.

Loads the YAML files in this directory into typed dataclasses and
provides lookup helpers. This is the single source of truth for
levels, enemies, weapons, difficulties, and unlockables — edit the
YAML files to add new game content without touching Python code.

Mirrors the role of `enums.rs` from the original Rust project, but
data-driven instead of hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

import yaml

_DATA_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LevelDef:
    id: int
    name: str
    secrets: int = 0
    encore: bool = False
    prime_index: Optional[int] = None  # set for prime sanctums
    encore_index: Optional[int] = None  # set for encore levels
    no_challenge: bool = False  # if True, hide the "Challenge done" checkbox

    @property
    def is_prime(self) -> bool:
        return self.prime_index is not None

    @property
    def is_encore(self) -> bool:
        return self.encore or self.encore_index is not None

    @property
    def has_challenge(self) -> bool:
        """Whether this level has a challenge that can be marked done.

        Encore levels never have challenges. Levels flagged with
        `noChallenge: true` in levels.yaml also don't have challenges.
        """
        return not self.is_encore and not self.no_challenge


@dataclass(frozen=True)
class SecretLevelDef:
    """A secret mission attached to a layer (not a prime sanctum)."""

    name: str
    is_prime: bool = False
    is_encore: bool = False


@dataclass(frozen=True)
class LayerDef:
    name: str
    levels: list[LevelDef] = field(default_factory=list)
    secret_level: Optional[SecretLevelDef] = None


@dataclass(frozen=True)
class ActDef:
    name: str
    layers: list[LayerDef] = field(default_factory=list)


@dataclass(frozen=True)
class EnemyDef:
    id: int
    name: str


@dataclass(frozen=True)
class WeaponVariantDef:
    name: str
    field: str  # the field name in generalprogress.bepis


@dataclass(frozen=True)
class WeaponTypeDef:
    name: str
    customization_field: Optional[str]
    variants: list[WeaponVariantDef] = field(default_factory=list)

    @property
    def is_customizable(self) -> bool:
        return self.customization_field is not None


@dataclass(frozen=True)
class UnlockableDef:
    id: int
    name: str


@dataclass(frozen=True)
class DifficultyDef:
    id: int
    name: str


# ---------------------------------------------------------------------------
# Top-level GameData aggregate
# ---------------------------------------------------------------------------


@dataclass
class GameData:
    """All loaded game data, with lookup helpers."""

    acts: list[ActDef] = field(default_factory=list)
    prime_sanctums: list[LevelDef] = field(default_factory=list)
    encore_levels: list[LevelDef] = field(default_factory=list)
    enemies: list[EnemyDef] = field(default_factory=list)
    weapon_types: list[WeaponTypeDef] = field(default_factory=list)
    unlockables: list[UnlockableDef] = field(default_factory=list)
    difficulties: list[DifficultyDef] = field(default_factory=list)

    # Lookup indexes (built by _build_indexes)
    _levels_by_id: dict[int, LevelDef] = field(default_factory=dict)
    _enemies_by_id: dict[int, EnemyDef] = field(default_factory=dict)
    _unlockables_by_id: dict[int, UnlockableDef] = field(default_factory=dict)
    _difficulties_by_id: dict[int, DifficultyDef] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, data_dir: Optional[Path] = None) -> "GameData":
        """Load all YAML files from `data_dir` (defaults to this package)."""
        data_dir = data_dir or _DATA_DIR
        gd = cls()

        levels_doc = _load_yaml(data_dir / "levels.yaml")
        gd.acts = cls._parse_acts(levels_doc.get("acts", []))
        gd.prime_sanctums = cls._parse_prime(levels_doc.get("prime_sanctums", []))
        gd.encore_levels = cls._parse_encore(levels_doc.get("encore_levels", []))

        # Merge prime_index / encore_index into the act LevelDefs so
        # iter_all_levels() doesn't yield duplicates. The ENCORE act's
        # level defs get encore_index; P-1/P-2 are NOT in any act (they
        # live only in prime_sanctums), so they stay as-is.
        encore_index_by_id = {e.id: e.encore_index for e in gd.encore_levels}
        for act in gd.acts:
            for layer in act.layers:
                for i, lev in enumerate(layer.levels):
                    if lev.id in encore_index_by_id:
                        layer.levels[i] = replace(lev, encore_index=encore_index_by_id[lev.id])

        enemies_doc = _load_yaml(data_dir / "enemies.yaml")
        gd.enemies = [EnemyDef(id=e["id"], name=e["name"]) for e in enemies_doc.get("enemies", [])]

        weapons_doc = _load_yaml(data_dir / "weapons.yaml")
        gd.weapon_types = cls._parse_weapon_types(weapons_doc.get("weapon_types", []))

        unlockables_doc = _load_yaml(data_dir / "unlockables.yaml")
        gd.unlockables = [
            UnlockableDef(id=u["id"], name=u["name"])
            for u in unlockables_doc.get("unlockables", [])
        ]

        difficulties_doc = _load_yaml(data_dir / "difficulties.yaml")
        gd.difficulties = [
            DifficultyDef(id=d["id"], name=d["name"])
            for d in difficulties_doc.get("difficulties", [])
        ]

        gd._build_indexes()
        return gd

    @staticmethod
    def _parse_acts(raw) -> list[ActDef]:
        acts: list[ActDef] = []
        for a in raw:
            layers: list[LayerDef] = []
            for l in a.get("layers", []):
                levels = [
                    LevelDef(
                        id=lev["id"],
                        name=lev["name"],
                        secrets=lev.get("secrets", 0),
                        encore=lev.get("encore", False),
                        no_challenge=lev.get("noChallenge", False),
                    )
                    for lev in l.get("levels", [])
                ]
                secret_def = _parse_secret_level(l.get("secret_level"))
                layers.append(LayerDef(name=l["name"], levels=levels, secret_level=secret_def))
            acts.append(ActDef(name=a["name"], layers=layers))
        return acts

    @staticmethod
    def _parse_prime(raw) -> list[LevelDef]:
        return [
            LevelDef(
                id=p["id"],
                name=p["name"],
                secrets=0,
                prime_index=p["prime_index"],
                no_challenge=p.get("noChallenge", False),
            )
            for p in raw
        ]

    @staticmethod
    def _parse_encore(raw) -> list[LevelDef]:
        return [
            LevelDef(
                id=e["id"],
                name=e["name"],
                secrets=0,
                encore=True,
                encore_index=e["encore_index"],
                # Encore levels never have challenges anyway (has_challenge
                # returns False for is_encore), but parse the flag for
                # completeness in case someone sets it.
                no_challenge=e.get("noChallenge", False),
            )
            for e in raw
        ]

    @staticmethod
    def _parse_weapon_types(raw) -> list[WeaponTypeDef]:
        types: list[WeaponTypeDef] = []
        for w in raw:
            variants = [
                WeaponVariantDef(name=v["name"], field=v["field"])
                for v in w.get("variants", [])
            ]
            types.append(
                WeaponTypeDef(
                    name=w["name"],
                    customization_field=w.get("customization_field"),
                    variants=variants,
                )
            )
        return types

    def _build_indexes(self) -> None:
        self._levels_by_id.clear()
        for act in self.acts:
            for layer in act.layers:
                for lev in layer.levels:
                    self._levels_by_id[lev.id] = lev
        for p in self.prime_sanctums:
            self._levels_by_id[p.id] = p
        for e in self.encore_levels:
            self._levels_by_id[e.id] = e

        self._enemies_by_id = {e.id: e for e in self.enemies}
        self._unlockables_by_id = {u.id: u for u in self.unlockables}
        self._difficulties_by_id = {d.id: d for d in self.difficulties}

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_level(self, level_id: int) -> Optional[LevelDef]:
        return self._levels_by_id.get(level_id)

    def get_enemy(self, enemy_id: int) -> Optional[EnemyDef]:
        return self._enemies_by_id.get(enemy_id)

    def get_unlockable(self, unlockable_id: int) -> Optional[UnlockableDef]:
        return self._unlockables_by_id.get(unlockable_id)

    def get_difficulty(self, difficulty_id: int) -> Optional[DifficultyDef]:
        return self._difficulties_by_id.get(difficulty_id)

    def iter_all_levels(self):
        """Iterate over every LevelDef (acts + prime sanctums).

        Encore levels live under the ENCORE act (with their encore_index
        merged in), so they're yielded once via the act iteration. Prime
        sanctums are NOT in any act, so they're yielded separately.
        """
        for act in self.acts:
            for layer in act.layers:
                yield from layer.levels
        yield from self.prime_sanctums

    def iter_regular_levels(self):
        """Iterate over levels that appear in the act/layer tree (not prime)."""
        for act in self.acts:
            for layer in act.layers:
                yield from layer.levels


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"game data file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_secret_level(name: Optional[str]) -> Optional[SecretLevelDef]:
    """Parse a layer's `secret_level` string into a SecretLevelDef.

    The string's prefix tells us what kind of secret level it is:
      - "P-N:" → a Prime Sanctum (tracked by DifficultyData.prime_levels)
      - "ENCORE" → an Encore placeholder (skipped in the secret level UI)
      - anything else → a regular secret mission (tracked by
        GeneralData.secret_missions)
    """
    if name is None:
        return None
    upper = name.upper()
    if upper.startswith("P-"):
        return SecretLevelDef(name=name, is_prime=True, is_encore=False)
    if "ENCORE" in upper:
        return SecretLevelDef(name=name, is_prime=False, is_encore=True)
    return SecretLevelDef(name=name, is_prime=False, is_encore=False)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

# Eagerly load on import so the rest of the codebase can do
# `from usave.data.schema import GAME_DATA` and immediately use it.
GAME_DATA = GameData.load()
