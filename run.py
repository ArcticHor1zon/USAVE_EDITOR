"""Entry point for the ULTRAKILL Save Editor.

Usage:
    python run.py              # launch the GUI
    python run.py --debug      # launch with verbose console logging
"""

from __future__ import annotations

import sys

from usave.gui import MainWindow


def main() -> int:
    debug = "--debug" in sys.argv

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    if debug:
        print("=" * 60)
        print("  ULTRAKILL Save Editor - Debug Mode")
        print("=" * 60)

    app = QApplication(sys.argv)
    app.setApplicationName("ULTRAKILL Save Editor")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
