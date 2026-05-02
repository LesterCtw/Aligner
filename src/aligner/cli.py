from __future__ import annotations

import argparse
import importlib.util

from aligner import __version__
from aligner.app import run_gui


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aligner")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("gui", help="Launch the PySide6 desktop UI.")
    subparsers.add_parser("probe", help="Check whether core runtime dependencies are importable.")
    return parser


def probe() -> int:
    modules = ["numpy", "scipy", "tifffile", "PySide6"]
    missing = [name for name in modules if importlib.util.find_spec(name) is None]
    if missing:
        print("Missing:", ", ".join(missing))
        return 1
    print("Core dependencies available.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "probe":
        return probe()
    if args.command == "gui":
        return run_gui()

    parser.print_help()
    return 0

