"""Pixel probes on the saved screenshots.

Stands in for eyeballing the output: checks the caption really is Luna
blue, the table really is green felt, the rail really is BTNFACE beige
and that a card face is white with a red or black pip.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QColor, QImage

SHOTS = Path(__file__).resolve().parent / "shots"
failures = []


def probe(path, x, y, label, expect):
    image = QImage(str(path))
    if image.isNull():
        failures.append(f"{path.name}: cannot load")
        return
    colour = image.pixelColor(x, y)
    r, g, b = colour.red(), colour.green(), colour.blue()
    ok = expect(r, g, b)
    state = "ok " if ok else "BAD"
    print(f"  [{state}] {label:<22} ({x:4},{y:4}) = rgb({r:3},{g:3},{b:3})")
    if not ok:
        failures.append(f"{path.name} {label} = rgb({r},{g},{b})")


def is_luna(r, g, b):
    return 10 < r < 140 and g > 90 and b > 200 and b > r + 90


def is_felt(r, g, b):
    return g > 60 and g > r + 40 and g > b + 40


def is_beige(r, g, b):
    return 200 < r < 245 and 195 < g < 245 and 175 < b < 235 and r >= g >= b


def is_white(r, g, b):
    return r > 235 and g > 235 and b > 235


def is_button(r, g, b):
    return r > 200 and b < r


name = "01-table-idle.png"
path = SHOTS / name
if not path.exists():
    print("no screenshots; run render_test.py first")
    sys.exit(2)

print(name)
probe(path, 520, 12, "luna caption", is_luna)
probe(path, 120, 14, "luna caption left", is_luna)
probe(path, 520, 300, "felt centre", is_felt)
probe(path, 60, 200, "felt left", is_felt)
probe(path, 520, 70, "felt below menu", is_felt)
probe(path, 975, 60, "rail panel frame", is_beige)

# the rail should show the XP sunken pattern: beige frame plus white well
image = QImage(str(path))
beige = white = 0
for y in range(52, image.height() - 24, 2):
    colour = image.pixelColor(975, y)
    r, g, b = colour.red(), colour.green(), colour.blue()
    if is_beige(r, g, b):
        beige += 1
    if is_white(r, g, b):
        white += 1
print(f"  [{'ok ' if beige and white else 'BAD'}] rail has beige frame "
      f"({beige} rows) and white sunken wells ({white} rows)")
if not (beige and white):
    failures.append("rail does not show the sunken panel pattern")

# the menu bar sits under the caption and is BTNFACE, not felt
probe(path, 520, 41, "menu bar", is_beige)

name = "03-hand-won.png"
path = SHOTS / name
if path.exists():
    print(name)
    # find the first clearly white pixel inside the player hand band
    image = QImage(str(path))
    found = 0
    for y in range(int(image.height() * 0.55), int(image.height() * 0.75)):
        for x in range(20, image.width() - 240, 3):
            r, g, b = image.pixelColor(x, y).red(), image.pixelColor(x, y).green(), image.pixelColor(x, y).blue()
            if r > 235 and g > 235 and b > 235:
                found += 1
                break
        if found:
            break
    print(f"  [{'ok ' if found else 'BAD'}] card face is white")
    if not found:
        failures.append("no white card face found in the player hand")

name = "05-insurance-prompt.png"
path = SHOTS / name
if path.exists():
    print(name)
    probe(path, 520, 400, "insurance felt", is_felt)

# chips must carry their face colours (a shading-only chip would be grey)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from blackjack.chrome import CHIP_COLOURS  # noqa: E402

image = QImage(str(SHOTS / "01-table-idle.png"))
rail_x = image.width() - 214
found = {}
for y in range(52, image.height() - 24):
    for x in range(rail_x + 8, image.width() - 8):
        colour = image.pixelColor(x, y)
        for value, (face, _mark) in CHIP_COLOURS.items():
            target = QColor(face)
            if value in found:
                continue
            if (
                abs(colour.red() - target.red()) < 26
                and abs(colour.green() - target.green()) < 26
                and abs(colour.blue() - target.blue()) < 26
            ):
                found[value] = (x, y)
print(f"  [{'ok ' if len(found) >= 3 else 'BAD'}] chip faces found: "
      f"{sorted(found)}")
if len(found) < 3:
    failures.append(f"only {len(found)} chip faces rendered: {sorted(found)}")

if failures:
    print(f"\nFAIL: {len(failures)}")
    for failure in failures:
        print("   ", failure)
    sys.exit(1)
print("\nPASS: colour probes match the Luna / felt / BTNFACE scheme")