"""Build the COBOL engine.

Prefers a native ``cobc`` when one is on PATH.  Otherwise the source is
compiled inside WSL, which is how this project is normally set up on
Windows.

    python build.py             compile with WSL
    python build.py --distro Ubuntu
    python build.py --check     compile, then start the engine once
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COBOL_DIR = ROOT / "cobol"
SOURCE = COBOL_DIR / "blackjack.cob"
BUILD_DIR = COBOL_DIR / "build"
COMPILE_FLAGS = ["-x", "-free", "-Wall"]


def wsl_path(path: Path) -> str:
    text = str(path)
    drive, _, tail = text.partition(":")
    return f"/mnt/{drive.lower()}{tail.replace('\\', '/')}"


def run(argv: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, text=True, capture_output=True, **kwargs
    )


def build_native() -> bool:
    cobc = shutil.which("cobc")
    if not cobc:
        return False
    print(f"using native cobc at {cobc}")
    result = run(
        [cobc, *COMPILE_FLAGS, "-o", str(BUILD_DIR / "blackjack.exe"), str(SOURCE)],
        cwd=str(COBOL_DIR),
    )
    print(result.stdout.strip() or result.stderr.strip())
    return result.returncode == 0


def build_in_wsl(distro: str) -> bool:
    if not shutil.which("wsl"):
        print("no native cobc and no wsl.exe on PATH", file=sys.stderr)
        print("install GnuCOBOL, or: wsl -d <distro> -- sudo apt install gnucobol",
              file=sys.stderr)
        return False

    probe = run(["wsl", "-d", distro, "--", "sh", "-lc", "command -v cobc"])
    if probe.returncode != 0 or not probe.stdout.strip():
        print(f"cobc is not installed in the {distro} WSL distribution", file=sys.stderr)
        print(f"  wsl -d {distro} -- sudo apt update && sudo apt install -y gnucobol",
              file=sys.stderr)
        return False

    command = (
        f"cd {shlex.quote(wsl_path(COBOL_DIR))} && "
        f"cobc {' '.join(COMPILE_FLAGS)} -o build/blackjack blackjack.cob"
    )
    print(f"compiling in WSL ({distro})")
    result = run(["wsl", "-d", distro, "--", "bash", "-lc", command])
    output = (result.stdout + result.stderr).strip()
    if output:
        print(output)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="compile the COBOL engine")
    parser.add_argument("--distro", default="Ubuntu-22.04",
                        help="WSL distribution that hosts cobc")
    parser.add_argument("--check", action="store_true",
                        help="start the engine once after building")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"missing source: {SOURCE}", file=sys.stderr)
        return 2
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    ok = build_native() or build_in_wsl(args.distro)
    if not ok:
        print("build failed", file=sys.stderr)
        return 1

    binary = BUILD_DIR / "blackjack.exe"
    if not binary.exists():
        binary = BUILD_DIR / "blackjack"
    print(f"built {binary} ({binary.stat().st_size:,} bytes)")

    if args.check:
        return subprocess.run([sys.executable, "-m", "blackjack", "--check"],
                              cwd=str(ROOT)).returncode
    print("run it with:  python -m blackjack")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())