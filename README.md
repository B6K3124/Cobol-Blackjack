# Blackjack

A blackjack table where the rules are computed by COBOL and the screen is
drawn by PySide6, dressed up like Windows XP Solitaire.

```
+--------------------------------------------------------------+
|  BlackJack                          (Luna blue caption)      |
|  Game  Options  Help                                          |
|                                                              |
|    DEALER                                                    |
|    [TD] [~4C]                          TOTAL 14               |
|                                                              |
|                                                              |
|                 You win $50.00                               |
|    HAND 1                                                    |
|    [3D] [8D]                              TOTAL 11             |
|                                                              |
|         [DEAL] [HIT] [STAND] [DOUBLE]                        |
+--------------------------------------------+------------------+
| Bankroll $475.00 | Running +2  True +0.33   | wsl/cobol      |
+--------------------------------------------+------------------+
| Bankroll  |  Chips  |  Count  |  Session                    |
```

## Requirements

* Python 3.10+ with PySide6 (`pip install PySide6`)
* GnuCOBOL 3.x to build the engine. Either natively, or inside WSL.

## Build and run

```bash
python build.py      # compile cobol/blackjack.cob
python -m blackjack  # play
```

`run.bat` does both in one step on Windows. If no native `cobc` is found,
`build.py` compiles inside WSL and the game launches the engine through
`wsl.exe`.

To verify the engine without opening a window:

```bash
python -m blackjack --check
```

## Layout

```
cobol/blackjack.cob      the game: shoe, shuffle, rules, payouts, statistics
blackjack/engine.py      stdin/stdout bridge, parses the state records
blackjack/xp.py          Luna / Solitaire colours, fonts, 3D edges, stylesheet
blackjack/chrome.py      title bar, push buttons, chips, sunken panels, status bar
blackjack/cards.py       painted card faces and the blue Solitaire back
blackjack/table.py       felt, hand layout, side rail, menus, main window
blackjack/main.py        entry point
build.py                 compiles the COBOL
cobol/build/soak.py      randomised engine test (recomputes every hand total)
cobol/build/layout_check.py  headless geometry audit of the table
cobol/build/render_test.py   saves screenshots of each visual state
cobol/build/pixel_check.py    checks the screenshots use the XP palette
```

## Rules implemented in COBOL

Six decks, reshuffled at the 75% penetration mark. Blackjack pays 3 to 2.
The dealer stands on all 17s and hits on 16, and peeks for blackjack when
the up-card is a ten or an ace. Insurance is offered against an ace and
pays 2 to 1. A hand may be doubled on its first two cards. Money is held
in cents throughout. A hi-lo running count and the decks remaining are
reported so the side rail can show them.

Statistics persist between sessions in `cobol/BLACKJACK.DAT`, written when
the engine exits. The file is a single 44 character line: four six digit
counters (wins, pushes, losses, rounds), then a sign and nine digits for the
net, then a sign and nine digits for the best bankroll. Anything else in the
file is rejected and the counters start from zero, so a damaged file can
never put rubbish on the scoreboard.

## Controls

| Key          | Action        |
| ------------ | ------------- |
| `Space`      | Deal / next   |
| `H`          | Hit           |
| `S`          | Stand         |
| `D`          | Double        |
| `I`          | Take insurance|
| `N`          | Decline       |
| `Ctrl+N`     | New game      |

Click a chip to choose the bet.

## The engine protocol

The engine is a plain line filter. It prints `READY`, then reads one command
per line and answers with a block of records terminated by `END`.

```
STATE <phase>
MONEY <bankroll> <bet> <roundNet> <cumulativeNet> <result>
RC <runningCount> <trueCount> <decksLeft>
HANDS <handCount> <activeHand>
HAND <index> <role> <status> <total> <soft> <result> <bet> <paid> <ncards> <card>...
FLAGS <doubleOK> <insuranceTaken>
STATS <wins> <pushes> <losses> <rounds> <net> <best>
NOTE <message>
END
```

Commands: `BET <dollars>`, `DEAL`, `HIT`, `STAND`, `DOUBLE`,
`INSURE`, `NOINSURE`, `INFO`, `QUIT`.

Card tokens are a rank (`A23456789TJQK`) plus a suit (`HDCS`). The dealer's
hole card is written `~` first, for example `~4C`. All numbers are
fixed-width so the front end can parse without locale handling.

Hand 1 is always the dealer; the player's hand follows, numbered two. Both
hands report an active status while the player decides, so a client that
wants the hand it is playing must ignore the dealer. GnuCOBOL gives no
way to tell an empty input line from the end of the pipe, so blank lines are
ignored and a run of them ends the session; end of input still stops the
engine straight away.

## Notes for anyone hacking on the COBOL

* `FUNCTION RANDOM` returned a constant in this GnuCOBOL build, so the shoe
  is shuffled with a Park-Miller generator in `PROC-NEXT-RANDOM`.
* GnuCOBOL rejects `ACCEPT ... AT END`, and it cannot open standard input
  as a `LINE SEQUENTIAL` file either, so blank lines are counted and a run
  of them ends the session.
* Every `PERFORM PROC-DRAW` sets `WS-DEAL-TARGET` first. The draw uses that
  field and nothing else, and `PROC-DRAW` refuses a target outside the
  current hand so a mistake can never write past the eleven card table.
* Numeric records are built by moving to numeric `DISPLAY` scratch fields
  and displaying those. `STRING` silently drops values that start with a
  space and must never be used with the same field as source and target.

## Tests

All of these run from the project root and need no display.

```
python build.py --check                  engine starts and answers INFO
wsl -d Ubuntu-22.04 -- bash -lc "cd '/mnt/c/.../cobol' && python3 build/soak.py 250"
python cobol/build/edge_cases.py         adversarial suite, 346 checks
python cobol/build/stats_check.py        counters survive a restart
python cobol/build/layout_check.py       widget geometry and hand layout
python cobol/build/render_test.py        headless screenshots
python cobol/build/pixel_check.py        colour probes on those screenshots
```

`edge_cases.py` is the one that earns its keep: it covers nonsense bets,
commands in the wrong phase, junk input, bankruptcy, shoe exhaustion,
double and insurance guards, money conservation on every settled round,
that `HIT` deals to the player rather than the dealer, corrupt statistics
files, standard input closing mid round, and the record parser. A check that
a random shoe cannot reach in a reasonable number of rounds is reported as
not exercised rather than quietly passing.