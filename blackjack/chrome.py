"""Luna flavoured window furniture.

Frameless title bar with the blue gradient caption, the little caption
buttons, XP push buttons, casino chips and the sunken status bar.  All of
it is painted by hand so the shapes match the 2001 originals instead of
whatever the platform theme decides.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QLabel, QWidget

from . import xp

CAPTION_HEIGHT = 30
BUTTON_SIZE = QSize(21, 21)


# --------------------------------------------------------------------------
# application icon
# --------------------------------------------------------------------------
def game_icon(size: int = 32) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    plate = QRectF(0, 0, size, size)
    gradient = QLinearGradient(plate.topLeft(), plate.bottomLeft())
    gradient.setColorAt(0.0, QColor("#F5F2E8"))
    gradient.setColorAt(1.0, QColor("#D8D3C2"))
    path = QPainterPath()
    path.addRoundedRect(plate.adjusted(1, 1, -1, -1), size * 0.18, size * 0.18)
    painter.fillPath(path, gradient)
    painter.setPen(QPen(QColor("#8A8676"), 1))
    painter.drawPath(path)

    painter.setFont(xp.suit_font(int(size * 0.68)))
    painter.setPen(xp.CARD_RED)
    painter.drawText(plate, Qt.AlignmentFlag.AlignCenter, "\u2660")
    painter.end()
    return pixmap


# --------------------------------------------------------------------------
# caption buttons
# --------------------------------------------------------------------------
class CaptionButton(QWidget):
    clicked = Signal()

    def __init__(self, kind: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.kind = kind
        self._hover = False
        self._down = False
        self.setFixedSize(BUTTON_SIZE)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hover = False
        self._down = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._down = True
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._down:
            self._down = False
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)

        if self.kind == "close":
            top = QColor("#F3A79C") if (self._hover or self._down) else QColor("#D97E72")
            bottom = QColor("#C33B2C") if (self._hover or self._down) else QColor("#B8483C")
        elif self._hover or self._down:
            top, bottom = QColor("#8EC0F5"), QColor("#2A6FC4")
        else:
            top, bottom = QColor("#EFF3F8"), QColor("#B8CBE2")

        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(0.5, top)
        gradient.setColorAt(0.51, bottom)
        gradient.setColorAt(1.0, bottom)

        path = QPainterPath()
        path.addRoundedRect(rect, 3, 3)
        painter.fillPath(path, QBrush(gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 110), 1))
        painter.drawPath(path)

        glyph = QColor(255, 255, 255) if self._hover or self.kind == "close" else QColor(
            40, 60, 90
        )
        painter.setPen(QPen(glyph, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        w, h = self.width(), self.height()
        if self.kind == "min":
            painter.drawLine(QPoint(int(w * 0.28), int(h * 0.68)),
                             QPoint(int(w * 0.72), int(h * 0.68)))
        elif self.kind == "max":
            painter.drawRect(QRectF(w * 0.26, h * 0.28, w * 0.48, h * 0.44))
            painter.drawLine(QPoint(int(w * 0.26), int(h * 0.40)),
                             QPoint(int(w * 0.74), int(h * 0.40)))
        else:
            painter.drawLine(QPoint(int(w * 0.32), int(h * 0.32)),
                             QPoint(int(w * 0.68), int(h * 0.68)))
            painter.drawLine(QPoint(int(w * 0.68), int(h * 0.32)),
                             QPoint(int(w * 0.32), int(h * 0.68)))
        painter.end()


class LunaTitleBar(QWidget):
    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._active = True
        self._drag_offset = QPoint()
        self._dragging = False
        self.setFixedHeight(CAPTION_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self.icon = QLabel(self)
        self.icon.setPixmap(game_icon(16))
        self.icon.move(4, (CAPTION_HEIGHT - 16) // 2)
        self.icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._min = CaptionButton("min", self)
        self._max = CaptionButton("max", self)
        self._close = CaptionButton("close", self)
        for button, signal in (
            (self._min, self.minimize_requested),
            (self._max, self.maximize_requested),
            (self._close, self.close_requested),
        ):
            button.clicked.connect(signal)
        self._position_buttons()

    def set_title(self, title: str) -> None:
        self._title = title
        self.update()

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self.update()

    def _position_buttons(self) -> None:
        x = self.width() - 6
        for button in (self._close, self._max, self._min):
            button.move(x - button.width(), (CAPTION_HEIGHT - button.height()) // 2)
            x -= button.width() + 2

    def resizeEvent(self, event) -> None:
        self._position_buttons()
        super().resizeEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            self._drag_offset = event.globalPosition().toPoint() - window.pos()
            self._dragging = True

    def mouseMoveEvent(self, event) -> None:
        if getattr(self, "_dragging", False):
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        full = QRectF(-8, -8, self.width() + 16, self.height() + 8)
        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(full, 7, 7)
        path.addRect(QRectF(0, self.height() - 8, self.width(), 8))
        painter.fillPath(path, QBrush(xp.luna_gradient(rect, self._active)))

        painter.setPen(QPen(xp.LUNA_EDGE if self._active else xp.CAPTION_INACTIVE_EDGE, 1))
        path = QPainterPath()
        path.addRoundedRect(full.adjusted(0.5, 0.5, -0.5, -0.5), 7, 7)
        path.addRect(QRectF(0, self.height() - 8, self.width(), 8))
        painter.drawPath(path)

        text_rect = QRectF(26, 0, self.width() - 130, self.height())
        font = xp.caption_font()
        painter.setFont(font)
        painter.setPen(QPen(xp.LUNA_SHADOW, 1))
        painter.drawText(text_rect.translated(1, 1),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         self._title)
        painter.setPen(
            QPen(xp.LUNA_TEXT if self._active else QColor(240, 245, 250), 1)
        )
        painter.drawText(text_rect,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         self._title)
        painter.end()


# --------------------------------------------------------------------------
# push buttons
# --------------------------------------------------------------------------
class XPButton(QWidget):
    clicked = Signal()

    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        default: bool = False,
        shortcut: str = "",
    ):
        super().__init__(parent)
        self._text = text
        self._shortcut = shortcut
        self._default = default
        self._hover = False
        self._down = False
        self._enabled = True
        self._focus = False
        self.setMinimumHeight(23)
        self.setFixedHeight(23)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.adjustSize()

    # -- sizing -------------------------------------------------------------
    def _label_text(self) -> str:
        label = self._text[1:] if self._text.startswith("&") else self._text
        if self._shortcut:
            label = f"{label} ({self._shortcut})"
        return label

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self.font())
        width = metrics.horizontalAdvance(self._label_text()) + 40
        return QSize(max(78, width), 23)

    def minimumSizeHint(self) -> QSize:
        return QSize(78, 23)

    # -- api ----------------------------------------------------------------
    def setText(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self.adjustSize()
            self.updateGeometry()
            self.update()

    def text(self) -> str:
        return self._text

    def setDefault(self, on: bool) -> None:
        self._default = on
        self.update()

    def setShortcutHint(self, hint: str) -> None:
        self._shortcut = hint
        self.update()

    def setEnabled(self, on: bool) -> None:
        self._enabled = on
        if not on:
            self.unsetCursor()
        self.update()

    def isEnabled(self) -> bool:
        return self._enabled

    # -- events -------------------------------------------------------------
    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hover = False
        self._down = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if not self._enabled:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._down = True
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._down:
            self._down = False
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()

    def focusInEvent(self, event) -> None:
        self._focus = True
        self.update()

    def focusOutEvent(self, event) -> None:
        self._focus = False
        self.update()

    def keyPressEvent(self, event) -> None:
        if not self._enabled:
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(event)

    # -- painting -----------------------------------------------------------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        shift = 1.0 if self._down else 0.0

        if not self._enabled:
            face = QColor("#F2F0E9")
            painter.fillPath(_rounded(rect), face)
            painter.setPen(QPen(QColor("#C9C5BA"), 1))
            painter.drawPath(_rounded(rect))
            text_colour = xp.GRAYTEXT
        else:
            painter.fillPath(_rounded(rect), QBrush(xp.button_gradient(rect, self._down)))
            border = QColor("#7B9BB8")
            if self._hover:
                border = QColor("#4E86C6")
            painter.setPen(QPen(border, 1))
            painter.drawPath(_rounded(rect))
            painter.setPen(QPen(QColor(255, 255, 255, 170), 1))
            top = QRectF(rect.left() + 1.5, rect.top() + 1.2,
                         rect.width() - 3, rect.height() * 0.45)
            painter.drawPath(_rounded(top, 2.5))
            if self._default:
                painter.setPen(QPen(QColor("#4B4B4B"), 2))
                painter.drawPath(_rounded(rect.adjusted(-0.5, -0.5, 0.5, 0.5), 3.5))
            if self._focus or self._default:
                glow = rect.adjusted(-3.5, -3.5, 3.5, 3.5)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(96, 160, 232, 190), 2))
                painter.drawRoundedRect(glow, 5, 5)
            text_colour = xp.QColor(20, 20, 20)

        painter.setFont(xp.ui_font(8, bold=self._default))
        painter.setPen(QPen(text_colour))
        text_rect = rect.translated(0, shift)

        label = self._text
        mnemonic = label[1] if label.startswith("&") else ""
        if mnemonic:
            label = label[1:]
        if self._shortcut:
            label = f"{label} ({self._shortcut})"

        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

        if mnemonic and self._enabled:
            metrics = painter.fontMetrics()
            start = text_rect.left() + (text_rect.width() - metrics.horizontalAdvance(label)) / 2
            width = metrics.horizontalAdvance(mnemonic)
            baseline = text_rect.center().y() + (
                metrics.ascent() - metrics.descent()
            ) / 2 + 2
            painter.drawLine(int(start), int(baseline),
                             int(start + width), int(baseline))
        painter.end()


def _rounded(rect: QRectF, radius: float = 3.0) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


# --------------------------------------------------------------------------
# chips
# --------------------------------------------------------------------------
CHIP_COLOURS = {
    1: ("#E9E4D6", "#3C5C9C"),
    5: ("#D62B2B", "#FFFFFF"),
    25: ("#1E9B47", "#FFFFFF"),
    100: ("#141414", "#E8C34A"),
    500: ("#5B2E91", "#E8C34A"),
    1000: ("#C9A227", "#FFFFFF"),
}


class Chip(QWidget):
    """A casino chip.  ``selected`` draws the XP style pressed-in look."""

    clicked = Signal(int)

    def __init__(self, value: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.value = value
        self._hover = False
        self._selected = False
        self.setFixedSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Bet ${value:,}")

    def setSelected(self, on: bool) -> None:
        if self._selected != on:
            self._selected = on
            self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.value)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        face, mark = CHIP_COLOURS.get(self.value, ("#E9E4D6", "#333333"))
        base = QColor(face)
        if not self.isEnabled():
            base = QColor("#DAD7CE")
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)

        shadow = QRectF(rect).translated(0, 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawEllipse(shadow)

        gradient = chip_gradient(rect)
        painter.setBrush(base)
        painter.drawEllipse(rect)
        painter.setBrush(gradient)
        painter.drawEllipse(rect)

        mark_colour = QColor(mark)
        if not self.isEnabled():
            mark_colour = QColor("#9B978C")
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(8):
            painter.save()
            painter.translate(rect.center())
            painter.rotate(i * 45)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(mark_colour)
            painter.drawRoundedRect(
                QRectF(rect.width() / 2 - 8, -2.2, 9.0, 4.4), 2.2, 2.2
            )
            painter.restore()

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(mark_colour, 1.4))
        painter.drawEllipse(rect.adjusted(9, 9, -9, -9))
        if self._hover:
            painter.setPen(QPen(QColor(255, 255, 255, 150), 1.6))
            painter.drawEllipse(rect.adjusted(1.5, 1.5, -1.5, -1.5))

        painter.setPen(QPen(mark_colour))
        painter.setFont(xp.ui_font(11, bold=True))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                         f"{self.value:,}")

        if self._selected:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 210), 2))
            painter.drawEllipse(rect.adjusted(-2, -2, 2, 2))
        painter.end()


def chip_gradient(rect: QRectF) -> QRadialGradient:
    """Domed plastic look: highlight up and left, shade around the rim."""
    focus = QPointF(
        rect.center().x() - rect.width() * 0.18,
        rect.center().y() - rect.height() * 0.18,
    )
    gradient = QRadialGradient(focus, rect.width() * 0.72)
    gradient.setColorAt(0.00, QColor(255, 255, 255, 150))
    gradient.setColorAt(0.30, QColor(255, 255, 255, 45))
    gradient.setColorAt(0.70, QColor(0, 0, 0, 30))
    gradient.setColorAt(1.00, QColor(0, 0, 0, 85))
    return gradient


# --------------------------------------------------------------------------
# sunken panel
# --------------------------------------------------------------------------
class SunkenPanel(QWidget):
    """Flat BTNFACE group box with a sunken well, used by the side rail."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), xp.BTNFACE)
        top = 17
        well = QRectF(5, top, self.width() - 10, self.height() - top - 6)
        xp.draw_sunken(painter, well, QColor(255, 255, 255))
        if self._title:
            painter.setFont(xp.ui_font(8, bold=True))
            painter.setPen(QPen(xp.QColor(60, 60, 50)))
            painter.drawText(
                QRectF(8, 1, self.width() - 16, 15),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self._title.upper(),
            )
            painter.setPen(QPen(xp.BTNHILIGHT))
            painter.drawLine(8, 16, self.width() - 9, 16)
        painter.end()


class XPStatusBar(QWidget):
    """The two pane status bar along the bottom of the window."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.panes = ["", "", ""]
        self.setFixedHeight(24)

    def set_panes(self, *texts: str) -> None:
        self.panes = list(texts) + [""] * (3 - len(texts))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), xp.BTNFACE)
        painter.setPen(QPen(xp.BTNHILIGHT))
        painter.drawLine(0, 0, self.width(), 0)
        painter.setPen(QPen(xp.BTNLIGHT))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        widths = [0.52, 0.26]
        x = 3
        painter.setFont(xp.ui_font(8))
        for index, fraction in enumerate(widths):
            width = int(self.width() * fraction) - 6
            if width <= 0:
                break
            well = QRectF(x, 3, width, self.height() - 7)
            xp.draw_sunken(painter, well, xp.BTNFACE)
            painter.setPen(QPen(xp.QColor(30, 30, 20)))
            painter.drawText(
                well.adjusted(6, 0, -6, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.panes[index],
            )
            x += width + 6
        painter.end()