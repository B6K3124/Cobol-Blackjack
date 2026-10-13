"""The playing table and the main window.

A green felt surface with the dealer's hand at the top, the player's
hands below, XP push buttons across the bottom and a side rail carrying
the bankroll, the chip rack, the hi-lo count and the session statistics.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QKeySequence,
    QPainter,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import xp
from .cards import HandView
from .chrome import (
    LunaTitleBar,
    SunkenPanel,
    XPButton,
    XPStatusBar,
    Chip,
    game_icon,
)
from .engine import Engine, EngineError, GameState, money

MAX_PLAYER_VIEWS = 1
CHIP_VALUES = [1, 5, 25, 100, 500, 1000]

BANNER_COLOURS = {
    "W": QColor(140, 255, 140),
    "P": QColor(255, 236, 150),
    "L": QColor(255, 140, 130),
    "-": QColor(235, 245, 235),
}


# --------------------------------------------------------------------------
# felt
# --------------------------------------------------------------------------
class Felt(QWidget):
    action = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(700, 560)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.dealer = HandView("Dealer", dealer=True)
        self.dealer.clicked.connect(lambda: self.action.emit("DEAL"))
        self.dealer.setParent(self)

        self.players: list[HandView] = []
        for _ in range(MAX_PLAYER_VIEWS):
            view = HandView("Hand")
            view.clicked.connect(self._on_player_clicked)
            self.players.append(view)
            view.hide()
            view.setParent(self)

        self.buttons: dict[str, XPButton] = {}
        for key, label, hint, default in (
            ("DEAL", "DEAL", "Space", True),
            ("HIT", "HIT", "H", False),
            ("STAND", "STAND", "S", False),
            ("DOUBLE", "DOUBLE", "D", False),
        ):
            button = XPButton(label, default=default, shortcut=hint)
            button.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            self.buttons[key] = button
            button.hide()
            button.setParent(self)

        self.insurance: list[XPButton] = []
        for label, hint, key in (
            ("INSURE", "I", "INSURE"),
            ("NO INSURANCE", "N", "NOINSURE"),
        ):
            button = XPButton(label, shortcut=hint)
            button.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            self.insurance.append(button)
            button.hide()
            button.setParent(self)

        self.banner = "Welcome to the table"
        self.banner_colour = BANNER_COLOURS["-"]
        self._flash = False
        self.top_left = ""
        self.top_right = ""
        self._pulse = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    # -- interactions -------------------------------------------------------
    def _on_player_clicked(self) -> None:
        self.action.emit("DEAL")

    # -- state --------------------------------------------------------------
    def apply(self, state: GameState, selected_bet: int) -> None:
        self.banner, self.banner_colour = self._message(state)
        self._flash = self.banner_colour in (
            BANNER_COLOURS["W"],
            BANNER_COLOURS["L"],
        )
        self.top_left = (
            f"Bankroll {money(state.bankroll)}      "
            f"Bet {money(max(state.bet, selected_bet))}"
        )
        stats = state.stats
        self.top_right = (
            f"Round {stats.rounds:,}      W {stats.wins}   P {stats.pushes}   "
            f"L {stats.losses}"
        )

        if state.dealer is not None:
            self.dealer.set_hand(state.dealer)
        else:
            self.dealer.set_empty()

        hands = state.player_hands
        for index, view in enumerate(self.players):
            if index < len(hands):
                view.set_hand(hands[index])
                view.show()
            else:
                view.set_empty(f"Hand {index + 1}")
                view.hide()
        self._layout_hands()
        self._layout_buttons(state)
        self.update()

    def _message(self, state: GameState) -> tuple[str, QColor]:
        note = state.note.strip()
        colour = BANNER_COLOURS["-"]
        if state.phase == "INSURANCE":
            return ("Dealer shows an ace - insurance?", BANNER_COLOURS["P"])
        if note and note not in ("Good luck", "Place your bet"):
            if state.result in BANNER_COLOURS and state.phase == "SETTLE":
                colour = BANNER_COLOURS[state.result]
            return note, colour
        if state.phase == "IDLE":
            return "Place your bet and press DEAL", colour
        if state.phase == "PLAYER":
            hand = state.active_hand
            if hand:
                return f"Hand {hand.index - 1} - your move", colour
            return "Your move", colour
        if state.phase == "DEALER":
            return "Dealer playing", colour
        if state.phase == "SETTLE":
            return {
                "W": f"You win {money(state.round_net)}",
                "L": f"You lose {money(abs(state.round_net))}",
                "P": "Push - bet returned",
            }.get(state.result, "Hand complete"), BANNER_COLOURS.get(
                state.result, colour
            )
        return note or "", colour

    # -- layout -------------------------------------------------------------
    def _layout_hands(self) -> None:
        dealer_y = 52
        self.dealer.move(28, dealer_y)
        self.dealer.set_spread(1.0)

        shown = [view for view in self.players if view.isVisible()]
        if not shown:
            return

        available = max(360, self.width() - 56)
        gap = 20
        count = len(shown)
        if count > 1:
            gap = max(10, (available - count * 200) // (count + 1))
        share = max(150, (available - gap * (count - 1)) // count)

        y = max(dealer_y + 190, self.height() - 272)
        x = 28
        for view in shown:
            cards = view.card_count
            if cards > 1:
                room = (share - 74 - 10) // (cards - 1)
                view.set_spread(max(0.2, min(1.0, room / 74.0)))
            else:
                view.set_spread(1.0)
            view.relayout(share)
            view.move(x, y)
            x += view.width() + gap

    def _layout_buttons(self, state: GameState) -> None:
        visible = []
        for key, button in self.buttons.items():
            show = self._button_visible(key, state)
            button.setVisible(show)
            if show:
                visible.append(button)

        gap = 8
        for button in visible:
            button.adjustSize()
        width = sum(button.width() for button in visible) + gap * (len(visible) + 1)
        x = max(20, (self.width() - width) // 2)
        y = self.height() - 50
        for button in visible:
            button.move(x, y)
            x += button.width() + gap

        insuring = state.phase == "INSURANCE"
        for button in self.insurance:
            button.setVisible(insuring)
        if insuring:
            first, second = self.insurance
            for button in (first, second):
                button.adjustSize()
            space = 28
            width = first.width() + space + second.width()
            x = max(20, (self.width() - width) // 2)
            y = self.height() // 2 - 48
            first.move(x, y)
            second.move(x + first.width() + space, y)

    def _button_visible(self, key: str, state: GameState) -> bool:
        if state.phase in ("IDLE", "SETTLE"):
            return key == "DEAL"
        if state.phase == "PLAYER":
            return key in ("HIT", "STAND", "DOUBLE")
        return False

    def _tick(self) -> None:
        if not self._flash:
            return
        self._pulse = (self._pulse + 1) % 22
        self.update()

    # -- painting -----------------------------------------------------------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        rect = QRectF(self.rect())

        painter.fillRect(self.rect(), QBrush(xp.felt_gradient(rect)))

        painter.setPen(QPen(QColor(255, 255, 255, 26), 1))
        for offset in range(6, self.height(), 9):
            painter.drawLine(0, offset, self.width(), offset)

        painter.setPen(QColor(255, 255, 255, 26))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(6, 6, -6, -6), 10, 10)

        painter.setFont(xp.ui_font(8, bold=True))
        painter.setPen(QColor(0, 0, 0, 110))
        painter.drawText(
            QRectF(18, 14, self.width() * 0.55, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.top_left,
        )
        painter.setPen(QColor(255, 255, 255, 225))
        painter.drawText(
            QRectF(18, 14, self.width() * 0.55, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.top_left,
        )
        painter.drawText(
            QRectF(self.width() * 0.42, 14, self.width() * 0.56, 18),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            self.top_right,
        )

        if self.banner:
            font = xp.ui_font(17, bold=True)
            painter.setFont(font)
            box = QRectF(0, self.height() - 168, self.width(), 60)
            colour = QColor(self.banner_colour)
            if self._flash:
                glow = 1.0 + 0.35 * abs((self._pulse % 11) / 5.5 - 1.0)
                colour = colour.lighter(int(100 + 90 * glow))
            painter.setPen(QColor(0, 0, 0, 140))
            painter.drawText(box.translated(0, 2),
                             Qt.AlignmentFlag.AlignCenter, self.banner)
            painter.setPen(colour)
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, self.banner)
        painter.end()


# --------------------------------------------------------------------------
# side rail
# --------------------------------------------------------------------------
def _label(text: str, size: int = 8, bold: bool = False) -> QLabel:
    label = QLabel(text)
    font = xp.ui_font(size, bold)
    label.setFont(font)
    label.setStyleSheet("background: transparent; border: none;")
    label.setContentsMargins(2, 1, 2, 1)
    return label


class SideRail(QWidget):
    bet_picked = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(214)
        self.chips: list[Chip] = []
        self._values: dict[str, QLabel] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(7)

        money_panel = SunkenPanel("Bankroll")
        box = QVBoxLayout(money_panel)
        box.setContentsMargins(11, 21, 11, 10)
        box.setSpacing(1)
        self.bankroll = _label("$0.00", 16, True)
        self.bankroll.setStyleSheet("color: rgb(20, 70, 20); background: transparent;")
        box.addWidget(self.bankroll)
        self.bet_line = _label("Bet $0.00")
        box.addWidget(self.bet_line)
        box.addStretch(1)
        outer.addWidget(money_panel)

        chip_panel = SunkenPanel("Chips")
        grid = QGridLayout(chip_panel)
        grid.setContentsMargins(9, 21, 9, 10)
        grid.setSpacing(2)
        for index, value in enumerate(CHIP_VALUES):
            chip = Chip(value)
            chip.clicked.connect(self.bet_picked.emit)
            self.chips.append(chip)
            grid.addWidget(chip, index // 3, index % 3)
        outer.addWidget(chip_panel)

        count_panel = SunkenPanel("Count")
        count_box = QVBoxLayout(count_panel)
        count_box.setContentsMargins(11, 21, 11, 10)
        count_box.setSpacing(1)
        self._values["running"] = _label("Running  0")
        self._values["true"] = _label("True  0.0")
        self._values["decks"] = _label("Decks left  4.5")
        for key in ("running", "true", "decks"):
            count_box.addWidget(self._values[key])
        count_box.addStretch(1)
        outer.addWidget(count_panel)

        stats_panel = SunkenPanel("Session")
        stats_box = QVBoxLayout(stats_panel)
        stats_box.setContentsMargins(11, 21, 11, 10)
        stats_box.setSpacing(1)
        for key, caption in (
            ("wins", "Wins"),
            ("pushes", "Pushes"),
            ("losses", "Losses"),
            ("rounds", "Rounds"),
            ("net", "Net"),
            ("best", "Best"),
        ):
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(2, 0, 2, 0)
            row_layout.addWidget(_label(caption))
            value = _label("0", bold=True)
            row_layout.addStretch(1)
            row_layout.addWidget(value)
            self._values[key] = value
            stats_box.addWidget(row)
        outer.addWidget(stats_panel)
        outer.addStretch(1)

    def update_state(self, state: GameState, selected_bet: int) -> None:
        self.bankroll.setText(money(state.bankroll))
        self.bet_line.setText(
            f"Bet {money(state.bet or selected_bet)}"
            + ("   (insurance taken)" if state.insured else "")
        )
        self._values["running"].setText(f"Running  {state.running_count:+d}")
        self._values["true"].setText(f"True  {state.true_count:+.2f}")
        self._values["decks"].setText(f"Decks left  {state.decks_left:.2f}")
        stats = state.stats
        self._values["wins"].setText(f"{stats.wins:,}")
        self._values["pushes"].setText(f"{stats.pushes:,}")
        self._values["losses"].setText(f"{stats.losses:,}")
        self._values["rounds"].setText(f"{stats.rounds:,}")
        self._values["net"].setText(money(stats.net))
        self._values["best"].setText(money(stats.best))

        enable = state.can_bet and state.bankroll > 0
        for chip in self.chips:
            chip.setEnabled(enable and chip.value <= state.bankroll)


# --------------------------------------------------------------------------
# main window
# --------------------------------------------------------------------------
class GameWindow(QWidget):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self._bet = 25
        self._ready = False
        self._starting = True

        self.setWindowTitle("Blackjack")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setWindowIcon(game_icon(32))
        self.resize(1040, 700)
        self.setMinimumSize(760, 600)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.titlebar = LunaTitleBar("Blackjack")
        self.titlebar.close_requested.connect(self.close)
        self.titlebar.minimize_requested.connect(self.showMinimized)
        self.titlebar.maximize_requested.connect(self.toggle_maximize)
        root.addWidget(self.titlebar)

        self.menubar = QMenuBar()
        self._build_menus()
        root.addWidget(self.menubar)

        body = QWidget()
        body.setAutoFillBackground(False)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.felt = Felt()
        self.felt.action.connect(self.send)
        body_layout.addWidget(self.felt, 1)

        self.rail = SideRail()
        self.rail.bet_picked.connect(self.pick_bet)
        body_layout.addWidget(self.rail)
        root.addWidget(body, 1)

        self.status = XPStatusBar()
        root.addWidget(self.status)

        self._shortcuts = {
            "H": "HIT",
            "S": "STAND",
            "D": "DOUBLE",
            "I": "INSURE",
            "N": "NOINSURE",
            " ": "DEAL",
        }
        for key, command in self._shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda k=command: self.send(k))
        restart = QShortcut(QKeySequence("Ctrl+N"), self)
        restart.activated.connect(self.new_game)

        self.set_state(self.engine.state)
        self._refresh_buttons()

    # -- menus --------------------------------------------------------------
    def _build_menus(self) -> None:
        game = self.menubar.addMenu("&Game")
        new = QAction("&New Game", self)
        new.setShortcut(QKeySequence("Ctrl+N"))
        new.triggered.connect(self.new_game)
        quit_action = QAction("E&xit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        game.addAction(new)
        game.addSeparator()
        game.addAction(quit_action)

        options = self.menubar.addMenu("&Options")
        self._hint_action = QAction("Show card &hints", self)
        self._hint_action.setCheckable(True)
        self._hint_action.triggered.connect(self._toggle_hints)
        options.addAction(self._hint_action)

        help_menu = self.menubar.addMenu("&Help")
        rules = QAction("&Blackjack Rules", self)
        rules.triggered.connect(self.show_rules)
        about = QAction("&About Blackjack", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(rules)
        help_menu.addSeparator()
        help_menu.addAction(about)

    def _toggle_hints(self, on: bool) -> None:
        status = "Card hints on" if on else "Card hints off"
        self.status.set_panes(status, self._status_right(), "")

    # -- engine -------------------------------------------------------------
    def start(self) -> None:
        self.status.set_panes("Starting the COBOL engine...", "", "")
        self.felt.banner = "Starting the COBOL engine..."
        try:
            state = self.engine.start()
        except EngineError as exc:
            self.felt.banner = "Could not start the engine"
            self.status.set_panes(str(exc)[:70], "", "")
            self.felt.update()
            return
        self._starting = False
        self._ready = True
        self.set_state(state)

    def send(self, command: str) -> None:
        if not self._ready:
            return
        try:
            if command == "DEAL":
                if self.engine.state.bankroll < self._bet:
                    self.felt.banner = "Not enough chips for that bet"
                    self.felt.update()
                    return
                self.engine.command(f"BET {self._bet}")
            state = self.engine.command(command)
        except EngineError as exc:
            self._ready = False
            self.felt.banner = str(exc)
            self.felt.update()
            self.status.set_panes(str(exc)[:70], "", "")
            return
        self.set_state(state)

    def pick_bet(self, value: int) -> None:
        self._bet = value
        for chip in self.rail.chips:
            chip.setSelected(chip.value == value)
        if self._ready and self.engine.state.can_bet:
            try:
                self.set_state(self.engine.command(f"BET {value}"))
                return
            except EngineError:
                pass
        self.set_state(self.engine.state)

    def new_game(self) -> None:
        if self._starting:
            return
        self._starting = True
        self._ready = False
        self.status.set_panes("Dealing in a new shoe...", "", "")
        QApplication.processEvents()
        try:
            self.set_state(self.engine.restart())
            self._ready = True
            self._starting = False
        except EngineError as exc:
            self.felt.banner = str(exc)
            self.felt.update()

    # -- rendering ----------------------------------------------------------
    def set_state(self, state: GameState) -> None:
        self.felt.apply(state, self._bet)
        self.rail.update_state(state, self._bet)
        self._refresh_buttons()
        self.status.set_panes(
            self._status_left(state),
            self._status_right(),
            f"Engine: {self.engine.argv_label}",
        )
        window_title = "Blackjack"
        if state.phase in ("PLAYER", "INSURANCE"):
            window_title = "Blackjack - your move"
        self.titlebar.set_title(window_title)

    def _status_left(self, state: GameState) -> str:
        if self._starting:
            return "Starting the COBOL engine..."
        return {
            "IDLE": "Place a bet, then DEAL",
            "PLAYER": f"Hand {len(state.player_hands)} in play",
            "INSURANCE": "Insurance decision",
            "DEALER": "Dealer turn",
            "SETTLE": "Round complete",
        }.get(state.phase, "Ready")

    def _status_right(self) -> str:
        count = self.engine.state
        return (
            f"Running {count.running_count:+d}   "
            f"True {count.true_count:+.2f}   "
            f"Decks {count.decks_left:.2f}"
        )

    def _refresh_buttons(self) -> None:
        state = self.engine.state
        playing = state.phase == "PLAYER"
        self.felt.buttons["HIT"].setEnabled(self._ready and playing)
        self.felt.buttons["STAND"].setEnabled(self._ready and playing)
        self.felt.buttons["DOUBLE"].setEnabled(
            self._ready and playing and state.double_ok
        )
        self.felt.buttons["DEAL"].setEnabled(
            self._ready and state.can_bet and state.bankroll > 0
        )
        insuring = self._ready and state.phase == "INSURANCE"
        for button in self.felt.insurance:
            button.setEnabled(insuring)

    # -- window -------------------------------------------------------------
    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def resizeEvent(self, event) -> None:
        if hasattr(self, "felt"):
            self.felt._layout_hands()
            self.felt._layout_buttons(self.engine.state)
        super().resizeEvent(event)

    def changeEvent(self, event) -> None:
        if event.type() == event.Type.ActivationChange:
            self.titlebar.set_active(self.isActiveWindow())
        super().changeEvent(event)

    def show_rules(self) -> None:
        self._message(
            "Blackjack Rules",
            "Blackjack pays 3 to 2.\n"
            "Dealer stands on 17, hits on 16.\n"
            "Double on the first two cards of a hand.\n"
            "Insurance offered when the dealer shows an ace.\n"
            "Six decks, shuffled at the 75% penetration mark.",
        )

    def show_about(self) -> None:
        self._message(
            "About Blackjack",
            "A blackjack table written in COBOL with a PySide6 front end.\n\n"
            "The game logic, shoe, shuffling, dealer and payouts are "
            "computed by GnuCOBOL; this window only draws the table.\n\n"
            "Styling: Windows XP Luna / Solitaire.",
        )

    def _message(self, title: str, text: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(text)
        box.setFont(xp.ui_font(9))
        box.exec()

    def closeEvent(self, event) -> None:
        self.engine.close()
        super().closeEvent(event)