"""Save file data classes for the ULTRAKILL save editor.

Each module mirrors one .NET class found in a `.bepis` save file:
  - level_data.py       -> RankData                          (lvl{N}progress.bepis)
  - difficulty_data.py  -> GameProgressMoneyAndGearDifficulty (difficulty{N}progress.bepis)
  - general_data.py     -> GameProgressMoneyAndGear          (generalprogress.bepis)
  - cybergrind_data.py  -> EndlessProgress                   (endlessprogress.bepis)
"""

from .base import (
    FieldMap,
    LIBRARY_NAME,
    ParsableClass,
    ParsableClassKeyed,
)
from .cybergrind_data import CybergrindData
from .difficulty_data import DifficultyData
from .general_data import GeneralData
from .level_data import LevelData

__all__ = [
    "ParsableClass",
    "ParsableClassKeyed",
    "FieldMap",
    "LIBRARY_NAME",
    "LevelData",
    "DifficultyData",
    "GeneralData",
    "CybergrindData",
]
