"""Save path detection for ULTRAKILL save files.

On Windows, reads the Steam install path from the registry
(HKLM\\SOFTWARE\\WOW6432Node\\Valve\\Steam InstallPath), then checks
`steamapps\\common\\ULTRAKILL\\Saves\\Slot{N}`.

On non-Windows, or when the registry lookup fails, returns None and the
user must enter the path manually in the GUI.

Ports `detect_save_path()` from `app.rs` in the Rust project.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


STEAM_REGISTRY_KEY = r"SOFTWARE\WOW6432Node\Valve\Steam"
STEAM_REGISTRY_VALUE = "InstallPath"
SAVE_RELATIVE_PATH = r"steamapps\common\ULTRAKILL\Saves"


def detect_save_path(slot: int) -> Optional[Path]:
    """Detect the save path for the given slot (1-5).

    Returns None if the platform is not Windows, the registry key is
    missing, or the slot directory does not exist.
    """
    if sys.platform != "win32":
        return None

    try:
        import winreg
    except ImportError:
        return None

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            STEAM_REGISTRY_KEY,
            0,
            winreg.KEY_READ,
        ) as key:
            install_path_raw, _ = winreg.QueryValueEx(key, STEAM_REGISTRY_VALUE)
    except OSError:
        return None

    install_path = Path(install_path_raw)
    save_dir = install_path / SAVE_RELATIVE_PATH / f"Slot{slot}"
    if save_dir.exists() and save_dir.is_dir():
        return save_dir
    return None


def detect_slot_root() -> Optional[Path]:
    """Detect the Slot-less root Saves directory.

    Useful when the user wants to switch slots in the GUI — we can
    check if `Saves/` exists and list its `Slot*` subdirectories.
    """
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            STEAM_REGISTRY_KEY,
            0,
            winreg.KEY_READ,
        ) as key:
            install_path_raw, _ = winreg.QueryValueEx(key, STEAM_REGISTRY_VALUE)
    except OSError:
        return None
    save_root = Path(install_path_raw) / SAVE_RELATIVE_PATH
    if save_root.exists() and save_root.is_dir():
        return save_root
    return None


def resolve_save_path(base: Path, slot: int) -> Path:
    """Resolve the actual save dir for a given slot.

    If `base` already ends with `Slot{N}`, return it as-is. Otherwise
    append `Slot{N}`. Mirrors `resolved_save_path()` from `app.rs`.
    """
    slot_folder = f"Slot{slot}"
    parts = base.parts
    if parts and parts[-1] == slot_folder:
        return base
    return base / slot_folder
