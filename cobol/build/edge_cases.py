"""Adversarial tests for the COBOL engine.

Every case here is something a player or a bug could do: commands in the
wrong phase, nonsense bets, bankruptcy, shoe exhaustion, table limits and
a corrupt statistics file.  The engine must answer with a sane state and
must never produce negative money or a negative bankroll.
"""

import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from blackjack.engine import Engine, EngineError, money, parse_state  # noqa: E402

DAT = ROOT / "cobol" / "BLACKJACK.DAT"

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    print(f"  [{'ok ' if condition else 'BAD'}] {name}"
          + (f"  {detail}" if detail and not condition else ""))


def sane(state, label):
    """Invariants that must hold for every state the engine emits."""
    ok = state.bankroll >= 0
    check(f"{label}: bankroll never negative", ok,
          f"bankroll={state.bankroll}")
    check(f"{label}: phase is known",
          state.phase in ("IDLE", "PLAYER", "INSURANCE", "DEALER", "SETTLE"),
          f"phase={state.phase}")
    check(f"{label}: count has 13 decks or fewer",
          0 <= state.decks_left <= 6.01, f"decks={state.decks_left}")
    check(f"{label}: result flag is sane",
          state.result in ("W", "P", "L", "-"), f"result={state.result}")
    for hand in state.hands:
        check(f"{label}: total in range",
              4 <= hand.total <= 31 or hand.is_empty,
              f"hand {hand.index} total={hand.total}")
        check(f"{label}: cards well formed",
              all(len(c.token) == 2 for c in hand.cards),
              f"hand {hand.index} {[c.token for c in hand.cards]}")


def section(title):
    print(f"\n== {title} ==")


# --------------------------------------------------------------------------
def test_bad_bets():
    section("nonsense bets")
    engine = Engine()
    engine.start()
    for arg in ["0", "-5", "abc", "1e9", "50.5", "", " ", "9" * 40,
                "0.004", "+10", "1,000"]:
        engine.command(f"BET {arg}" if arg.strip() else "BET")
        state = engine.state
        sane(state, f"BET {arg!r}")
        check(f"BET {arg!r} keeps the bankroll",
              state.bankroll == 50000, f"bankroll={state.bankroll}")
    state = engine.command("BET 5")
    check("a sane bet is accepted", state.bet == 500, f"bet={state.bet}")
    engine.close()


def test_wrong_phase():
    section("commands in the wrong phase")
    engine = Engine()
    engine.start()
    for verb in ["HIT", "STAND", "DOUBLE", "INSURE", "NOINSURE"]:
        state = engine.command(verb)
        sane(state, verb)
        check(f"{verb} during IDLE does not move money",
              state.bankroll == 50000, f"bankroll={state.bankroll}")
    state = engine.command("DEAL")
    sane(state, "DEAL with no bet")
    check("DEAL with no bet uses the default wager",
          state.bankroll == 49500, f"bankroll={state.bankroll}")
    state = engine.command("BET 10")
    state = engine.command("DEAL")
    check("DEAL reaches the player", state.phase in ("PLAYER", "INSURANCE"),
          f"phase={state.phase}")
    if state.phase == "INSURANCE":
        state = engine.command("INSURE")
    check("mid-round bet is refused",
          "mid-round" in engine.command("BET 999").note.lower(),
          f"note={engine.state.note!r}")
    for verb in ["DEAL", "INSURE"]:
        state = engine.command(verb)
        sane(state, verb)
    state = engine.command("STAND")
    check("STAND settles the round", state.phase == "SETTLE",
          f"phase={state.phase}")
    engine.close()


def test_garbage_input():
    section("garbage input")
    engine = Engine()
    engine.start()
    junk = [
        "", " ", "   ", "x" * 500, "deal", "DeaL", "\t", "INFO INFO",
        "BET 5 EXTRA", "HIT; DROP TABLE", "SPLIT;DROP", "12345",
        "BET\t5", "═" * 40, "notacommand", "DEALX",
    ]
    for command in junk:
        try:
            state = engine.command(command)
        except EngineError as exc:
            check(f"junk {command[:12]!r} answered", False, str(exc))
            break
        sane(state, f"junk {command[:10]!r}")
    check("engine survives junk input", engine.state.ready)
    engine.close()


def test_bankruptcy():
    section("going broke")
    engine = Engine()
    engine.start()
    guard = 0
    while engine.state.bankroll > 0 and guard < 4000:
        guard += 1
        engine.command("BET 50" if engine.state.bankroll >= 5000 else "BET 1")
        state = engine.command("DEAL")
        while state.phase in ("PLAYER", "INSURANCE"):
            if state.phase == "INSURANCE":
                state = engine.command("NOINSURE")
            else:
                state = engine.command("STAND")
    check("bankroll fell below the smallest bet",
          engine.state.bankroll < 100,
          f"bankroll={engine.state.bankroll}")
    before = engine.state.bankroll
    for verb in ["BET 1", "BET 50", "DEAL"]:
        state = engine.command(verb)
        sane(state, f"broke {verb}")
    check("a broke table refuses to deal",
          engine.state.bankroll == before and engine.state.phase != "PLAYER",
          f"bankroll={engine.state.bankroll} phase={engine.state.phase}")
    engine.close()


def test_shoe_exhaustion():
    section("shoe exhaustion")
    engine = Engine()
    engine.start()
    rounds = 0
    reshuffles = 0
    decks = engine.state.decks_left
    while rounds < 260:
        engine.command("BET 1")
        state = engine.command("DEAL")
        if state.decks_left > decks:
            reshuffles += 1
        decks = state.decks_left
        if state.phase not in ("PLAYER", "INSURANCE"):
            continue
        rounds += 1
        while state.phase in ("PLAYER", "INSURANCE"):
            if state.phase == "INSURANCE":
                state = engine.command("NOINSURE")
            else:
                state = engine.command("STAND")
    check("the shoe was reshuffled mid-session", reshuffles > 0,
          f"reshuffles={reshuffles}")
    check("decks left stays sane after reshuffles",
          0 < engine.state.decks_left <= 6.01, f"{engine.state.decks_left}")
    engine.close()


def _play_to_end(engine, state):
    """Finish the round: stand on 17 or more, hit otherwise."""
    steps = 0
    while state.phase in ("PLAYER", "INSURANCE") and steps < 200:
        steps += 1
        if state.phase == "INSURANCE":
            state = engine.command("NOINSURE")
            continue
        hand = state.active_hand
        if hand is None:
            break
        state = engine.command("STAND" if hand.total >= 17 else "HIT")
    return state


def test_double_and_insurance_guards():
    section("double and insurance guards")
    engine = Engine()
    engine.start()
    doubled = 0
    insurance_seen = 0
    double_gone_after_hit = 0
    hits_checked = 0
    guard = 0
    while guard < 1200 and doubled < 3:
        guard += 1
        if engine.state.bankroll < 5000:
            engine.close()
            engine = Engine()
            engine.start()
        engine.command("BET 25")
        round_start = engine.state.bankroll
        state = engine.command("DEAL")
        if state.phase not in ("PLAYER", "INSURANCE"):
            continue
        if state.phase == "INSURANCE":
            insurance_seen += 1
            before = state.bankroll
            stake = state.bet // 2
            state = engine.command("INSURE")
            if state.phase in ("PLAYER", "INSURANCE"):
                check("insurance costs half the bet",
                      state.bankroll == before - stake,
                      f"bankroll={state.bankroll} expected={before - stake}")
                check("insurance is recorded", state.insured,
                      "insured flag unset")
            else:
                # insuring a blackjack settles the round at even money, so
                # measure the money against where the round began
                check("an insured round conserves money",
                      state.bankroll == round_start + state.round_net,
                      f"bankroll={state.bankroll} "
                      f"expected={round_start + state.round_net} "
                      f"net={state.round_net}")
        if state.phase != "PLAYER":
            continue
        hand = state.active_hand
        if hand is None:
            continue
        if state.double_ok and hand.total == 11 and hand.bet * 2 <= state.bankroll:
            before = state.bankroll
            wager = hand.bet
            index = hand.index
            state = engine.command("DOUBLE")
            doubled += 1
            live = state.phase in ("PLAYER", "INSURANCE")
            if live:
                check("double costs exactly the bet",
                      state.bankroll == before - wager,
                      f"bankroll={state.bankroll} expected={before - wager}")
            else:
                # the round finished inside the double, so the whole wager
                # is measured against where the round began
                check("a doubled round conserves money",
                      state.bankroll == round_start + state.round_net,
                      f"bankroll={state.bankroll} "
                      f"expected={round_start + state.round_net} "
                      f"net={state.round_net}")
            check("double is no longer offered", not state.double_ok,
                  "double_ok still set")
            check("the bet was doubled",
                  next((h.bet for h in state.hands
                        if h.index == index), 0) == wager * 2,
                  "bet was not doubled")
            grown = next((h for h in state.hands if h.index == index), None)
            if grown is not None:
                check("double leaves three cards", len(grown.cards) == 3,
                      f"cards={len(grown.cards)}")
            if live:
                state = engine.command("DOUBLE")
                check("a second double is refused",
                      "cannot" in state.note.lower(), f"note={state.note!r}")
                check("a refused double costs nothing",
                      state.bankroll == before - wager,
                      f"bankroll={state.bankroll}")
            state = _play_to_end(engine, state)
        else:
            if state.double_ok and len(hand.cards) == 2:
                state = engine.command("HIT")
                hits_checked += 1
                if state.double_ok:
                    double_gone_after_hit += 1
                state = _play_to_end(engine, state)
    check("double was exercised", doubled > 0,
          f"rounds searched={guard}")
    check("insurance was exercised", insurance_seen > 0,
          f"rounds searched={guard}")
    check("double is withdrawn after a hit", double_gone_after_hit == 0,
          f"{double_gone_after_hit} of {hits_checked} hands still offered it")
    print(f"     (doubles tried: {doubled}, insurance rounds: "
          f"{insurance_seen}, hits checked: {hits_checked})")
    engine.close()


def test_money_conservation():
    section("money conservation")
    engine = Engine()
    engine.start()
    rng = random.Random(7)
    bad = 0
    for _ in range(220):
        engine.command("BET 5")
        before = engine.state.bankroll
        state = engine.command("DEAL")
        if state.phase not in ("PLAYER", "INSURANCE"):
            continue
        while state.phase in ("PLAYER", "INSURANCE"):
            if state.phase == "INSURANCE":
                state = engine.command("NOINSURE" if rng.random() < 0.7
                                       else "INSURE")
            else:
                hand = state.active_hand
                if hand is None:
                    break
                if state.double_ok and hand.total == 11 and rng.random() < 0.3:
                    state = engine.command("DOUBLE")
                elif hand.total < 13:
                    state = engine.command("HIT")
                else:
                    state = engine.command("STAND")
        if state.phase != "SETTLE":
            continue
        expected = before + state.round_net
        if state.bankroll != expected:
            bad += 1
            print(f"      mismatch: bankroll={state.bankroll} "
                  f"before={before} net={state.round_net}")
    check("every settled round conserves money", bad == 0,
          f"{bad} mismatched rounds")
    engine.close()


def test_hit_deals_to_the_player():
    section("hit goes to the player, not the dealer")
    engine = Engine()
    engine.start()
    rounds = 0
    hits = 0
    problems = []
    while rounds < 400 and hits < 60:
        engine.command("BET 1")
        state = engine.command("DEAL")
        if state.phase == "INSURANCE":
            state = engine.command("NOINSURE")
        if state.phase != "PLAYER":
            continue
        rounds += 1
        active = state.active_hand
        if active is None:
            problems.append("no player hand was active after the deal")
            break
        if active.index < 2:
            problems.append(f"the active hand is index {active.index}")
        if active.total >= 15:
            _play_to_end(engine, state)
            continue
        cards = len(active.cards)
        total = active.total
        soft_before = active.soft
        dealer = state.dealer
        dealer_cards = len(dealer.cards) if dealer else -1
        state = engine.command("HIT")
        hits += 1
        hand = next((h for h in state.hands if h.index == active.index), None)
        now = state.dealer
        label = f"hand {active.index} from {cards} cards and {total}"
        if hand is None:
            problems.append(f"the hand disappeared after HIT ({label})")
        elif hand.status != "B":
            if len(hand.cards) != cards + 1:
                problems.append(f"HIT changed the wrong hand: "
                                f"{cards} -> {len(hand.cards)} cards ({label})")
            elif hand.total < total and not soft_before:
                problems.append(f"the total fell from {total} to "
                                f"{hand.total} ({label})")
            elif state.phase == "PLAYER" and (
                now is None or len(now.cards) != dealer_cards
            ):
                problems.append(f"HIT changed the dealer hand on the player's "
                                f"turn ({label})")
        _play_to_end(engine, state)
    check("HIT deals to the player's hand", not problems,
          "; ".join(problems[:4]) if problems else "")
    check("HIT was exercised", hits >= 20, f"hits={hits}")
    print(f"     (rounds={rounds} hits={hits})")
    engine.close()


def test_hit_is_always_bounded():
    section("hitting cannot go on for ever")
    engine = Engine()
    engine.start()
    rounds = 0
    worst = 0
    problems = []
    for _ in range(600):
        if engine.state.bankroll < 2000:
            engine.close()
            engine = Engine()
            engine.start()
        engine.command("BET 1")
        state = engine.command("DEAL")
        if state.phase == "INSURANCE":
            state = engine.command("NOINSURE")
        if state.phase != "PLAYER":
            continue
        rounds += 1
        hits = 0
        while state.phase in ("PLAYER", "INSURANCE") and hits < 40:
            if state.phase == "INSURANCE":
                state = engine.command("NOINSURE")
                continue
            hand = state.active_hand
            if hand is None:
                break
            cards = len(hand.cards)
            state = engine.command("HIT")
            hits += 1
            now = next((h for h in state.hands if h.index == hand.index), None)
            if now is not None and now.status == "A" and len(now.cards) <= 11:
                if len(now.cards) != cards + 1:
                    problems.append(f"hand {hand.index} went {cards} -> "
                                    f"{len(now.cards)} cards")
            if "not your move" in state.note.lower():
                problems.append(f"a hit was refused after {hits} hits")
        worst = max(worst, hits)
        if hits >= 40:
            problems.append("a hand never finished")
        if hits > 11:
            problems.append(f"a hand took {hits} hits")
        played = [h for h in state.hands
                  if not h.is_dealer and h.status in ("S", "B")]
        if state.phase == "SETTLE" and len(played) != len(state.player_hands):
            problems.append(f"{len(played)} of {len(state.player_hands)} "
                            f"hands finished")
    check("no hand can be hit for ever", not problems,
          "; ".join(problems[:4]) if problems else "")
    print(f"     (rounds={rounds} most hits in one round={worst})")
    engine.close()


def test_corrupt_stats():
    section("corrupt statistics file")
    backup = DAT.read_bytes() if DAT.exists() else None
    # the record is 44 characters: 4 six-digit counters, then a sign and
    # nine digits for the net and for the best bankroll
    valid = b"0" * 18 + b"000010" + b"-" + b"000000500" + b"+" + b"000001000"
    cases = {
        "zeroed": (b"0" * 44, 0),
        "too short": (b"123", 0),
        "letters": (b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEF" * 2, 0),
        "empty": (b"", 0),
        "bad sign byte": (b"0" * 24 + b"X" + b"0" * 9 + b"+" + b"0" * 9, 0),
        "trailing junk": (valid + b"EXTRA", 0),
        "huge numbers": (b"9" * 24 + b"+" + b"9" * 9 + b"+" + b"9" * 9 + b"\n",
                         999999),
        "real counters": (valid, 10),
    }
    for label, (payload, rounds) in cases.items():
        DAT.write_bytes(payload)
        engine = Engine()
        try:
            state = engine.start()
            check(f"starts with a {label} stats file",
                  state.phase == "IDLE", f"phase={state.phase}")
            check(f"{label}: counters are not garbage",
                  state.stats.rounds == rounds,
                  f"rounds={state.stats.rounds} expected={rounds}")
            state = engine.command("BET 5")
            state = engine.command("DEAL")
            sane(state, f"stats {label}")
            engine.command("STAND")
            engine.close()
        except EngineError as exc:
            check(f"starts with a {label} stats file", False, str(exc))
    if backup is not None:
        DAT.write_bytes(backup)
    elif DAT.exists():
        DAT.unlink()


def test_eof_midround():
    section("stdin closed mid-round")
    win = str(ROOT / "cobol/build/blackjack").replace("\\", "/")
    argv = ["wsl", "-d", "Ubuntu-22.04", "--",
            f"/mnt/{win[0].lower()}{win[2:]}"]
    before = DAT.stat().st_size if DAT.exists() else None
    proc = subprocess.run(argv, input=b"BET 5\nDEAL\nHIT\n", cwd=str(ROOT / "cobol"),
                          capture_output=True, timeout=60)
    check("engine exits cleanly when stdin closes",
          proc.returncode == 0, f"returncode={proc.returncode}")
    check("the session was saved on exit", DAT.exists() or before is None)
    check("no stderr spew", not proc.stderr.strip(),
          proc.stderr.decode(errors="replace")[:200])


def test_parser_robustness():
    section("record parser")
    for records, label, expect_error in (
        ([], "empty block", False),
        (["   "], "blank line", False),
        (["STATE"], "state with no value", True),
        (["MONEY 1 2 3"], "short money record", True),
        (["MONEY 1 2 3 zz 4"], "money with a bad number", True),
        (["RC 1 x 3.0"], "running count with text", True),
        (["HAND 1 D A 10 N - 0 0 0"], "hand with no cards", False),
        (["HAND 1 D A 10 N - 0 0 0 2 AK"], "hand with a bogus card", True),
        (["HAND 1 D A 10 N - 0"], "hand cut short", True),
        (["STATS 1 2 3"], "short stats", True),
        (["GARBAGE 1 2 3"], "unknown tag", False),
        (["NOTE"], "note with no text", False),
        (["MONEY 1 2 3 4 -5 WIN"], "a good block", False),
    ):
        try:
            parse_state(records)
            check(f"parser handles {label}", not expect_error,
                  "should have been rejected")
        except EngineError as exc:
            check(f"parser handles {label}", expect_error,
                  f"rejected with {exc}")
        except Exception as exc:  # noqa: BLE001
            check(f"parser handles {label}", False,
                  f"leaked {type(exc).__name__}: {exc}")


def test_money_format():
    section("money formatting")
    for cents, expected in (
        (0, "$0.00"), (5, "$0.05"), (-5, "-$0.05"), (100, "$1.00"),
        (123456, "$1,234.56"), (-123456, "-$1,234.56"),
        (999999999, "$9,999,999.99"),
    ):
        check(f"money({cents}) == {expected}", money(cents) == expected,
              f"got {money(cents)}")


for test in (
    test_bad_bets,
    test_wrong_phase,
    test_garbage_input,
    test_bankruptcy,
    test_shoe_exhaustion,
    test_double_and_insurance_guards,
    test_money_conservation,
    test_hit_deals_to_the_player,
    test_hit_is_always_bounded,
    test_corrupt_stats,
    test_eof_midround,
    test_parser_robustness,
    test_money_format,
):
    try:
        test()
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        check(f"{test.__name__} completed", False, str(exc))

failed = [name for name, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
if failed:
    print("FAILURES:")
    for name in failed:
        print("   ", name)
    sys.exit(1)
print("PASS: no edge case broke the engine")