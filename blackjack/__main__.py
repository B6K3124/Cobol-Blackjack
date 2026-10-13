"""Entry point for ``python -m blackjack``."""

import sys
from pathlib import Path

if __package__ in (None, ""):  # pragma: no cover - direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "blackjack"

from blackjack.main import main

if __name__ == "__main__":
    raise SystemExit(main())