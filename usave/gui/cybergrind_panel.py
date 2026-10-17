"""Cybergrind panel — wave/kills/style/time edits for the current difficulty.

Ports `update_cybergrind()` from `app.rs` in the Rust project.

Layout:
  Cybergrind
  ---------------------------------------------------------------------------
  Wave:    [text edit]   (per current difficulty)
  Kills:   [text edit]
  Style:   [text edit]
  Time (s): [text edit]
  [Create file] [Delete file]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..save_classes import CybergrindData

if TYPE_CHECKING:
    from .main_window import MainWindow


class CybergrindPanel(QWidget):
    """Top-right panel: Cyber Grind stats for the current difficulty."""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._building = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        box = QGroupBox("Cybergrind")
        box_layout = QVBoxLayout(box)

        # Wave
        row = QHBoxLayout()
        row.addWidget(QLabel("Wave:"))
        self.wave_edit = QLineEdit()
        self.wave_edit.setPlaceholderText("0.0")
        self.wave_edit.textChanged.connect(self._on_field_changed)
        row.addWidget(self.wave_edit, 1)
        box_layout.addLayout(row)

        # Kills
        row = QHBoxLayout()
        row.addWidget(QLabel("Kills:"))
        self.kills_edit = QLineEdit()
        self.kills_edit.setPlaceholderText("0")
        self.kills_edit.textChanged.connect(self._on_field_changed)
        row.addWidget(self.kills_edit, 1)
        box_layout.addLayout(row)

        # Style
        row = QHBoxLayout()
        row.addWidget(QLabel("Style:"))
        self.style_edit = QLineEdit()
        self.style_edit.setPlaceholderText("0")
        self.style_edit.textChanged.connect(self._on_field_changed)
        row.addWidget(self.style_edit, 1)
        box_layout.addLayout(row)

        # Time
        row = QHBoxLayout()
        row.addWidget(QLabel("Time (s):"))
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("0.0")
        self.time_edit.textChanged.connect(self._on_field_changed)
        row.addWidget(self.time_edit, 1)
        box_layout.addLayout(row)

        # File ops
        row = QHBoxLayout()
        self.create_btn = QPushButton("Create file")
        self.create_btn.clicked.connect(self._on_create_file)
        row.addWidget(self.create_btn)

        self.delete_btn = QPushButton("Delete file")
        self.delete_btn.clicked.connect(self._on_delete_file)
        row.addWidget(self.delete_btn)
        box_layout.addLayout(row)

        layout.addWidget(box)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self._building = True
        try:
            classes = self._main.current_classes()
            if classes is None:
                self.setEnabled(False)
                return
            self.setEnabled(True)
            cg = classes.cybergrind
            diff_idx = self._main.current_difficulty()
            if diff_idx < len(cg.waves):
                self.wave_edit.setText(cg.waves[diff_idx])
            if diff_idx < len(cg.kills):
                self.kills_edit.setText(cg.kills[diff_idx])
            if diff_idx < len(cg.style):
                self.style_edit.setText(cg.style[diff_idx])
            if diff_idx < len(cg.times):
                self.time_edit.setText(cg.times[diff_idx])

            self.create_btn.setEnabled(not cg.file_exists)
            self.delete_btn.setEnabled(cg.file_exists)
        finally:
            self._building = False

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_field_changed(self) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        cg = classes.cybergrind
        diff_idx = self._main.current_difficulty()
        if diff_idx >= len(cg.waves):
            return

        # Read & validate
        wave = self.wave_edit.text()
        kills = self.kills_edit.text()
        style = self.style_edit.text()
        time = self.time_edit.text()

        # Validate wave (float or empty)
        wave = self._validate_f32(wave)
        kills = self._validate_u32(kills)
        style = self._validate_u32(style)
        time = self._validate_f32(time)

        # Update model
        cg.waves[diff_idx] = wave
        cg.kills[diff_idx] = kills
        cg.style[diff_idx] = style
        cg.times[diff_idx] = time
        cg.dirty = True
        cg.decoded = True
        self._main.mark_dirty_and_save()

    def _on_create_file(self) -> None:
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.cybergrind.file_exists = True
        classes.cybergrind.dirty = True
        classes.cybergrind.decoded = True
        self._main.mark_dirty_and_save()
        self.refresh()

    def _on_delete_file(self) -> None:
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.cybergrind.file_exists = False
        save_dir = self._main._resolved_save_path()
        if save_dir is not None:
            CybergrindData.delete_from(save_dir)
        self.refresh()

    # ------------------------------------------------------------------
    # Validators (port `validate_f32` / `validate_u32` from `app.rs`)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_f32(value: str) -> str:
        if not value:
            return value
        try:
            float(value)
            return value
        except ValueError:
            # Strip invalid chars, allow one decimal point
            new_value = ""
            encountered_dot = False
            for c in value:
                if c.isdigit():
                    new_value += c
                elif c == "." and not encountered_dot:
                    new_value += "."
                    encountered_dot = True
            try:
                float(new_value)
                return new_value
            except ValueError:
                return ""

    @staticmethod
    def _validate_u32(value: str) -> str:
        if not value:
            return value
        try:
            int(value)
            return value
        except ValueError:
            new_value = "".join(c for c in value if c.isdigit())
            try:
                int(new_value)
                return new_value
            except ValueError:
                return ""
