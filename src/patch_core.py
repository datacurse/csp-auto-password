"""Install and remove the de-itzmx proxy payload into a CSP paint folder."""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from common import csp_is_running, stop_csp
from paths import proxy_payload_dir
from state import clear_state, load_state, save_state
from version import (
    PATCH_MARKER_FILES,
    PATCH_SIDEcar_FILES,
    PROXY_STEM,
    REQUIRED_AFTER_PATCH,
    payload_available,
)

# Fresh CSP (itzmx build) does not ship SHFolder.dll in the install folder.
# Our patch is purely additive — virgin restore means deleting every file we add.
PATCH_ADDED_FILES: tuple[str, ...] = PATCH_SIDEcar_FILES


@dataclass
class PatchStatus:
    install_dir: Path | None
    patched: bool
    partial: bool
    missing: tuple[str, ...]
    extra: tuple[str, ...]
    broken_proxy: bool = False


def paint_dir_files(install_dir: Path) -> dict[str, Path]:
    return {name: install_dir / name for name in PATCH_SIDEcar_FILES}


def _is_our_proxy(dll_path: Path) -> bool:
    """True if SHFolder.dll is our forwarding proxy (not CSP/native)."""
    if not dll_path.is_file():
        return False
    try:
        data = dll_path.read_bytes()
    except OSError:
        return False
    return b"SHFolder_orig" in data or b"deitzmx_anchor" in data


def _restore_shfolder(install_dir: Path) -> None:
    """Return SHFolder.dll to the pre-patch install-dir state."""
    real = install_dir / f"{PROXY_STEM}.dll"
    backup = install_dir / f"{PROXY_STEM}.dll.itzmx-backup"
    state = load_state()
    had_native = bool(state.get("had_native_shfolder"))

    if backup.is_file():
        if _is_our_proxy(backup):
            # Corrupt backup from an older bug — virgin had no local SHFolder.
            backup.unlink(missing_ok=True)
            real.unlink(missing_ok=True)
        else:
            shutil.copy2(backup, real)
            backup.unlink(missing_ok=True)
        return

    if had_native and real.is_file() and not _is_our_proxy(real):
        # Replaced a rare pre-existing SHFolder; no backup left — leave as-is.
        return

    # Default CSP: additive shadow only — remove SHFolder.dll entirely.
    real.unlink(missing_ok=True)


def inspect_install(install_dir: Path | None) -> PatchStatus:
    if install_dir is None or not install_dir.is_dir():
        return PatchStatus(None, False, False, PATCH_MARKER_FILES, (), False)

    present = [name for name in PATCH_MARKER_FILES if (install_dir / name).is_file()]
    missing = tuple(n for n in PATCH_MARKER_FILES if n not in present)
    patched = len(missing) == 0
    partial = bool(present) and not patched

    extra: list[str] = []
    backup = install_dir / f"{PROXY_STEM}.dll.itzmx-backup"
    if backup.is_file():
        extra.append(backup.name)

    proxy = install_dir / f"{PROXY_STEM}.dll"
    broken_proxy = False
    if not patched:
        if _is_our_proxy(proxy):
            partial = True
            broken_proxy = True
            missing = (f"{PROXY_STEM}.dll",)
        elif proxy.is_file() and not load_state().get("had_native_shfolder"):
            # Leftover from a bad unpatch (e.g. copied System32 SHFolder).
            partial = True
            broken_proxy = True
            missing = (f"{PROXY_STEM}.dll",)

    return PatchStatus(install_dir, patched, partial, missing, tuple(extra), broken_proxy)


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def apply_patch(install_dir: Path, csp_version: str) -> None:
    if not payload_available(csp_version):
        raise RuntimeError(f"payload_missing:{csp_version}")

    staged = proxy_payload_dir(csp_version)
    if csp_is_running():
        stop_csp()
        time.sleep(2)

    real = install_dir / f"{PROXY_STEM}.dll"
    backup = install_dir / f"{PROXY_STEM}.dll.itzmx-backup"
    had_native = real.is_file() and not _is_our_proxy(real)
    if had_native and not backup.is_file():
        shutil.copy2(real, backup)

    errors: list[str] = []
    for name in PATCH_SIDEcar_FILES:
        src = staged / name
        dst = install_dir / name
        if not src.is_file():
            if name in REQUIRED_AFTER_PATCH:
                errors.append(name)
            continue
        try:
            _copy_file(src, dst)
        except OSError as exc:
            if name in REQUIRED_AFTER_PATCH:
                errors.append(f"{name} ({exc})")

    status = inspect_install(install_dir)
    if status.missing or errors:
        detail = ", ".join(errors or status.missing)
        raise RuntimeError(f"deploy_incomplete:{detail}")

    save_state(
        csp_version=csp_version,
        install_dir=install_dir,
        patched=True,
        had_native_shfolder=had_native,
    )


def remove_patch(install_dir: Path, csp_version: str) -> None:
    if csp_is_running():
        stop_csp()
        time.sleep(2)

    _restore_shfolder(install_dir)

    for name in PATCH_MARKER_FILES:
        path = install_dir / name
        if path.is_file():
            path.unlink(missing_ok=True)

    backup = install_dir / f"{PROXY_STEM}.dll.itzmx-backup"
    backup.unlink(missing_ok=True)

    clear_state()
    save_state(
        csp_version=csp_version,
        install_dir=install_dir,
        patched=False,
        had_native_shfolder=False,
    )
