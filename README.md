# USAVE_EDITOR (Python)

![Python](https://img.shields.io/badge/python-3.10+-3776ab.svg?style=for-the-badge&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-Qt-41cd52.svg?style=for-the-badge&logo=qt&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![State](https://img.shields.io/badge/state-alpha-%23ff0000?style=for-the-badge&label=state&labelColor=%231a1a1a)

A Python rewrite of a save editor for the game ULTRAKILL. The original was written in Rust with
a custom .NET Binary Format (NRBF) parser; this rewrite is pure Python with
a PySide6 (Qt) GUI and **YAML-driven game data** so new levels/enemies/weapons
can be added without touching code when ULTRAKILL updates.

> [!CAUTION]
> This tool is in alpha and may corrupt your save files. **Always back up
> your `Saves` folder before using it.** You have been warned.

_Based on [ultrakill-save-editor](https://github.com/PyPylia/ultrakill-save-editor/tree/main)
by [PyPylia](https://github.com/PyPylia), via the Rust port by
[ArcticHor1zon](https://github.com/ArcticHor1zon)._

---

## Features

- Load and edit all 4 ULTRAKILL save file types:
  - `generalprogress.bepis` — money, weapons, enemies, unlockables, secret missions
  - `endlessprogress.bepis` — Cyber Grind stats (wave/kills/style/time per difficulty)
  - `lvl{N}progress.bepis` — per-level ranks, secrets, challenge, major assists
  - `difficulty{N}progress.bepis` — current level + Prime Sanctum lock state
- Auto-detects your Steam install path on Windows (reads the registry)
- Supports 5 save slots
- Per-difficulty editing (Harmless / Lenient / Standard / Violent / Brutal)
- Create or delete individual save files
- Auto-saves on every change (matching the original Rust app's behavior)
- All game data (levels, enemies, weapons, difficulties, unlockables) lives
  in **YAML config files** — no code edits needed when ULTRAKILL updates

## Requirements

- Python 3.10 or newer
- Windows (recommended — auto-detect only works on Windows; Linux/Mac users
  can paste the save path manually)
- The Steam version of ULTRAKILL

## Installation

```bash
git clone <this repo>
cd usave-editor-python
pip install -r requirements.txt
```

## Usage

```bash
python run.py
```

Optionally, run with debug logging:

```bash
python run.py --debug
```

The editor opens maximized. The top bar lets you:

1. **Save path** — auto-detected on Windows; edit manually if needed
2. **Save Slot** — pick slot 1–5
3. **Load** — reload all save files from the current path/slot
4. **Difficulty** — pick which difficulty's data to edit (affects ranks,
   Cyber Grind stats, and Prime Sanctum state)

The left panel shows the level tree (Act > Layer > Level). Click a level
to expand it and edit its rank, secrets, challenge, and major assists.
Prime Sanctums (P-1, P-2) live in their own section at the bottom and also
have a "State" combo (Locked / Unlocked / Completed).

The right panel shows:
- **Cybergrind** — best wave / kills / style / time for the current difficulty
- **General data** — money, intro/tutorial/clash state, and collapsible
  sections for Unlockables, Weapons (per type: customizable + variant
  unlocks), and Enemies (discovery state)

## Adding new content when ULTRAKILL updates

This is the main improvement over the Rust original. All game data lives
in YAML files under [`usave/data/`](usave/data/). Edit them with any text
editor — no Python knowledge required.

### Add a new level

Edit [`usave/data/levels.yaml`](usave/data/levels.yaml). Find the layer the
new level belongs to, then add an entry to its `levels:` list:

```yaml
- name: "LAYER 9: TREACHERY"
  levels:
    - { id: 34, name: "9-1: COOL NEW LEVEL", secrets: 5 }   # ← new entry
  secret_level: "P-3: ???"
```

- `id` must be unique across all levels (it's used in the filename
  `lvl34progress.bepis`)
- `secrets` is the number of collectible secret skulls; boss levels
  typically have 0
- Save the file and restart the editor. Done.

### Add a new enemy

Edit [`usave/data/enemies.yaml`](usave/data/enemies.yaml):

```yaml
- { id: 44, name: "Cool New Enemy" }   # ← use the next free id
```

**Important:** do NOT change existing `id` values — they are positional and
the save file's `newEnemiesFound` array depends on the order.

### Add a new weapon variant

Edit [`usave/data/weapons.yaml`](usave/data/weapons.yaml). Find the weapon
type the variant belongs to and add an entry to its `variants:` list:

```yaml
- name: "Revolver"
  customization_field: "revCustomizationUnlocked"
  variants:
    - { name: "Piercer Revolver",       field: "rev0" }
    - { name: "Cool New Revolver",      field: "rev4" }   # ← new entry
```

The `field` is the field name in `generalprogress.bepis`. You can find it by
inspecting a save file with the editor after unlocking the variant in-game,
or by decompiling the game's `Assembly-CSharp.dll`.

### Add a new difficulty

Edit [`usave/data/difficulties.yaml`](usave/data/difficulties.yaml):

```yaml
- { id: 5, name: "ULTRAKILL MUST DIE" }   # ← use the next free id
```

### Add a new unlockable

Edit [`usave/data/unlockables.yaml`](usave/data/unlockables.yaml):

```yaml
- { id: 2, name: "Cool New Unlockable" }   # ← use the next free id
```

## Project structure

```
usave-editor-python/
├── run.py                          # Entry point
├── requirements.txt
├── Icon.ico                        # Window icon (from the original)
├── LICENSE                         # GPLv3 (carried over)
├── usave/
│   ├── nrbf/                       # .NET Binary Format library (port of ms-nrbf)
│   │   ├── primitives.py           # PrimitiveType, Primitive, PrimitiveArray, AdditionalInfo
│   │   ├── reader.py               # NrbfReader (LE binary, 7-bit string, .NET dates)
│   │   ├── writer.py               # NrbfWriter
│   │   ├── records.py              # All NRBF record dataclasses
│   │   └── stream.py               # Stream, Class, Field high-level API
│   ├── data/                       # ← EDIT THESE YAML FILES TO ADD CONTENT
│   │   ├── levels.yaml
│   │   ├── enemies.yaml
│   │   ├── weapons.yaml
│   │   ├── difficulties.yaml
│   │   ├── unlockables.yaml
│   │   └── schema.py               # Loads YAML into typed dataclasses
│   ├── save_classes/               # The 4 .NET class parsers
│   │   ├── base.py                 # ParsableClass, ParsableClassKeyed bases
│   │   ├── level_data.py           # RankData           (lvl{N}progress.bepis)
│   │   ├── difficulty_data.py      # ...Difficulty      (difficulty{N}progress.bepis)
│   │   ├── general_data.py         # GameProgressMoneyAndGear (generalprogress.bepis)
│   │   └── cybergrind_data.py      # EndlessProgress    (endlessprogress.bepis)
│   ├── save_manager.py             # Classes container + load/save orchestration
│   ├── save_path.py                # Windows registry Steam detection
│   └── gui/                        # PySide6 (Qt) GUI
│       ├── main_window.py
│       ├── top_bar.py
│       ├── levels_panel.py
│       ├── general_panel.py
│       └── cybergrind_panel.py
└── tests/                          # pytest smoke tests
    ├── test_nrbf_roundtrip.py
    └── test_save_classes.py
```

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## How it works

ULTRAKILL saves are `.bepis` files containing .NET Binary Format (NRBF)
serialized objects. Each file holds one root class instance (e.g.
`RankData` for level progress) with typed fields (primitives, primitive
arrays, and nested classes).

The `usave/nrbf/` package is a pure-Python port of the Rust `ms-nrbf` crate
from the original project. It implements:

- The 17 NRBF primitive types (Boolean, Byte, Char, Decimal, Double, Int16,
  Int32, Int64, SByte, Single, TimeSpan, DateTime, UInt16, UInt32, UInt64,
  Null, String)
- All record types (SerializationHeader, ClassWithMembersAndTypes,
  ArraySinglePrimitive, BinaryLibrary, MemberReference, ObjectNull,
  MessageEnd, etc.)
- 7-bit-encoded length-prefixed UTF-8 strings (matching
  `System.IO.BinaryReader.ReadString`)
- .NET DateTime / TimeSpan tick encoding

The save classes (`usave/save_classes/`) map between the decoded NRBF
`Class` tree and Python dataclasses. They preserve "original fields" so
that fields the editor doesn't understand are round-tripped byte-identically
on save.

## Issues

If you find any bugs, please open an issue. Include:

- The exact save file that caused the problem (if you can share it)
- The error message or unexpected behavior
- What you did leading up to it

## License

Distributed under GNU GPLv3 license. See [`LICENSE`](LICENSE) for details.
