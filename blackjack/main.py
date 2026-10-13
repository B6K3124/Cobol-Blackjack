"""Entry point for the blackjack table.

    python -m blackjack            start the game
    python -m blackjack --check    build the engine if needed, then exit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):  # allow "python blackjack/main.py"
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from blackjack import xp
from blackjack.chrome import game_icon
from blackjack.engine import Engine, EngineError
from blackjack.table import GameWindow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="COBOL blackjack table")
    parser.add_argument(
        "--distro",
        default="Ubuntu-22.04",
        help="WSL distribution hosting the compiled engine",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the engine can be started, then exit",
    )
    args = parser.parse_args(argv)

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Blackjack")
    app.setOrganizationName("Cobol")
    app.setStyle("Fusion")
    app.setStyleSheet(xp.stylesheet())
    app.setWindowIcon(game_icon(64))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, xp.BTNFACE)
    palette.setColor(QPalette.ColorRole.WindowText, xp.QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.Base, xp.QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, xp.QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.Highlight, xp.HIGHLIGHT)
    palette.setColor(QPalette.ColorRole.HighlightedText, xp.QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipBase, xp.INFO)
    app.setPalette(palette)

    engine = Engine(distro=args.distro)

    if args.check:
        try:
            state = engine.start()
        except EngineError as exc:
            print(f"engine check failed: {exc}", file=sys.stderr)
            return 2
        print(f"engine ok via {engine.argv_label}")
        print(f"phase={state.phase} bankroll={state.bankroll} decks={state.decks_left}")
        engine.close()
        return 0

    window = GameWindow(engine)
    window.show()
    QTimer.singleShot(0, window.start)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())