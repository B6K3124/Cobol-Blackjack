"""Bridge between the COBOL blackjack engine and the GUI.

The engine is a plain stdin/stdout filter: one command per line in, one
block of records out terminated by ``END``.  This module owns the child
process, parses the records into dataclasses and hands the GUI a single
``GameState`` per command.

The engine is compiled inside WSL, so on Windows the child is launched
through ``wsl.exe``.  A native Windows binary is preferred when one has
been built, which makes start-up nearly instant.
"""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COBOL_DIR = PROJECT_ROOT / "cobol"
BUILD_DIR = COBOL_DIR / "build"

READY_TIMEOUT = 90.0
COMMAND_TIMEOUT = 15.0


class EngineError(RuntimeError):
    """The engine died or spoke something we cannot understand."""


def to_int(token: str) -> int:
    return int(token)


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def wsl_path(path: Path) -> str:
    """Translate ``C:\\a\\b`` into ``/mnt/c/a/b`` for wsl.exe."""
    text = str(path)
    drive, _, tail = text.partition(":")
    return f"/mnt/{drive.lower()}{tail.replace(os.sep, '/')}"


def _runs_here(path: Path) -> bool:
    """Cheap magic-number check so we never hand a Linux ELF to Windows."""
    try:
        with path.open("rb") as handle:
            magic = handle.read(4)
    except OSError:
        return False
    if os.name == "nt":
        return magic.startswith(b"MZ")
    return magic.startswith(b"\x7fELF") or not magic.startswith(b"MZ")


# --------------------------------------------------------------------------
# records
# --------------------------------------------------------------------------
@dataclass
class Card:
    rank: str
    suit: str
    face_down: bool = False

    @property
    def token(self) -> str:
        return f"{self.rank}{self.suit}"


@dataclass
class Hand:
    index: int
    role: str
    status: str
    total: int
    soft: bool
    result: str
    bet: int
    paid: int
    cards: list[Card] = field(default_factory=list)

    @property
    def is_dealer(self) -> bool:
        return self.role == "D"

    @property
    def is_live(self) -> bool:
        return self.status in ("A", "B", "S")

    @property
    def is_empty(self) -> bool:
        return self.status == "E"

    @property
    def label(self) -> str:
        return "Dealer" if self.is_dealer else f"Hand {self.index - 1}"


@dataclass
class Stats:
    wins: int = 0
    pushes: int = 0
    losses: int = 0
    rounds: int = 0
    net: int = 0
    best: int = 0


@dataclass
class GameState:
    phase: str = "IDLE"
    bankroll: int = 0
    bet: int = 0
    round_net: int = 0
    cumulative_net: int = 0
    result: str = "-"
    running_count: int = 0
    true_count: float = 0.0
    decks_left: float = 0.0
    hands: list[Hand] = field(default_factory=list)
    double_ok: bool = False
    insured: bool = False
    stats: Stats = field(default_factory=Stats)
    note: str = ""
    ready: bool = False

    @property
    def player_hands(self) -> list[Hand]:
        return [h for h in self.hands if not h.is_dealer]

    @property
    def dealer(self) -> Hand | None:
        return next((h for h in self.hands if h.is_dealer), None)

    @property
    def active_hand(self) -> Hand | None:
        """The player hand the engine is waiting on, if there is one.

        The engine keeps the dealer in the first slot and numbers the
        player hand as hand two, so the dealer is skipped here even
        though it also reports an active status while the player is
        deciding.
        """
        active = [h for h in self.hands if not h.is_dealer and h.status == "A"]
        return active[-1] if active else None

    @property
    def can_bet(self) -> bool:
        return self.phase in ("IDLE", "SETTLE")


# --------------------------------------------------------------------------
# engine process
# --------------------------------------------------------------------------
class Engine:
    """Owns the COBOL child process."""

    def __init__(self, distro: str = "Ubuntu-22.04", log=None):
        self.distro = distro
        self.log = log
        self._proc: subprocess.Popen | None = None
        self._lines: queue.Queue = queue.Queue()
        self._reader: threading.Thread | None = None
        self._argv: list[str] = []
        self.state = GameState()

    # -- process management -------------------------------------------------
    @property
    def native_binary(self) -> Path | None:
        """A binary this machine can exec directly, if one was built."""
        for name in ("blackjack.exe", "blackjack"):
            candidate = BUILD_DIR / name
            if candidate.exists() and _runs_here(candidate):
                return candidate
        return None

    def _build_argv(self) -> tuple[list[str], Path]:
        native = self.native_binary
        if native is not None and os.name == "nt":
            return [str(native)], BUILD_DIR
        if not shutil.which("wsl"):
            raise EngineError(
                "cobc is not available on PATH and wsl.exe was not found.\n"
                "Build the engine with:  python build.py"
            )
        return (
            ["wsl", "-d", self.distro, "--", wsl_path(BUILD_DIR / "blackjack")],
            COBOL_DIR,
        )

    @property
    def argv_label(self) -> str:
        """How the engine is being hosted, for the status bar."""
        if not self._argv:
            return "-"
        if self._argv[0].endswith("wsl.exe") or self._argv[0] == "wsl":
            return "wsl/cobol"
        return Path(self._argv[0]).name

    def start(self) -> GameState:
        self.close(quiet=True)
        self._argv, cwd = self._build_argv()
        self._lines = queue.Queue()
        try:
            self._proc = subprocess.Popen(
                self._argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
                cwd=str(cwd),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                if os.name == "nt"
                else 0,
            )
        except OSError as exc:
            raise EngineError(f"could not start the engine: {exc}") from exc

        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

        banner = self._next_line(READY_TIMEOUT)
        if banner != "READY":
            raise EngineError(f"unexpected engine banner: {banner!r}")
        return self.command("INFO")

    def _pump(self) -> None:
        stream = self._proc.stdout if self._proc else None
        if stream is None:
            return
        try:
            while True:
                raw = stream.readline()
                if not raw:
                    break
                self._lines.put(raw.decode("utf-8", "replace").rstrip("\r\n"))
        except (ValueError, OSError):
            pass
        finally:
            self._lines.put(None)

    def _next_line(self, timeout: float) -> str:
        try:
            line = self._lines.get(timeout=timeout)
        except queue.Empty as exc:
            raise EngineError("the engine stopped responding") from exc
        if line is None:
            raise EngineError("the engine exited unexpectedly")
        return line

    def _collect(self) -> list[str]:
        records = []
        while True:
            line = self._next_line(COMMAND_TIMEOUT)
            if line == "END":
                return records
            if line:
                records.append(line)

    def command(self, command: str) -> GameState:
        if self._proc is None or self._proc.poll() is not None:
            raise EngineError("the engine is not running")
        try:
            self._proc.stdin.write(command.encode("ascii", "replace") + b"\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, ValueError) as exc:
            raise EngineError("the engine closed its input") from exc
        self.state = parse_state(self._collect())
        self.state.ready = True
        return self.state

    def restart(self) -> GameState:
        """Fresh bankroll; the engine reloads its statistics from disk."""
        return self.start()

    def close(self, quiet: bool = False) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.write(b"QUIT\n")
                proc.stdin.flush()
                proc.stdin.close()
        except (BrokenPipeError, ValueError, OSError):
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        for stream in (proc.stdout,):
            if stream and not stream.closed:
                stream.close()


# --------------------------------------------------------------------------
# record parsing
# --------------------------------------------------------------------------
def parse_card(token: str) -> Card:
    if len(token) < 2:
        raise EngineError(f"unreadable card {token!r}")
    if token.startswith("~"):
        return Card(token[1], token[2], face_down=True)
    return Card(token[0], token[1])


def parse_state(records: list[str]) -> GameState:
    """Build a state from one protocol block.

    A damaged or truncated record raises EngineError with the offending
    text rather than an IndexError or ValueError, so the caller can report
    the problem instead of the whole application dying on it.
    """

    def need(record: str, fields: list[str], count: int) -> None:
        if len(fields) < count:
            raise EngineError(f"truncated record {record.strip()!r}")

    state = GameState()
    for record in records:
        fields = record.split()
        if not fields:
            continue
        tag = fields[0]
        try:
            if tag == "STATE":
                need(record, fields, 2)
                state.phase = fields[1]
            elif tag == "MONEY":
                need(record, fields, 6)
                state.bankroll = to_int(fields[1])
                state.bet = to_int(fields[2])
                state.round_net = to_int(fields[3])
                state.cumulative_net = to_int(fields[4])
                state.result = fields[5]
            elif tag == "RC":
                need(record, fields, 4)
                state.running_count = to_int(fields[1])
                state.true_count = float(fields[2])
                state.decks_left = float(fields[3])
            elif tag == "HAND":
                need(record, fields, 10)
                state.hands.append(
                    Hand(
                        index=to_int(fields[1]),
                        role=fields[2],
                        status=fields[3],
                        total=to_int(fields[4]),
                        soft=fields[5] == "Y",
                        result=fields[6],
                        bet=to_int(fields[7]),
                        paid=to_int(fields[8]),
                        cards=[parse_card(tok) for tok in fields[10:]],
                    )
                )
            elif tag == "FLAGS":
                need(record, fields, 3)
                state.double_ok = fields[1] == "Y"
                state.insured = fields[2] == "Y"
            elif tag == "STATS":
                need(record, fields, 7)
                state.stats = Stats(
                    wins=to_int(fields[1]),
                    pushes=to_int(fields[2]),
                    losses=to_int(fields[3]),
                    rounds=to_int(fields[4]),
                    net=to_int(fields[5]),
                    best=to_int(fields[6]),
                )
            elif tag == "NOTE":
                state.note = " ".join(fields[1:])
        except (IndexError, ValueError) as exc:
            raise EngineError(f"unreadable record {record.strip()!r}: {exc}") from exc
    return state