"""Main window for the ULTRAKILL save editor.

A QMainWindow with:
  - a top bar (path edit, auto-detect, slot combo, load button, difficulty combo)
  - a horizontal splitter:
      * left:  levels tree (Act > Layer > Level)
      * right: cybergrind panel + general panel (stacked vertically)
  - a status bar footer showing the current task ("Nothing to do" when idle)

Auto-saves on every change (matching the original egui behavior, which
saved every frame where input was detected). Edits to a save file that
already exists (created by the game or by clicking "Create file") are
written in place immediately. Edits to a file that does NOT exist are
held in memory only — the user must click "Create file" to persist them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..data.schema import GAME_DATA, DifficultyDef
from ..save_classes import LevelData
from ..save_manager import Classes
from ..save_path import detect_save_path, resolve_save_path
from .cybergrind_panel import CybergrindPanel
from .general_panel import GeneralPanel
from .levels_panel import LevelsPanel
from .top_bar import TopBar


_WINDOW_TITLE = "ULTRAKILL Save Editor"
_IDLE_STATUS = "Nothing to do"
_STATUS_TIMEOUT_MS = 4000  # how long temporary status messages stay visible


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(_WINDOW_TITLE)
        self._load_icon()

        # App state
        self.save_path: Optional[Path] = None
        self.save_slot: int = 1
        self.difficulty: int = 2  # Standard
        self.classes: Optional[Classes] = None

        # Auto-detect on startup
        detected = detect_save_path(self.save_slot)
        if detected is not None:
            self.save_path = detected
            self.classes = Classes.load(self._resolved_save_path())

        # Build UI
        self.top_bar = TopBar(self)
        self.top_bar.set_path(str(self.save_path) if self.save_path else "")
        self.top_bar.set_slot(self.save_slot)
        self.top_bar.set_difficulty(self.difficulty)

        # Wire up top bar signals
        self.top_bar.path_changed.connect(self.on_path_changed)
        self.top_bar.auto_detect_clicked.connect(self.on_auto_detect_clicked)
        self.top_bar.slot_changed.connect(self.on_slot_changed)
        self.top_bar.load_clicked.connect(self.on_load_clicked)
        self.top_bar.difficulty_changed.connect(self.on_difficulty_changed)

        self.levels_panel = LevelsPanel(self)
        self.general_panel = GeneralPanel(self)
        self.cybergrind_panel = CybergrindPanel(self)

        # Layout: top bar on top, splitter below
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        outer.addWidget(self.top_bar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.levels_panel)
        splitter.setStretchFactor(0, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.cybergrind_panel)
        right_layout.addWidget(self.general_panel, 1)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([400, 800])

        outer.addWidget(splitter, 1)
        self.setCentralWidget(central)
        self.resize(1400, 900)

        # Status bar — permanent "Nothing to do" label underneath, with
        # temporary action messages shown via showMessage() on top.
        self._idle_label = QLabel(_IDLE_STATUS)
        self._idle_label.setStyleSheet("padding: 2px 6px; color: #888;")
        self.statusBar().addWidget(self._idle_label, 1)

        # Initial population
        self._refresh_all_panels()

    # ------------------------------------------------------------------
    # Icon
    # ------------------------------------------------------------------

    def _load_icon(self) -> None:
        icon_path = Path(__file__).resolve().parent.parent.parent / "Icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def set_status(self, text: str, timeout: int = _STATUS_TIMEOUT_MS) -> None:
        """Show a temporary status message in the footer.

        After `timeout` milliseconds the message clears and the permanent
        "Nothing to do" label reappears.
        """
        self.statusBar().showMessage(text, timeout)

    # ------------------------------------------------------------------
    # Path / slot / difficulty resolution
    # ------------------------------------------------------------------

    def _resolved_save_path(self) -> Optional[Path]:
        if self.save_path is None:
            return None
        return resolve_save_path(self.save_path, self.save_slot)

    # ------------------------------------------------------------------
    # Top bar callbacks (called by TopBar)
    # ------------------------------------------------------------------

    def on_path_changed(self, path_str: str) -> None:
        path = Path(path_str)
        if path.exists() and path.is_dir():
            self.save_path = path
            self.top_bar.set_load_enabled(True)
            self.set_status(f"Path set: {path}")
        else:
            self.save_path = None
            self.top_bar.set_load_enabled(False)
            self.set_status("Path does not exist")

    def on_auto_detect_clicked(self) -> None:
        self.set_status("Auto-detecting save path...")
        detected = detect_save_path(self.save_slot)
        if detected is None:
            self.set_status("Auto-detect failed")
            QMessageBox.information(
                self,
                "Auto-detect failed",
                f"Could not auto-detect the ULTRAKILL save directory for slot {self.save_slot}.\n\n"
                "Make sure Steam is installed and ULTRAKILL has been run at least once.\n"
                "You can still enter the path manually.",
            )
            return
        self.save_path = detected
        self.top_bar.set_path(str(detected))
        self.top_bar.set_load_enabled(True)
        self.set_status(f"Auto-detected: {detected}")

    def on_slot_changed(self, slot: int) -> None:
        self.save_slot = slot
        self.set_status(f"Switched to slot {slot}")
        # Try to auto-detect the new slot's path
        detected = detect_save_path(slot)
        if detected is not None:
            self.save_path = detected
            self.top_bar.set_path(str(detected))
            self.top_bar.set_load_enabled(True)

    def on_load_clicked(self) -> None:
        save_dir = self._resolved_save_path()
        if save_dir is None:
            QMessageBox.warning(self, "No save path", "Please enter a valid save path first.")
            return
        if not save_dir.exists():
            QMessageBox.warning(
                self, "Path missing", f"Save directory does not exist:\n{save_dir}"
            )
            return
        self.set_status(f"Loading from {save_dir}...")
        self.classes = Classes.load(save_dir)
        self._refresh_all_panels()
        # Count how many files were loaded
        if self.classes is not None:
            n_levels = sum(1 for d in self.classes.levels.values() if d.decoded)
            n_diff = sum(1 for d in self.classes.difficulty.values() if d.decoded)
            parts = []
            if n_levels:
                parts.append(f"{n_levels} levels")
            if n_diff:
                parts.append(f"{n_diff} difficulties")
            if self.classes.general.decoded:
                parts.append("general")
            if self.classes.cybergrind.decoded:
                parts.append("cybergrind")
            if parts:
                self.set_status(f"Loaded: {', '.join(parts)}")
            else:
                self.set_status("Loaded (no save files found)")

    def on_difficulty_changed(self, difficulty: int) -> None:
        self.difficulty = difficulty
        diff_def = GAME_DATA.get_difficulty(difficulty)
        diff_name = diff_def.name if diff_def else str(difficulty)
        self.set_status(f"Difficulty: {diff_name}")
        # The levels panel and cybergrind panel both display per-difficulty
        # data, so refresh them.
        self.levels_panel.refresh()
        self.cybergrind_panel.refresh()

    # ------------------------------------------------------------------
    # Save logic
    # ------------------------------------------------------------------

    def mark_dirty_and_save(self) -> None:
        """Mark general+cybergrind dirty (if loaded), save dirty, clear flags.

        Called by child panels after any user edit. Only writes files that
        already exist (file_exists=True) — does NOT create new files.
        """
        if self.classes is None:
            return
        save_dir = self._resolved_save_path()
        if save_dir is None:
            self.set_status("No save path — changes will not be written")
            return
        self.classes.mark_dirty_if_loaded()
        self.classes.save_dirty(save_dir)
        self.classes.clear_dirty()

    def save_single_level(self, level_id: int) -> None:
        """Immediately save a single level's file (used by Create file button)."""
        if self.classes is None:
            return
        save_dir = self._resolved_save_path()
        if save_dir is None:
            return
        data = self.classes.levels.get(level_id)
        if data is None:
            return
        level = GAME_DATA.get_level(level_id)
        if level is None:
            return
        try:
            data.save_to(level, save_dir)
        except Exception as e:
            QMessageBox.warning(self, "Save failed", f"Could not save lvl{level_id}progress.bepis:\n{e}")

    def delete_single_level(self, level_id: int) -> None:
        """Immediately delete a single level's file (used by Delete file button)."""
        if self.classes is None:
            return
        save_dir = self._resolved_save_path()
        if save_dir is None:
            return
        level = GAME_DATA.get_level(level_id)
        if level is None:
            return
        LevelData.delete_from(level, save_dir)

    # ------------------------------------------------------------------
    # Panel refresh
    # ------------------------------------------------------------------

    def _refresh_all_panels(self) -> None:
        self.levels_panel.refresh()
        self.general_panel.refresh()
        self.cybergrind_panel.refresh()

    # ------------------------------------------------------------------
    # Convenience accessors for child panels
    # ------------------------------------------------------------------

    def current_classes(self) -> Optional[Classes]:
        return self.classes

    def current_difficulty(self) -> int:
        return self.difficulty

    def current_difficulty_def(self) -> DifficultyDef:
        return GAME_DATA.get_difficulty(self.difficulty)
