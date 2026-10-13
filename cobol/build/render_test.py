"""Headless render pass: exercise every visual state once and save a
screenshot of each, so painting regressions show up as images."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from blackjack import xp
from blackjack.engine import Engine
from blackjack.table import GameWindow

OUT = ROOT / "cobol" / "build" / "shots"
saved = []


def shot(window, name):
    OUT.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(OUT / f"{name}.png"))
    saved.append(name)
    print(f"  {name}.png")


def main():
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setStyleSheet(xp.stylesheet())

    engine = Engine()
    window = GameWindow(engine)
    window.resize(1040, 700)
    window.show()
    window.start()
    app.processEvents()

    shot(window, "01-table-idle")

    window.pick_bet(25)
    app.processEvents()
    shot(window, "02-chip-selected")

    got_insurance = got_win = got_loss = False
    for _ in range(250):
        window.send("DEAL")
        app.processEvents()
        if engine.state.phase not in ("PLAYER", "INSURANCE"):
            continue
        if engine.state.phase == "INSURANCE" and not got_insurance:
            got_insurance = True
            shot(window, "05-insurance-prompt")

        guard = 0
        while engine.state.phase in ("PLAYER", "INSURANCE") and guard < 16:
            guard += 1
            if engine.state.phase == "INSURANCE":
                window.send("NOINSURE")
            else:
                hand = engine.state.active_hand
                if hand is None:
                    break
                if engine.state.double_ok and hand.total == 11:
                    window.send("DOUBLE")
                elif hand.total < 12:
                    window.send("HIT")
                else:
                    window.send("STAND")
            app.processEvents()

        if engine.state.phase == "SETTLE":
            if not got_win and engine.state.result == "W":
                got_win = True
                shot(window, "03-hand-won")
            if not got_loss and engine.state.result == "L":
                got_loss = True
                shot(window, "04-hand-lost")
        if got_insurance and got_win and got_loss:
            break

    window.showMaximized()
    app.processEvents()
    shot(window, "07-maximised")

    print(f"rounds={engine.state.stats.rounds} bankroll={engine.state.bankroll}")
    print("insurance=%s win=%s loss=%s"
          % (got_insurance, got_win, got_loss))
    engine.close()
    print(f"headless render pass OK ({len(saved)} shots)")


main()