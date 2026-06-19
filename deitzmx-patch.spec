# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for deitzmx-patch.exe (Russian GUI installer).

Build:
  python tools/stage_version_payload.py --rebuild
  pyinstaller deitzmx-patch.spec

Output: dist/csp-password-patch.exe
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

_ctk_datas, _ctk_binaries, _ctk_hidden = collect_all("customtkinter")

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=_ctk_binaries,
    datas=_ctk_datas,
    hiddenimports=[
        "gui",
        "gui_i18n",
        "common",
        "patch_core",
        "state",
        "version",
        "paths",
        "customtkinter",
        "tkinter",
        "tkinter.messagebox",
        *_ctk_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

versions = Path("versions")
if versions.is_dir():
    for ver_dir in sorted(versions.iterdir()):
        proxy = ver_dir / "proxy"
        if proxy.is_dir():
            for f in proxy.iterdir():
                if f.is_file():
                    dest = f"versions/{ver_dir.name}/proxy/{f.name}"
                    a.datas.append((dest, str(f), "DATA"))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="csp-password-patch",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
    icon=None,
)
