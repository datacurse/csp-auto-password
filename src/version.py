"""Supported CSP versions and bundled patch availability."""

from __future__ import annotations

from pathlib import Path

from paths import proxy_payload_dir

# Shown in the version combo (future releases listed up front).
SUPPORTED_VERSIONS: tuple[str, ...] = ("5.0.0", "4.2.0")

DEFAULT_VERSION = "5.0.0"
PROXY_STEM = "SHFolder"

# Files copied by apply_patch (includes SHFolder.dll proxy replacement).
PATCH_SIDEcar_FILES: tuple[str, ...] = (
    "deitzmx.dll",
    "deitzmx.config",
    "deitzmx_hook.js",
    f"{PROXY_STEM}_orig.dll",
    f"{PROXY_STEM}.dll",
)

# Files that only exist when our patch was applied. SHFolder.dll is excluded —
# CSP ships a native copy, so counting it causes false "partial install" reports.
PATCH_MARKER_FILES: tuple[str, ...] = (
    "deitzmx.dll",
    "deitzmx.config",
    "deitzmx_hook.js",
    f"{PROXY_STEM}_orig.dll",
)

REQUIRED_AFTER_PATCH: tuple[str, ...] = (
    "deitzmx.dll",
    "deitzmx.config",
    "deitzmx_hook.js",
    f"{PROXY_STEM}.dll",
)


def payload_available(csp_version: str) -> bool:
    staged = proxy_payload_dir(csp_version)
    if not staged.is_dir():
        return False
    for name in REQUIRED_AFTER_PATCH:
        if not (staged / name).is_file():
            return False
    return True


def available_versions() -> tuple[str, ...]:
    return tuple(v for v in SUPPORTED_VERSIONS if payload_available(v))
