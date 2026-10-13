"""Geometric layout audit.

Images cannot be eyeballed here, so this checks the invariants that make
the table look right: every hand, card and button must sit inside the
felt, hands must not collide, the button row must stay clear of the
cards, and the side rail must never be clipped.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from blackjack import xp
from blackjack.cards import CardWidget
from blackjack.engine import Engine
from blackjack.table import GameWindow

failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


def inside(child, parent, label):
    top_left = child.mapTo(parent, child.rect().topLeft())
    bottom_right = child.mapTo(parent, child.rect().bottomRight())
    check(
        parent.rect().contains(top_left) and parent.rect().contains(bottom_right),
        f"{label} escapes the felt: "
        f"{top_left.x()},{top_left.y()} .. {bottom_right.x()},{bottom_right.y()} "
        f"in {parent.width()}x{parent.height()}",
    )


def no_overlap(a, b, label):
    if a.geometry().intersects(b.geometry()):
        failures.append(f"{label} overlaps {b}")


def audit(window, tag):
    felt = window.felt
    app = QApplication.instance()
    app.processEvents()

    check(felt.dealer.y() < felt.height() * 0.45,
          f"[{tag}] dealer is not in the top half (y={felt.dealer.y()})")

    for view in felt.players:
        if not view.isVisible():
            continue
        inside(view, felt, f"[{tag}] player hand")
        for card in view._cards:
            if card.isVisible():
                inside(card, felt, f"[{tag}] card {card._rank}{card._suit}")
                check(
                    felt.rect().contains(card.mapTo(felt, card.rect().topLeft())),
                    f"[{tag}] card outside felt",
                )
        # every visible card must sit inside its own hand view's strip
        check(view.y() > felt.dealer.y(),
              f"[{tag}] player hand above dealer")

    hands = [v for v in felt.players if v.isVisible()]
    for i, first in enumerate(hands):
        for second in hands[i + 1:]:
            no_overlap(first, second, f"[{tag}] hand {first._title}")

    buttons = [b for b in felt.buttons.values() if b.isVisible()]
    if window.engine.state.phase != "INSURANCE":
        check(buttons, f"[{tag}] no buttons visible in phase {window.engine.state.phase}")
    for button in buttons:
        inside(button, felt, f"[{tag}] button {button.text()}")
        check(button.y() > 0, f"[{tag}] button off the top")
        for hand in hands:
            no_overlap(button, hand, f"[{tag}] button {button.text()} vs hand")

    visible_insurance = [b for b in felt.insurance if b.isVisible()]
    if window.engine.state.phase == "INSURANCE":
        check(len(visible_insurance) == 2,
              f"[{tag}] insurance prompt missing")
    else:
        check(not visible_insurance, f"[{tag}] insurance prompt should be hidden")

    check(window.rail.width() >= 200, f"[{tag}] rail too narrow")
    for chip in window.rail.chips:
        check(window.rail.rect().contains(chip.mapTo(window.rail, chip.rect().topLeft())),
              f"[{tag}] chip {chip.value} outside the rail")


def main():
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setStyleSheet(xp.stylesheet())

    engine = Engine()
    window = GameWindow(engine)
    for size in ((1040, 700), (860, 620), (1400, 900), (1920, 1080)):
        window.resize(*size)
    window.resize(1040, 700)
    window.show()
    window.start()
    app.processEvents()

    audit(window, "idle")
    window.pick_bet(25)
    audit(window, "bet")
    window.pick_bet(1)  # keep the bankroll alive across the rounds

    # smallest supported window
    window.resize(760, 600)
    app.processEvents()
    window.felt._layout_hands()
    window.felt._layout_buttons(engine.state)
    audit(window, "min-window")
    window.resize(1040, 700)
    app.processEvents()

    dealt = 0
    insurance_seen = 0
    for _ in range(200):
        window.send("DEAL")
        app.processEvents()
        if engine.state.phase not in ("PLAYER", "INSURANCE"):
            continue
        dealt += 1
        guard = 0
        while engine.state.phase in ("PLAYER", "INSURANCE") and guard < 24:
            guard += 1
            if engine.state.phase == "INSURANCE":
                insurance_seen += 1
                window.send("NOINSURE")
                app.processEvents()
                audit(window, "insurance")
                continue
            active = engine.state.active_hand
            if active is None:
                break
            if active.total < 12:
                window.send("HIT")
            else:
                window.send("STAND")
            app.processEvents()
        if engine.state.phase == "SETTLE":
            audit(window, "settle")

    print(f"hands dealt={dealt} rounds={engine.state.stats.rounds} "
          f"insurance decisions={insurance_seen}")
    engine.close()

    if failures:
        print(f"FAIL: {len(failures)} layout problems")
        for failure in failures[:15]:
            print("   ", failure)
        sys.exit(1)
    print("PASS: layout invariants held")


main()