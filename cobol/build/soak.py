"""Randomised soak test for the COBOL blackjack engine.

Drives the engine over its stdin/stdout protocol and independently
recomputes every hand total from the cards the engine reports, so a wrong
card valuation or a malformed record shows up as a failure.
"""

import random
import subprocess
import sys

ENGINE = "./build/blackjack"
RANKS = "A23456789TJQK"
VALUES = {r: 11 if r == "A" else 10 if r in "TJQK" else int(r) for r in RANKS}


def best_total(codes):
    total = sum(VALUES[c[0]] for c in codes)
    aces = sum(c[0] == "A" for c in codes)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def read_state(proc):
    lines = []
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("engine exited unexpectedly")
        line = line.rstrip("\n")
        if line == "END":
            return lines
        assert line, "engine emitted a blank record"
        lines.append(line)


def send(proc, cmd):
    proc.stdin.write(cmd + "\n")
    proc.stdin.flush()
    return read_state(proc)


def check_hands(blocks, errors):
    for line in blocks:
        f = line.split()
        if f[0] != "HAND":
            continue
        idx, role, status, total, soft, result, bet, paid, ncards = f[1:10]
        cards = f[10:]
        if status == "E":
            continue
        if len(cards) != int(ncards):
            errors.append(f"hand {idx}: ncards={ncards} but {len(cards)} cards")
            continue
        for tok in cards:
            bare = tok[1:] if tok.startswith("~") else tok
            if bare[0] not in RANKS or bare[1:] not in ("H", "D", "C", "S"):
                errors.append(f"hand {idx}: bad card token {tok!r}")
                return
        face_down = [c for c in cards if c.startswith("~")]
        if face_down:
            if role != "D" or len(face_down) != 1:
                errors.append(f"hand {idx}: bad hole card placement {cards}")
            continue
        want = best_total(cards)
        if want != int(total):
            errors.append(f"hand {idx} ({role}): total {total} != {want} {cards}")
        want_soft = "Y" if "A" in cards and want != sum(
            min(VALUES[c[0]], 10) for c in cards
        ) else "N"
        if want_soft != soft and "A" in cards:
            errors.append(f"hand {idx}: soft {soft} inconsistent with {cards}")


def main():
    rounds_wanted = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    rng = random.Random(20261002)
    proc = subprocess.Popen(
        [ENGINE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1
    )
    assert proc.stdout.readline().strip() == "READY"
    state = send(proc, "INFO")

    errors = []
    rounds = 0
    hands_checked = 0
    budget = 40000
    bankroll = int(next(l for l in state if l.startswith("MONEY")).split()[1])

    while rounds < rounds_wanted and budget > 0:
        budget -= 1
        send(proc, "BET 5")
        state = send(proc, "DEAL")
        if next(l for l in state if l.startswith("MONEY")).split()[2] == "0000000000":
            break

        while budget > 0:
            budget -= 1
            check_hands(state, errors)
            phase = next(l for l in state if l.startswith("STATE")).split()[1]
            if phase == "INSURANCE":
                cmd = "INSURE" if rng.random() < 0.5 else "NOINSURE"
            elif phase == "PLAYER":
                flags = next(l for l in state if l.startswith("FLAGS")).split()[1:]
                opts = ["HIT", "STAND"]
                if flags[0] == "Y":
                    opts.append("DOUBLE")
                cmd = rng.choice(opts)
            else:
                break
            state = send(proc, cmd)

        phase = next(l for l in state if l.startswith("STATE")).split()[1]
        if phase != "SETTLE":
            continue
        rounds += 1
        hands_checked += sum(
            1
            for l in state
            if l.split()[:1] == ["HAND"] and l.split()[3] != "E"
        )
        money = next(l for l in state if l.startswith("MONEY")).split()[1:]
        bankroll = int(money[0])
        if bankroll < 0:
            errors.append(f"negative bankroll {bankroll}")
        if money[4] not in ("W", "P", "L", "-"):
            errors.append(f"bad round result flag {money[4]!r}")
        check_hands(state, errors)
        if bankroll < 500:
            send(proc, "BET 1")

    proc.stdin.write("QUIT\n")
    proc.stdin.flush()
    proc.wait(timeout=10)

    stats = next(l for l in state if l.startswith("STATS")).split()[1:]
    print(f"rounds={rounds} hand-checks={hands_checked} final-bankroll={bankroll}")
    print(f"stats W/P/L/rounds/net/best = {stats}")
    if errors:
        print(f"FAIL: {len(errors)} errors")
        for e in errors[:10]:
            print("   ", e)
        sys.exit(1)
    print("PASS: every reported hand total matched its cards")


main()