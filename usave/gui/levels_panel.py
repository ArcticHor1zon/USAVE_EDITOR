"""Levels panel — QTreeWidget showing Act > Layer > Level hierarchy.

Each level row has inline editors:
  - Rank combo (per difficulty)
  - Prime state combo (for prime sanctums only)
  - Secret checkboxes (one per secret skull)
  - Create file / Delete file buttons

Secret mission state combos are shown for non-prime, non-encore secret
levels (attached to their layer row).

Ports `update_levels()`, `update_single_level()`, and
`update_secret_level()` from `app.rs` in the Rust project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..data.schema import GAME_DATA, ActDef, LayerDef, LevelDef, SecretLevelDef
from ..save_classes.level_data import (
    ALL_RANKS,
    LEVEL_RANK_NONE,
    RANK_LABELS,
)
from ..save_classes.difficulty_data import (
    LOCKABLE_COMPLETED,
    LOCKABLE_LOCKED,
    LOCKABLE_UNLOCKED,
)

if TYPE_CHECKING:
    from .main_window import MainWindow


# Column indices in the tree
_COL_NAME = 0
_COL_RANK = 1
_COL_STATE = 2
_COL_SECRETS = 3
_COL_FILE_OPS = 4


class LevelsPanel(QWidget):
    """Left panel: tree of acts > layers > levels with inline editors."""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self._main = main_window
        self._building = False  # guard against recursive signals during refresh

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QLabel("Levels")
        header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 4px;")
        layout.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["Level", "Rank", "State", "Secrets", "File"])
        self.tree.header().setSectionResizeMode(_COL_NAME, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(_COL_RANK, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(_COL_STATE, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(_COL_SECRETS, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(_COL_FILE_OPS, QHeaderView.ResizeToContents)
        self.tree.setIndentation(20)
        layout.addWidget(self.tree, 1)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild the entire tree from the current Classes state."""
        self._building = True
        try:
            self.tree.clear()
            classes = self._main.current_classes()
            if classes is None:
                return

            for act in GAME_DATA.acts:
                act_item = QTreeWidgetItem([act.name, "", "", "", ""])
                act_item.setFont(_COL_NAME, act_item.font(0))
                f = act_item.font(_COL_NAME)
                f.setBold(True)
                act_item.setFont(_COL_NAME, f)
                self.tree.addTopLevelItem(act_item)

                for layer in act.layers:
                    if not layer.levels and layer.secret_level is None:
                        continue
                    layer_item = QTreeWidgetItem([layer.name, "", "", "", ""])
                    f = layer_item.font(_COL_NAME)
                    f.setBold(True)
                    layer_item.setFont(_COL_NAME, f)
                    act_item.addChild(layer_item)

                    # Regular levels (skip prime/encore — they get their own sections)
                    regular_levels = [lev for lev in layer.levels if not lev.is_prime]
                    for level in regular_levels:
                        self._add_level_row(layer_item, level)

                    # Secret level combo (if non-prime, non-encore)
                    if layer.secret_level is not None:
                        sl = layer.secret_level
                        if not sl.is_prime and not sl.is_encore:
                            self._add_secret_level_row(layer_item, sl)

                act_item.setExpanded(True)
                for i in range(act_item.childCount()):
                    act_item.child(i).setExpanded(True)

            # PRIME SANCTUMS section
            prime_levels = [lev for lev in GAME_DATA.prime_sanctums]
            if prime_levels:
                prime_item = QTreeWidgetItem(["PRIME SANCTUMS", "", "", "", ""])
                f = prime_item.font(_COL_NAME)
                f.setBold(True)
                prime_item.setFont(_COL_NAME, f)
                self.tree.addTopLevelItem(prime_item)
                for level in prime_levels:
                    self._add_level_row(prime_item, level)
                prime_item.setExpanded(True)
                for i in range(prime_item.childCount()):
                    prime_item.child(i).setExpanded(True)

        finally:
            self._building = False

    # ------------------------------------------------------------------
    # Row builders
    # ------------------------------------------------------------------

    def _add_level_row(self, parent: QTreeWidgetItem, level: LevelDef) -> None:
        classes = self._main.current_classes()
        if classes is None:
            return
        data = classes.levels.get(level.id)
        if data is None:
            return

        item = QTreeWidgetItem([level.name, "", "", "", ""])
        item.setData(_COL_NAME, Qt.UserRole, level.id)
        parent.addChild(item)

        # Rank combo (per-difficulty)
        diff_idx = self._main.current_difficulty()
        if data.ranks and diff_idx < len(data.ranks):
            current_rank = data.ranks[diff_idx]
        else:
            current_rank = LEVEL_RANK_NONE
        rank_combo = QComboBox()
        for r in ALL_RANKS:
            rank_combo.addItem(RANK_LABELS[r], r)
        rank_combo.setCurrentIndex(ALL_RANKS.index(current_rank) if current_rank in ALL_RANKS else 0)
        rank_combo.currentIndexChanged.connect(
            lambda _i, lid=level.id: self._on_rank_changed(lid)
        )
        self.tree.setItemWidget(item, _COL_RANK, rank_combo)

        # Prime state combo (for prime sanctums only)
        if level.is_prime:
            diff_data = classes.difficulty.get(self._main.current_difficulty())
            if diff_data is not None and level.prime_index is not None:
                if level.prime_index < len(diff_data.prime_levels):
                    current_state = diff_data.prime_levels[level.prime_index]
                else:
                    current_state = LOCKABLE_LOCKED
            else:
                current_state = LOCKABLE_LOCKED
            state_combo = QComboBox()
            state_combo.addItem("Locked", LOCKABLE_LOCKED)
            state_combo.addItem("Unlocked", LOCKABLE_UNLOCKED)
            state_combo.addItem("Completed", LOCKABLE_COMPLETED)
            state_combo.setCurrentIndex(
                [LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED].index(current_state)
                if current_state in (LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED)
                else 0
            )
            state_combo.currentIndexChanged.connect(
                lambda _i, lid=level.id: self._on_prime_state_changed(lid)
            )
            self.tree.setItemWidget(item, _COL_STATE, state_combo)

        # Secret checkboxes
        if data.secrets_found:
            secrets_widget = QWidget()
            secrets_layout = QHBoxLayout(secrets_widget)
            secrets_layout.setContentsMargins(2, 0, 2, 0)
            secrets_layout.setSpacing(4)
            for i, found in enumerate(data.secrets_found):
                cb = QCheckBox()
                cb.setChecked(found)
                cb.stateChanged.connect(
                    lambda _s, lid=level.id, idx=i: self._on_secret_toggled(lid, idx)
                )
                secrets_layout.addWidget(cb)
            self.tree.setItemWidget(item, _COL_SECRETS, secrets_widget)

        # File ops buttons
        file_widget = QWidget()
        file_layout = QHBoxLayout(file_widget)
        file_layout.setContentsMargins(2, 0, 2, 0)
        file_layout.setSpacing(4)

        create_btn = QPushButton("Create")
        create_btn.setEnabled(not data.file_exists)
        create_btn.clicked.connect(
            lambda _checked=False, lid=level.id: self._on_create_file(lid)
        )
        file_layout.addWidget(create_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setEnabled(data.file_exists)
        delete_btn.clicked.connect(
            lambda _checked=False, lid=level.id: self._on_delete_file(lid)
        )
        file_layout.addWidget(delete_btn)
        self.tree.setItemWidget(item, _COL_FILE_OPS, file_widget)

    def _add_secret_level_row(self, parent: QTreeWidgetItem, sl: SecretLevelDef) -> None:
        classes = self._main.current_classes()
        if classes is None:
            return
        current_state = classes.general.secret_missions.get(sl.name, LOCKABLE_LOCKED)

        item = QTreeWidgetItem([sl.name, "", "", "", ""])
        parent.addChild(item)

        state_combo = QComboBox()
        state_combo.addItem("Locked", LOCKABLE_LOCKED)
        state_combo.addItem("Unlocked", LOCKABLE_UNLOCKED)
        state_combo.addItem("Completed", LOCKABLE_COMPLETED)
        state_combo.setCurrentIndex(
            [LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED].index(current_state)
            if current_state in (LOCKABLE_LOCKED, LOCKABLE_UNLOCKED, LOCKABLE_COMPLETED)
            else 0
        )
        state_combo.currentIndexChanged.connect(
            lambda _i, name=sl.name: self._on_secret_level_state_changed(name)
        )
        self.tree.setItemWidget(item, _COL_STATE, state_combo)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_rank_changed(self, level_id: int) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        data = classes.levels.get(level_id)
        if data is None:
            return
        item = self._find_level_item(level_id)
        if item is None:
            return
        rank_combo = self.tree.itemWidget(item, _COL_RANK)
        if not isinstance(rank_combo, QComboBox):
            return
        new_rank = rank_combo.currentData()
        diff_idx = self._main.current_difficulty()
        if diff_idx < len(data.ranks):
            data.ranks[diff_idx] = new_rank
        data.dirty = True
        data.decoded = True
        self._main.mark_dirty_and_save()

    def _on_prime_state_changed(self, level_id: int) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        level = GAME_DATA.get_level(level_id)
        if level is None or level.prime_index is None:
            return
        diff_data = classes.difficulty.get(self._main.current_difficulty())
        if diff_data is None:
            return
        item = self._find_level_item(level_id)
        if item is None:
            return
        state_combo = self.tree.itemWidget(item, _COL_STATE)
        if not isinstance(state_combo, QComboBox):
            return
        new_state = state_combo.currentData()
        if level.prime_index < len(diff_data.prime_levels):
            diff_data.prime_levels[level.prime_index] = new_state
        diff_data.file_exists = True
        diff_data.dirty = True
        diff_data.decoded = True
        self._main.mark_dirty_and_save()

    def _on_secret_toggled(self, level_id: int, secret_idx: int) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        data = classes.levels.get(level_id)
        if data is None or secret_idx >= len(data.secrets_found):
            return
        item = self._find_level_item(level_id)
        if item is None:
            return
        secrets_widget = self.tree.itemWidget(item, _COL_SECRETS)
        if secrets_widget is None:
            return
        cb = secrets_widget.layout().itemAt(secret_idx).widget()
        if not isinstance(cb, QCheckBox):
            return
        data.secrets_found[secret_idx] = cb.isChecked()
        data.dirty = True
        data.decoded = True
        self._main.mark_dirty_and_save()

    def _on_secret_level_state_changed(self, name: str) -> None:
        if self._building:
            return
        classes = self._main.current_classes()
        if classes is None:
            return
        # Find the combo by walking the tree
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                layer_item = top.child(j)
                for k in range(layer_item.childCount()):
                    item = layer_item.child(k)
                    if item.text(_COL_NAME) == name:
                        state_combo = self.tree.itemWidget(item, _COL_STATE)
                        if isinstance(state_combo, QComboBox):
                            classes.general.secret_missions[name] = state_combo.currentData()
                            classes.general.dirty = True
                            classes.general.decoded = True
                            self._main.mark_dirty_and_save()
                        return

    def _on_create_file(self, level_id: int) -> None:
        classes = self._main.current_classes()
        if classes is None:
            return
        data = classes.levels.get(level_id)
        if data is None:
            return
        data.file_exists = True
        data.dirty = True
        data.decoded = True
        self._main.save_single_level(level_id)
        self.refresh()

    def _on_delete_file(self, level_id: int) -> None:
        classes = self._main.current_classes()
        if classes is None:
            return
        data = classes.levels.get(level_id)
        if data is None:
            return
        data.file_exists = False
        self._main.delete_single_level(level_id)
        self.refresh()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_level_item(self, level_id: int) -> Optional[QTreeWidgetItem]:
        """Find the tree item for a given level id by recursive walk.

        Handles both 3-level structure (Act > Layer > Level) and 2-level
        structure (PRIME SANCTUMS > Level).
        """
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            found = self._find_level_item_recursive(top, level_id)
            if found is not None:
                return found
        return None

    def _find_level_item_recursive(
        self, item: QTreeWidgetItem, level_id: int
    ) -> Optional[QTreeWidgetItem]:
        # Check this item itself (handles prime sanctums which are
        # direct children of the PRIME SANCTUMS top-level item).
        if item.data(_COL_NAME, Qt.UserRole) == level_id:
            return item
        # Recurse into children
        for i in range(item.childCount()):
            found = self._find_level_item_recursive(item.child(i), level_id)
            if found is not None:
                return found
        return None
