"""General panel — money, intro/tutorial/clash, weapons, enemies, unlockables.

Ports `update_general()` from `app.rs` in the Rust project.

Layout:
  Money:       [text edit]
  Intro seen:  [checkbox]
  Tutorial beat: [checkbox]
  Clash mode:  [checkbox]
  > Unlockables (collapsible)
      Florp Found:        [checkbox]
      KITR Found:         [checkbox]
  > Weapons (collapsible)
      > Revolvers
          Customizable:   [checkbox]
          Piercer Unlocked: [checkbox]
          ...
      > Shotguns
          ...
  > Enemies (collapsible)
      Cerberus:           [combo: Undiscovered/Partial/Full]
      ...
  [Create file] [Delete file]

When the user edits any field:
  - If generalprogress.bepis already exists (created by the game or by
    clicking "Create file"), the change is written to disk immediately
    — no need to click "Delete file" then "Create file" again.
  - If the file does NOT exist, the change is held in memory only.
    Click "Create file" to persist it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..data.schema import GAME_DATA
from ..save_classes.difficulty_data import (
    LOCKABLE_COMPLETED,
    LOCKABLE_LOCKED,
    LOCKABLE_UNLOCKED,
    LOCKABLE_LABELS,
)

if TYPE_CHECKING:
    from .main_window import MainWindow


class GeneralPanel(QWidget):
    """Right-side panel: general save data (money, weapons, enemies, etc.)."""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._building = False

        # Outer scroll area so the panel works at small window sizes.
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer_layout.addWidget(scroll, 1)

        inner = QWidget()
        scroll.setWidget(inner)
        self.inner_layout = QVBoxLayout(inner)
        self.inner_layout.setContentsMargins(6, 6, 6, 6)
        self.inner_layout.setSpacing(6)

        self._build_static_section()
        self._build_unlockables_section()
        self._build_weapons_section()
        self._build_enemies_section()
        self._build_file_ops_section()
        self.inner_layout.addStretch(1)

    # ------------------------------------------------------------------
    # Section builders (called once at construction)
    # ------------------------------------------------------------------

    def _build_static_section(self) -> None:
        box = QGroupBox("General data")
        layout = QVBoxLayout(box)

        # Money
        row = QHBoxLayout()
        row.addWidget(QLabel("Money:"))
        self.money_edit = QLineEdit()
        self.money_edit.setPlaceholderText("0")
        self.money_edit.textChanged.connect(self._on_money_changed)
        row.addWidget(self.money_edit, 1)
        layout.addLayout(row)

        # Checkboxes
        self.intro_seen_cb = QCheckBox("Intro seen")
        self.intro_seen_cb.toggled.connect(self._on_intro_toggled)
        layout.addWidget(self.intro_seen_cb)

        self.tutorial_beat_cb = QCheckBox("Tutorial beat")
        self.tutorial_beat_cb.toggled.connect(self._on_tutorial_toggled)
        layout.addWidget(self.tutorial_beat_cb)

        self.clash_mode_cb = QCheckBox("Clash mode unlocked")
        self.clash_mode_cb.toggled.connect(self._on_clash_toggled)
        layout.addWidget(self.clash_mode_cb)

        self.inner_layout.addWidget(box)

    def _build_unlockables_section(self) -> None:
        box = QGroupBox("Unlockables")
        box.setCheckable(True)
        box.setChecked(False)
        layout = QVBoxLayout(box)

        for u in GAME_DATA.unlockables:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{u.name} Found:"))
            row.addStretch(1)
            cb = QCheckBox()
            cb.setProperty("unlockable_name", u.name)
            cb.toggled.connect(
                lambda checked, name=u.name: self._on_unlockable_toggled(name, checked)
            )
            row.addWidget(cb)
            layout.addLayout(row)

        self.inner_layout.addWidget(box)

    def _build_weapons_section(self) -> None:
        box = QGroupBox("Weapons")
        box.setCheckable(True)
        box.setChecked(False)
        layout = QVBoxLayout(box)

        for w in GAME_DATA.weapon_types:
            weapon_box = QGroupBox(f"{w.name}s")
            weapon_box.setCheckable(True)
            weapon_box.setChecked(False)
            weapon_layout = QVBoxLayout(weapon_box)

            if w.is_customizable:
                row = QHBoxLayout()
                row.addWidget(QLabel("Customizable:"))
                row.addStretch(1)
                cb = QCheckBox()
                cb.setProperty("weapon_type_name", w.name)
                cb.toggled.connect(
                    lambda checked, name=w.name: self._on_customizable_toggled(name, checked)
                )
                row.addWidget(cb)
                weapon_layout.addLayout(row)

            for v in w.variants:
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{v.name} Unlocked:"))
                row.addStretch(1)
                cb = QCheckBox()
                cb.setProperty("variant_name", v.name)
                cb.toggled.connect(
                    lambda checked, name=v.name: self._on_variant_toggled(name, checked)
                )
                row.addWidget(cb)
                weapon_layout.addLayout(row)

            layout.addWidget(weapon_box)

        self.inner_layout.addWidget(box)

    def _build_enemies_section(self) -> None:
        box = QGroupBox("Enemies")
        box.setCheckable(True)
        box.setChecked(False)
        layout = QVBoxLayout(box)

        for e in GAME_DATA.enemies:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{e.name}:"))
            row.addStretch(1)
            combo = QComboBox()
            combo.addItem("Undiscovered", LOCKABLE_LOCKED)
            combo.addItem("Partially Discovered", LOCKABLE_UNLOCKED)
            combo.addItem("Fully Discovered", LOCKABLE_COMPLETED)
            combo.setProperty("enemy_name", e.name)
            combo.currentIndexChanged.connect(
                lambda _i, name=e.name: self._on_enemy_state_changed(name)
            )
            row.addWidget(combo)
            layout.addLayout(row)

        self.inner_layout.addWidget(box)

    def _build_file_ops_section(self) -> None:
        row = QHBoxLayout()
        self.create_btn = QPushButton("Create file")
        self.create_btn.clicked.connect(self._on_create_file)
        row.addWidget(self.create_btn)

        self.delete_btn = QPushButton("Delete file")
        self.delete_btn.clicked.connect(self._on_delete_file)
        row.addWidget(self.delete_btn)

        self.inner_layout.addLayout(row)

    # ------------------------------------------------------------------
    # Refresh (called when Classes is loaded/reloaded)
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self._building = True
        try:
            classes = self._main.current_classes()
            if classes is None:
                self.setEnabled(False)
                return
            self.setEnabled(True)
            g = classes.general

            self.money_edit.setText(g.money)
            self.intro_seen_cb.setChecked(g.intro_seen)
            self.tutorial_beat_cb.setChecked(g.tutorial_beat)
            self.clash_mode_cb.setChecked(g.clash_mode_unlocked)

            # Unlockables
            self._for_each_checkbox_in_group("Unlockables", "unlockable_name", lambda cb, name:
                cb.setChecked(g.unlockables_found.get(name, False))
            )

            # Weapons
            self._for_each_checkbox_in_group("Weapons", "weapon_type_name", lambda cb, name:
                cb.setChecked(g.weapons_customizable.get(name, False))
            )
            self._for_each_checkbox_in_group("Weapons", "variant_name", lambda cb, name:
                cb.setChecked(g.unlocked_weapons.get(name, False))
            )

            # Enemies
            self._for_each_combo_in_group("Enemies", "enemy_name", lambda combo, name:
                combo.setCurrentIndex(
                    [LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED].index(
                        g.enemies_discovered.get(name, LOCKABLE_LOCKED)
                    )
                    if g.enemies_discovered.get(name, LOCKABLE_LOCKED) in
                       (LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED)
                    else 0
                )
            )

            # File ops
            self.create_btn.setEnabled(not g.file_exists)
            self.delete_btn.setEnabled(g.file_exists)
        finally:
            self._building = False

    def _for_each_checkbox_in_group(self, group_title: str, prop_name: str, fn) -> None:
        """Iterate over checkboxes inside a top-level QGroupBox and apply `fn`."""
        for i in range(self.inner_layout.count()):
            item = self.inner_layout.itemAt(i)
            w = item.widget() if item else None
            if not isinstance(w, QGroupBox) or w.title() != group_title:
                continue
            self._walk_checkboxes(w, prop_name, fn)

    def _walk_checkboxes(self, parent: QWidget, prop_name: str, fn) -> None:
        """Recursively walk a widget's children for checkboxes with `prop_name`."""
        for child in parent.findChildren(QCheckBox):
            name = child.property(prop_name)
            if name is not None:
                fn(child, name)

    def _for_each_combo_in_group(self, group_title: str, prop_name: str, fn) -> None:
        for i in range(self.inner_layout.count()):
            item = self.inner_layout.itemAt(i)
            w = item.widget() if item else None
            if not isinstance(w, QGroupBox) or w.title() != group_title:
                continue
            for child in w.findChildren(QComboBox):
                name = child.property(prop_name)
                if name is not None:
                    fn(child, name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _persist_or_hold(self, status_msg: str) -> None:
        """Common logic after a general-field edit.

        If generalprogress.bepis already exists, mark dirty+decoded and
        save in place. Otherwise, hold the change in memory only.
        """
        classes = self._main.current_classes()
        if classes is None:
            return
        if classes.general.file_exists:
            classes.general.dirty = True
            classes.general.decoded = True
            self._main.mark_dirty_and_save()
            self._main.set_status(status_msg)
        else:
            self._main.set_status(
                f"{status_msg} (in memory — click Create file to save)"
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_money_changed(self, text: str) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        # Allow only digits
        cleaned = "".join(c for c in text if c.isdigit())
        if cleaned != text:
            self.money_edit.blockSignals(True)
            self.money_edit.setText(cleaned)
            self.money_edit.blockSignals(False)
        classes.general.money = cleaned or "0"
        self._persist_or_hold(f"Money set to {cleaned or '0'}")

    def _on_intro_toggled(self, checked: bool) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.general.intro_seen = checked
        self._persist_or_hold(f"Intro seen: {'on' if checked else 'off'}")

    def _on_tutorial_toggled(self, checked: bool) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.general.tutorial_beat = checked
        self._persist_or_hold(f"Tutorial beat: {'on' if checked else 'off'}")

    def _on_clash_toggled(self, checked: bool) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.general.clash_mode_unlocked = checked
        self._persist_or_hold(f"Clash mode: {'on' if checked else 'off'}")

    def _on_unlockable_toggled(self, name: str, checked: bool) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.general.unlockables_found[name] = checked
        self._persist_or_hold(f"{name}: {'found' if checked else 'not found'}")

    def _on_customizable_toggled(self, name: str, checked: bool) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.general.weapons_customizable[name] = checked
        self._persist_or_hold(f"{name} customizable: {'on' if checked else 'off'}")

    def _on_variant_toggled(self, name: str, checked: bool) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.general.unlocked_weapons[name] = checked
        self._persist_or_hold(f"{name}: {'unlocked' if checked else 'locked'}")

    def _on_enemy_state_changed(self, name: str) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        # Find the combo
        for i in range(self.inner_layout.count()):
            item = self.inner_layout.itemAt(i)
            w = item.widget() if item else None
            if not isinstance(w, QGroupBox) or w.title() != "Enemies":
                continue
            for child in w.findChildren(QComboBox):
                if child.property("enemy_name") == name:
                    new_state = child.currentData()
                    classes.general.enemies_discovered[name] = new_state
                    state_label = LOCKABLE_LABELS.get(new_state, str(new_state))
                    self._persist_or_hold(f"{name}: {state_label}")
                    return

    def _on_create_file(self) -> None:
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.general.file_exists = True
        classes.general.dirty = True
        classes.general.decoded = True
        self._main.mark_dirty_and_save()
        self.refresh()
        self._main.set_status("Created generalprogress.bepis")

    def _on_delete_file(self) -> None:
        classes = self._main.current_classes()
        if classes is None:
            return
        classes.general.file_exists = False
        # Delete the actual file
        from ..save_classes import GeneralData
        save_dir = self._main._resolved_save_path()
        if save_dir is not None:
            GeneralData.delete_from(save_dir)
        self.refresh()
        self._main.set_status("Deleted generalprogress.bepis")
