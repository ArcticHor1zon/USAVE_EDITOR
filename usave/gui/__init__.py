"""PySide6 GUI for the ULTRAKILL save editor.

Layout:
  MainWindow
  ├── TopBar           (path edit, slot combo, load, difficulty)
  └── QSplitter
      ├── LevelsPanel      (tree: Act > Layer > Level)
      └── right column
          ├── CybergrindPanel
          └── GeneralPanel
"""

from .main_window import MainWindow

__all__ = ["MainWindow"]
