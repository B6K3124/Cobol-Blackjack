"""Painted playing cards in the Windows XP Solitaire style.

Face up cards are white rounded rectangles with a bold corner index and a
large centre pip, exactly like the cards that shipped with Windows XP.
Face down cards use the blue Solitaire back with its diamond lattice.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import xp

CARD_WIDTH = 74
CARD_HEIGHT = 100


def _chip_font(pixel: int) -> QFont:
    font = xp.ui_font(9, bold=True)
    font.setPixelSize(pixel)
    return font


class CardWidget(QWidget):
    """A single card, face up or face down."""

    clicked = Signal()

    def __init__(self, card: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._rank = card[0] if card else ""
        self._suit = card[1] if card else ""
        self._face_down = not card
        self._highlight = False
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # -- state --------------------------------------------------------------
    def set_card(self, card) -> None:
        if card is None:
            self._rank, self._suit = "", ""
            self._face_down = True
        else:
            self._rank, self._suit = card[0], card[1]
            self._face_down = False
        self.update()

    def set_highlight(self, on: bool) -> None:
        if self._highlight != on:
            self._highlight = on
            self.update()

    @property
    def is_face_down(self) -> bool:
        return self._face_down

    # -- painting -----------------------------------------------------------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        rect = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)

        if self._highlight:
            glow = QRectF(rect).adjusted(-2, -2, 2, 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 150))
            painter.drawRoundedRect(glow, 4, 4)

        shadow = QRectF(rect).translated(2.0, 2.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 55))
        painter.drawRoundedRect(shadow, 3.5, 3.5)

        if self._face_down:
            self._paint_back(painter, rect)
        else:
            self._paint_face(painter, rect)
        painter.end()

    def _paint_back(self, painter: QPainter, rect: QRectF) -> None:
        body = QPainterPath()
        body.addRoundedRect(rect, 3.5, 3.5)
        painter.fillPath(body, xp.BACK_FILL)

        painter.save()
        painter.setClipPath(body)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(xp.BACK_PATTERN)
        step = 9.0
        radius = 2.2
        row = 0
        y = rect.top()
        while y < rect.bottom() + step:
            offset = (step / 2) if row % 2 else 0.0
            x = rect.left() - step + offset
            while x < rect.right() + step:
                path = QPainterPath()
                path.moveTo(x, y - radius)
                path.lineTo(x + radius, y)
                path.lineTo(x, y + radius)
                path.lineTo(x - radius, y)
                path.closeSubpath()
                painter.drawPath(path)
                x += step
            y += step
            row += 1
        painter.restore()

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 70), 1.0))
        painter.drawRoundedRect(rect.adjusted(2.5, 2.5, -2.5, -2.5), 2.5, 2.5)
        painter.setPen(QPen(xp.BACK_BORDER, 1.4))
        painter.drawRoundedRect(rect, 3.5, 3.5)

    def _paint_face(self, painter: QPainter, rect: QRectF) -> None:
        body = QPainterPath()
        body.addRoundedRect(rect, 3.5, 3.5)
        painter.fillPath(body, xp.CARD_FACE)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(xp.CARD_EDGE, 1.0))
        painter.drawRoundedRect(rect, 3.5, 3.5)

        colour = xp.suit_colour(self._suit)
        glyph = xp.SUIT_GLYPH[self._suit]
        h = rect.height()
        w = rect.width()

        rank_font = _chip_font(max(11, int(h * 0.215)))
        suit_font = xp.suit_font(max(9, int(h * 0.155)))

        inset_x = rect.left() + w * 0.085
        inset_y = rect.top() + h * 0.045

        painter.setPen(QPen(colour))
        painter.setFont(rank_font)
        metrics = painter.fontMetrics()
        rank_w = metrics.horizontalAdvance(self._rank)
        painter.drawText(
            QRectF(inset_x - 1, inset_y - 1, rank_w + 4, rank_font.pixelSize() + 4),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._rank,
        )
        painter.setFont(suit_font)
        painter.drawText(
            QRectF(inset_x - 1, inset_y + rank_font.pixelSize() - 2,
                   rank_w + 8, suit_font.pixelSize() + 6),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            glyph,
        )

        painter.save()
        painter.translate(rect.center())
        painter.rotate(180)
        painter.setFont(rank_font)
        painter.drawText(
            QRectF(-inset_x - rank_w - 3, -inset_y - rank_font.pixelSize() - 3,
                   rank_w + 4, rank_font.pixelSize() + 4),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._rank,
        )
        painter.setFont(suit_font)
        painter.drawText(
            QRectF(-inset_x - rank_w - 5,
                   -inset_y - rank_font.pixelSize() - suit_font.pixelSize() + 2,
                   rank_w + 8, suit_font.pixelSize() + 6),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            glyph,
        )
        painter.restore()

        big = xp.suit_font(int(h * 0.52))
        painter.setFont(big)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, glyph)
        painter.setPen(QPen(xp.CARD_EDGE, 1.0))


class HandView(QWidget):
    """A fanned row of cards plus the hand's total and outcome."""

    clicked = Signal()

    def __init__(self, title: str, dealer: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._dealer = dealer
        self._cards: list[CardWidget] = []
        self._total = 0
        self._soft = False
        self._result = "-"
        self._active = False
        self._bet = 0
        self._paid = 0
        self._spread = 1.0
        self._min_width = 200
        self.setFixedSize(200, CARD_HEIGHT + 44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # -- geometry -----------------------------------------------------------
    def _card_x(self, index: int) -> int:
        if index == 0:
            return 0
        spread = max(18, int(CARD_WIDTH * self._spread))
        if len(self._cards) <= 5:
            spread = min(spread, int(CARD_WIDTH * 0.62))
        else:
            spread = max(12, spread - (index - 4) * 2)
        return index * spread

    def relayout(self, min_width: int | None = None) -> None:
        if min_width is not None:
            self._min_width = min_width
        for index, card in enumerate(self._cards):
            card.move(self._card_x(index), 26)
        visible = len([c for c in self._cards if c.isVisible()])
        needed = self._card_x(visible - 1) + CARD_WIDTH if visible else 0
        self.setFixedWidth(max(self._min_width, needed + 6))
        self.setFixedHeight(CARD_HEIGHT + 44)
        self.updateGeometry()
        self.update()

    # -- state --------------------------------------------------------------
    def set_hand(self, hand) -> None:
        cards = list(hand.cards)
        while len(self._cards) < len(cards):
            widget = CardWidget()
            widget.clicked.connect(self.clicked.emit)
            self._cards.append(widget)
            widget.setParent(self)
        for index, widget in enumerate(self._cards):
            widget.setVisible(index < len(cards))
            if index < len(cards):
                widget.set_card(None if cards[index].face_down else cards[index].token)
        self._total = hand.total
        self._soft = hand.soft
        self._result = hand.result
        self._active = hand.status == "A"
        self._bet = hand.bet
        self._paid = hand.paid
        self._title = hand.label
        self.relayout()

    def set_empty(self, title: str | None = None) -> None:
        for widget in self._cards:
            widget.setVisible(False)
        if title:
            self._title = title
        self._total = 0
        self._soft = False
        self._result = "-"
        self._active = False
        self._bet = 0
        self._paid = 0
        self.relayout()

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self.update()

    def set_placeholder_cards(self, count: int) -> None:
        while len(self._cards) < count:
            widget = CardWidget()
            self._cards.append(widget)
            widget.setParent(self)
        for index, widget in enumerate(self._cards):
            widget.set_card(None)
            widget.setVisible(index < count)
        self.relayout()

    def set_spread(self, spread: float) -> None:
        if abs(spread - self._spread) > 0.01:
            self._spread = spread
            self.relayout()

    @property
    def card_count(self) -> int:
        return len([w for w in self._cards if w.isVisible()])

    # -- painting -----------------------------------------------------------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        total_text = f"{self._total}"
        if self._soft:
            total_text = f"{self._total} soft"
        if self._total:
            badge = total_text
        else:
            badge = "--"

        painter.setFont(xp.ui_font(9, bold=True))
        title_colour = (QColor(255, 255, 255, 200) if self._dealer
                        else QColor(255, 255, 255, 235))
        painter.setPen(title_colour)
        painter.drawText(
            QRectF(4, 2, self.width() - 150, 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._title.upper(),
        )

        metrics = painter.fontMetrics()
        badge_w = metrics.horizontalAdvance(badge) + 22
        badge_rect = QRectF(self.width() - badge_w - 4, 1, badge_w, 18)
        painter.setBrush(QColor(0, 0, 0, 90))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 9, 9)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        painter.drawRoundedRect(badge_rect, 9, 9)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            badge_rect, Qt.AlignmentFlag.AlignCenter, f"TOTAL {badge}"
        )

        if self._bet:
            painter.setFont(xp.ui_font(8))
            painter.setPen(QColor(255, 235, 150, 220))
            painter.drawText(
                QRectF(4, 2, self.width() - 160, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"Bet {self._bet / 100:,.2f}",
            )

        if self._result in ("W", "P", "L", "B") and not self._active:
            colour = {
                "W": QColor(120, 255, 120),
                "P": QColor(255, 235, 140),
                "L": QColor(255, 130, 120),
            }.get(self._result, QColor(255, 255, 255))
            painter.setFont(xp.ui_font(10, bold=True))
            painter.setPen(colour)
            painter.drawText(
                QRectF(0, 22, 92, 22),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"[{self._result}]",
            )

        painter.end()