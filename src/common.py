"""Windows helpers: CSP discovery, admin elevation, process checks."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CSP_PROCESS = "CLIPStudioPaint.exe"
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def is_admin() -> bool:
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def csp_is_running() -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {CSP_PROCESS}"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_CREATE_NO_WINDOW,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return CSP_PROCESS.lower() in out.lower()


def stop_csp() -> None:
    subprocess.run(
        ["taskkill", "/IM", CSP_PROCESS, "/F"],
        capture_output=True,
        creationflags=_CREATE_NO_WINDOW,
    )


def read_exe_product_version(exe: Path) -> str | None:
    if sys.platform != "win32" or not exe.is_file():
        return None
    try:
        cp = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-Item -LiteralPath '{exe}').VersionInfo.ProductVersion",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_CREATE_NO_WINDOW,
        )
        out = cp.stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def find_paint_dir_optional() -> Path | None:
    for base in (
        Path(r"C:\Program Files\CELSYS"),
        Path(r"C:\Program Files (x86)\CELSYS"),
    ):
        if not base.is_dir():
            continue
        for paint in sorted(base.glob("*/CLIP STUDIO PAINT")):
            exe = paint / CSP_PROCESS
            resource = paint / "resource"
            if exe.is_file() and (resource / "english").is_dir():
                return paint
    return None


def normalize_csp_version(product_version: str | None, supported: tuple[str, ...]) -> str | None:
    if not product_version:
        return None
    pv = product_version.strip()
    for ver in sorted(supported, reverse=True):
        if pv == ver or pv.startswith(f"{ver}."):
            return ver
    return None


def detect_installed_csp_version(supported: tuple[str, ...]) -> tuple[str | None, Path | None, str | None]:
    paint = find_paint_dir_optional()
    if paint is None:
        return None, None, None
    exe = paint / CSP_PROCESS
    product = read_exe_product_version(exe)
    return normalize_csp_version(product, supported), paint, product


def _elevated_workdir() -> Path:
    entry = Path(sys.argv[0]).resolve()
    if getattr(sys, "frozen", False):
        return entry.parent
    if entry.suffix.lower() in (".py", ".pyw") and entry.parent.name == "src":
        return entry.parent.parent
    return entry.parent


def run_elevated_sync(argv: list[str]) -> tuple[int, str]:
    if os.name != "nt":
        return 1, "Только Windows"
    executable = Path(sys.executable)
    if getattr(sys, "frozen", False):
        args = list(argv)
    else:
        args = [str(Path(sys.argv[0]).resolve()), *argv]

    err_file = Path(tempfile.gettempdir()) / "deitzmx-patch-gui-error.txt"
    try:
        err_file.unlink(missing_ok=True)
    except OSError:
        pass
    args.extend(["--gui-error-file", str(err_file)])

    exe = str(executable).replace("'", "''")
    workdir = str(_elevated_workdir()).replace("'", "''")
    arg_parts = ", ".join("'" + a.replace("'", "''") + "'" for a in args)
    ps = (
        f"$p = Start-Process -FilePath '{exe}' "
        f"-ArgumentList @({arg_parts}) "
        f"-WorkingDirectory '{workdir}' "
        f"-Verb RunAs -Wait -PassThru -WindowStyle Hidden; "
        f"if ($null -eq $p) {{ exit 1 }}; exit $p.ExitCode"
    )
    cp = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        creationflags=_CREATE_NO_WINDOW,
    )
    if cp.returncode != 0 and err_file.is_file():
        try:
            text = err_file.read_text(encoding="utf-8").strip()
            if text:
                return cp.returncode, text
        except OSError:
            pass
    return int(cp.returncode), ""
