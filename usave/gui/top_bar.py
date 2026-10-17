"""Top bar widget — path edit, auto-detect, slot combo, load, difficulty combo.

Ports `update_top_bar()` from `app.rs` in the Rust project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ..data.schema import GAME_DATA

if TYPE_CHECKING:
    from .main_window import MainWindow


class TopBar(QWidget):
    """Top bar with save path, slot, difficulty, and load controls."""

    # Signals emitted when the user changes something.
    path_changed = Signal(str)
    auto_detect_clicked = Signal()
    slot_changed = Signal(int)
    load_clicked = Signal()
    difficulty_changed = Signal(int)

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Save path label + edit
        layout.addWidget(QLabel("Save path:"))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("C:\\Program Files (x86)\\Steam\\steamapps\\common\\ULTRAKILL\\Saves\\Slot1")
        self.path_edit.setMinimumWidth(450)
        self.path_edit.textChanged.connect(self._on_path_text_changed)
        layout.addWidget(self.path_edit, 1)

        # Auto-detect button
        self.auto_detect_btn = QPushButton("Auto-detect")
        self.auto_detect_btn.clicked.connect(self._on_auto_detect)
        layout.addWidget(self.auto_detect_btn)

        # Slot combo
        layout.addWidget(QLabel("Save Slot:"))
        self.slot_combo = QComboBox()
        for i in range(1, 6):
            self.slot_combo.addItem(str(i), i)
        self.slot_combo.currentIndexChanged.connect(self._on_slot_index_changed)
        layout.addWidget(self.slot_combo)

        # Load button
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self._on_load)
        layout.addWidget(self.load_btn)

        # Stretch to push difficulty to the right
        layout.addStretch(0)

        # Difficulty label + combo (right-aligned)
        layout.addWidget(QLabel("Difficulty:"))
        self.diff_combo = QComboBox()
        for d in GAME_DATA.difficulties:
            self.diff_combo.addItem(d.name, d.id)
        self.diff_combo.setCurrentIndex(2)  # Standard
        self.diff_combo.currentIndexChanged.connect(self._on_diff_index_changed)
        layout.addWidget(self.diff_combo)

    # ------------------------------------------------------------------
    # Public setters (used by MainWindow)
    # ------------------------------------------------------------------

    def set_path(self, path: str) -> None:
        self.path_edit.blockSignals(True)
        self.path_edit.setText(path)
        self.path_edit.blockSignals(False)
        self.load_btn.setEnabled(bool(path))

    def set_slot(self, slot: int) -> None:
        self.slot_combo.blockSignals(True)
        idx = self.slot_combo.findData(slot)
        if idx >= 0:
            self.slot_combo.setCurrentIndex(idx)
        self.slot_combo.blockSignals(False)

    def set_difficulty(self, difficulty: int) -> None:
        self.diff_combo.blockSignals(True)
        idx = self.diff_combo.findData(difficulty)
        if idx >= 0:
            self.diff_combo.setCurrentIndex(idx)
        self.diff_combo.blockSignals(False)

    def set_load_enabled(self, enabled: bool) -> None:
        self.load_btn.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_path_text_changed(self, text: str) -> None:
        self.load_btn.setEnabled(bool(text.strip()))
        self.path_changed.emit(text)

    def _on_auto_detect(self) -> None:
        self.auto_detect_clicked.emit()

    def _on_slot_index_changed(self, _idx: int) -> None:
        slot = self.slot_combo.currentData()
        self.slot_changed.emit(slot)

    def _on_load(self) -> None:
        self.load_clicked.emit()

    def _on_diff_index_changed(self, _idx: int) -> None:
        diff_id = self.diff_combo.currentData()
        self.difficulty_changed.emit(diff_id)
