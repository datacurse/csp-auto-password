"""Frozen vs dev paths for bundled proxy payloads and user data."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN = getattr(sys, "frozen", False)

APP_NAME = "deitzmx-patch"
USER_DATA = Path.home() / "AppData" / "Local" / APP_NAME
SETTINGS_FILE = USER_DATA / "settings.json"
STATE_FILE = USER_DATA / "state.json"


def repo_root() -> Path:
    if FROZEN:
        return Path(sys.executable).resolve().parent
    return REPO_ROOT


def bundle_root() -> Path:
    if FROZEN and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return REPO_ROOT


def versions_dir() -> Path:
    return bundle_root() / "versions"


def proxy_payload_dir(csp_version: str) -> Path:
    return versions_dir() / csp_version / "proxy"
