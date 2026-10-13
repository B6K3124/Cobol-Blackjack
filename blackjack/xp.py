"""Windows XP theme constants and painters.

Everything visual lives here: the Luna blue caption, the 3D edge colours,
the Tahoma type ramp and the Solitaire felt.  The palette is sampled from
the Luna colour scheme so the game reads as period-correct rather than
"a dark modern UI with rounded corners".
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QRadialGradient,
)

# --------------------------------------------------------------------------
# system colours (COLOR_* of the Luna scheme)
# --------------------------------------------------------------------------
BTNFACE = QColor("#ECE9D8")
BTNTEXT = QColor("#000000")
BTNHILIGHT = QColor("#FFFFFF")
BTNSHADOW = QColor("#808080")
BTNLIGHT = QColor("#D4D0C8")
BTNDARK = QColor("#716F64")
GRAYTEXT = QColor("#808080")
HIGHLIGHT = QColor("#0A246A")
HIGHLIGHTTEXT = QColor("#FFFFFF")
WINDOW = QColor("#FFFFFF")
WINDOWTEXT = QColor("#000000")
MENU = QColor("#ECE9D8")
INFO = QColor("#FFFFE1")

EDGE_LIGHT = QColor("#FFFFFF")
EDGE_HILIGHT = QColor("#DFDFDF")
EDGE_SHADOW = QColor("#A0A0A0")
EDGE_DKSHADOW = QColor("#808080")

# --------------------------------------------------------------------------
# Luna blue caption
# --------------------------------------------------------------------------
LUNA_TOP = QColor("#0B4FC0")
LUNA_MID = QColor("#1C74DE")
LUNA_BOTTOM = QColor("#3A93FF")
LUNA_HIGHLIGHT = QColor("#8FC6FF")
LUNA_EDGE = QColor("#002A78")
LUNA_TEXT = QColor("#FFFFFF")
LUNA_SHADOW = QColor("#0A3E92")

CAPTION_INACTIVE_TOP = QColor("#7FA9D9")
CAPTION_INACTIVE_BOTTOM = QColor("#BBD5EE")
CAPTION_INACTIVE_EDGE = QColor("#5E7FA8")

# --------------------------------------------------------------------------
# playing table
# --------------------------------------------------------------------------
FELT_CENTRE = QColor("#0B8B12")
FELT_EDGE = QColor("#03540A")

CARD_RED = QColor("#C81414")
CARD_BLACK = QColor("#101010")
CARD_EDGE = QColor("#7A7A7A")
CARD_FACE = QColor("#FDFDFD")

BACK_FILL = QColor("#1D3F94")
BACK_PATTERN = QColor("#7FA8E8")
BACK_BORDER = QColor("#071C4C")

# suit glyphs - the engine sends H/D/C/S
SUIT_GLYPH = {"H": "\u2665", "D": "\u2666", "C": "\u2663", "S": "\u2660"}
RED_SUITS = {"H", "D"}
SUIT_NAME = {"H": "Hearts", "D": "Diamonds", "C": "Clubs", "S": "Spades"}


def suit_colour(suit: str) -> QColor:
    return CARD_RED if suit in RED_SUITS else CARD_BLACK


# --------------------------------------------------------------------------
# fonts - Tahoma was the XP UI face; card indices are drawn bold
# --------------------------------------------------------------------------
def ui_font(size: int = 8, bold: bool = False, italic: bool = False) -> QFont:
    font = QFont("Tahoma")
    font.setPointSize(size)
    font.setBold(bold)
    font.setItalic(italic)
    return font


def suit_font(pixel_size: int) -> QFont:
    font = QFont("Segoe UI Symbol")
    font.setPixelSize(pixel_size)
    return font


def caption_font() -> QFont:
    font = QFont("Trebuchet MS")
    font.setPixelSize(19)
    font.setBold(True)
    return font


# --------------------------------------------------------------------------
# gradients
# --------------------------------------------------------------------------
def luna_gradient(rect: QRectF, active: bool = True) -> QLinearGradient:
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    if active:
        gradient.setColorAt(0.00, LUNA_TOP)
        gradient.setColorAt(0.08, LUNA_MID)
        gradient.setColorAt(0.55, LUNA_MID)
        gradient.setColorAt(0.92, LUNA_BOTTOM)
        gradient.setColorAt(1.00, LUNA_HIGHLIGHT)
    else:
        gradient.setColorAt(0.00, CAPTION_INACTIVE_TOP)
        gradient.setColorAt(0.90, CAPTION_INACTIVE_BOTTOM)
        gradient.setColorAt(1.00, CAPTION_INACTIVE_TOP)
    return gradient


def felt_gradient(rect: QRectF) -> QRadialGradient:
    centre = QPointF(rect.center().x(), rect.center().y() * 0.94)
    radius = max(rect.width(), rect.height()) * 0.78
    gradient = QRadialGradient(centre, radius)
    gradient.setColorAt(0.00, FELT_CENTRE)
    gradient.setColorAt(0.55, QColor("#078210"))
    gradient.setColorAt(1.00, FELT_EDGE)
    return gradient


def button_gradient(rect: QRectF, pressed: bool) -> QLinearGradient:
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    if pressed:
        gradient.setColorAt(0.0, QColor("#C8C3B4"))
        gradient.setColorAt(1.0, QColor("#E6E2D6"))
    else:
        gradient.setColorAt(0.00, QColor("#FDFDFB"))
        gradient.setColorAt(0.45, QColor("#F3F0E8"))
        gradient.setColorAt(0.50, QColor("#EAE6DA"))
        gradient.setColorAt(1.00, QColor("#D6D1C2"))
    return gradient


# --------------------------------------------------------------------------
# 3D edge helpers - the classic sunken/raised four pixel border
# --------------------------------------------------------------------------
def draw_sunken(painter: QPainter, rect: QRectF, face: QColor, bevel: int = 1) -> None:
    """Two pixel sunken well used by list boxes, panels and the status bar."""
    painter.fillRect(rect, face)
    painter.setPen(EDGE_DKSHADOW)
    painter.drawLine(rect.topLeft(), rect.topRight())
    painter.drawLine(rect.topLeft(), rect.bottomLeft())
    painter.setPen(EDGE_HILIGHT)
    painter.drawLine(rect.topRight(), rect.bottomRight())
    painter.drawLine(rect.bottomLeft(), rect.bottomRight())
    if bevel > 1:
        inner = rect.adjusted(1, 1, -1, -1)
        painter.setPen(EDGE_SHADOW)
        painter.drawLine(inner.topLeft(), inner.topRight())
        painter.drawLine(inner.topLeft(), inner.bottomLeft())
        painter.setPen(EDGE_LIGHT)
        painter.drawLine(inner.topRight(), inner.bottomRight())
        painter.drawLine(inner.bottomLeft(), inner.bottomRight())


def draw_raised(painter: QPainter, rect: QRectF, face: QColor) -> None:
    painter.fillRect(rect, face)
    painter.setPen(EDGE_LIGHT)
    painter.drawLine(rect.topLeft(), rect.topRight())
    painter.drawLine(rect.topLeft(), rect.bottomLeft())
    painter.setPen(EDGE_HILIGHT)
    painter.drawLine(rect.topRight(), rect.bottomRight())
    painter.drawLine(rect.bottomLeft(), rect.bottomRight())


def draw_rounded_sunken(
    painter: QPainter, rect: QRectF, face: QColor, radius: float = 3.0
) -> None:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    painter.fillPath(path, face)
    painter.setPen(EDGE_DKSHADOW)
    painter.drawPath(path)


# --------------------------------------------------------------------------
# global stylesheet
# --------------------------------------------------------------------------
def stylesheet() -> str:
    return f"""
    QWidget {{
        font-family: "Tahoma";
        font-size: 11px;
    }}
    QMenuBar {{
        background-color: rgb({MENU.red()}, {MENU.green()}, {MENU.blue()});
        border-bottom: 1px solid rgb({BTNLIGHT.red()}, {BTNLIGHT.green()},
                                     {BTNLIGHT.blue()});
        padding: 1px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 3px 8px;
        color: rgb(0, 0, 0);
    }}
    QMenuBar::item:selected {{
        background: rgb({HIGHLIGHT.red()}, {HIGHLIGHT.green()},
                        {HIGHLIGHT.blue()});
        color: rgb(255, 255, 255);
    }}
    QMenu {{
        background-color: rgb({MENU.red()}, {MENU.green()}, {MENU.blue()});
        border: 1px solid rgb({BTNSHADOW.red()}, {BTNSHADOW.green()},
                              {BTNSHADOW.blue()});
    }}
    QMenu::item {{
        padding: 4px 26px 4px 24px;
        color: rgb(0, 0, 0);
    }}
    QMenu::item:selected {{
        background: rgb({HIGHLIGHT.red()}, {HIGHLIGHT.green()},
                        {HIGHLIGHT.blue()});
        color: rgb(255, 255, 255);
    }}
    QMenu::item:disabled {{
        color: rgb(128, 128, 128);
    }}
    QMenu::separator {{
        height: 1px;
        background: rgb({BTNLIGHT.red()}, {BTNLIGHT.green()}, {BTNLIGHT.blue()});
        margin: 3px 2px;
    }}
    QToolTip {{
        background-color: rgb({INFO.red()}, {INFO.green()}, {INFO.blue()});
        color: rgb(0, 0, 0);
        border: 1px solid rgb(0, 0, 0);
    }}
    """


def centre_text(painter: QPainter, rect: QRectF, text: str) -> None:
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)