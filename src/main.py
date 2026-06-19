#!/usr/bin/env python3
"""de-itzmx patch installer — GUI entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python src/main.py` without installing as a package.
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import detect_installed_csp_version, find_paint_dir_optional, is_admin
from gui import run_gui
from patch_core import apply_patch, remove_patch
from version import DEFAULT_VERSION, SUPPORTED_VERSIONS


def _write_gui_error(path: str | None, message: str) -> None:
    if not path:
        return
    try:
        Path(path).write_text(message, encoding="utf-8")
    except OSError:
        pass


def cmd_patch(args: argparse.Namespace) -> int:
    paint = find_paint_dir_optional()
    if paint is None:
        _write_gui_error(args.gui_error_file, "csp_not_found")
        return 1
    ver = args.csp_version or DEFAULT_VERSION
    try:
        apply_patch(paint, ver)
        return 0
    except Exception as exc:
        _write_gui_error(args.gui_error_file, str(exc))
        return 1


def cmd_unpatch(args: argparse.Namespace) -> int:
    paint = find_paint_dir_optional()
    if paint is None:
        _write_gui_error(args.gui_error_file, "csp_not_found")
        return 1
    ver = args.csp_version or DEFAULT_VERSION
    try:
        remove_patch(paint, ver)
        return 0
    except Exception as exc:
        _write_gui_error(args.gui_error_file, str(exc))
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="de-itzmx patch installer for Clip Studio Paint")
    p.add_argument("--gui", action="store_true", help="Open the graphical installer")
    p.add_argument("--patch", action="store_true", help="Install patch (elevated)")
    p.add_argument("--unpatch", action="store_true", help="Remove patch (elevated)")
    p.add_argument("--csp-version", default=None, help="Target CSP version id")
    p.add_argument("--gui-error-file", default=None, help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.patch:
        if not is_admin():
            _write_gui_error(args.gui_error_file, "admin_required")
            return 1
        return cmd_patch(args)

    if args.unpatch:
        if not is_admin():
            _write_gui_error(args.gui_error_file, "admin_required")
            return 1
        return cmd_unpatch(args)

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
