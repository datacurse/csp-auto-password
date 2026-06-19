"""Persist patch state and user settings."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from paths import SETTINGS_FILE, STATE_FILE


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_settings() -> dict:
    return _load_json(SETTINGS_FILE)


def save_csp_version(version: str) -> None:
    data = load_settings()
    data["csp_version"] = version
    _save_json(SETTINGS_FILE, data)


def load_csp_version(default: str) -> str:
    data = load_settings()
    ver = data.get("csp_version")
    return str(ver) if ver else default


def load_state() -> dict:
    return _load_json(STATE_FILE)


def save_state(
    *,
    csp_version: str,
    install_dir: Path,
    patched: bool,
    had_native_shfolder: bool | None = None,
) -> None:
    data = {
        "version": 1,
        "csp_version": csp_version,
        "install_dir": str(install_dir),
        "patched": patched,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if had_native_shfolder is not None:
        data["had_native_shfolder"] = had_native_shfolder
    _save_json(STATE_FILE, data)


def clear_state() -> None:
    if STATE_FILE.is_file():
        try:
            STATE_FILE.unlink()
        except OSError:
            pass
