"""Statistics must survive a restart.

Plays a known number of rounds, exits the engine, starts it again and
checks that the counters came back from BLACKJACK.DAT.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from blackjack.engine import Engine

ROUNDS = 25


def play(engine, rounds):
    played = 0
    while played < rounds:
        engine.command("BET 1")
        state = engine.command("DEAL")
        if state.phase not in ("PLAYER", "INSURANCE"):
            continue
        played += 1
        while state.phase in ("PLAYER", "INSURANCE"):
            if state.phase == "INSURANCE":
                state = engine.command("NOINSURE")
            elif state.active_hand.total < 13:
                state = engine.command("HIT")
            else:
                state = engine.command("STAND")
    return engine.state.stats


engine = Engine()
engine.start()
before = play(engine, ROUNDS)
print(f"session 1: rounds={before.rounds} W/P/L={before.wins}/{before.pushes}"
      f"/{before.losses} net={before.net} best={before.best}")
engine.close()

engine = Engine()
engine.start()
after = engine.state.stats
print(f"session 2: rounds={after.rounds} W/P/L={after.wins}/{after.pushes}"
      f"/{after.losses} net={after.net} best={after.best}")

failures = []
if after.rounds != before.rounds:
    failures.append(f"rounds did not persist: {after.rounds} != {before.rounds}")
if (after.wins, after.pushes, after.losses) != (before.wins, before.pushes, before.losses):
    failures.append("win/push/loss counts did not persist")
if after.net != before.net or after.best != before.best:
    failures.append("net/best did not persist")
engine.close()

path = Path(__file__).resolve().parents[2] / "cobol" / "BLACKJACK.DAT"
print(f"BLACKJACK.DAT = {path.read_text().strip()!r}")

if failures:
    print("FAIL:")
    for failure in failures:
        print("   ", failure)
    sys.exit(1)
print("PASS: statistics survive a restart")