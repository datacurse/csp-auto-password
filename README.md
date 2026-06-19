# CLIP Studio Paint — de-itzmx patch

Remove the itzmx anti-resale layer from CLIP Studio Paint v4.2.0 Patch1: daily
password, website splash, tamper warnings, random pop-ups.

**Recommended:** the baked-in patch — double-click CSP normally, no external
launcher.

**Easiest install:** build or download `csp-password-patch.exe` (see [docs.md](docs.md)
→ GUI installer). Russian UI with patch/unpatch buttons and version selector.

See **[docs.md](docs.md)** for how the patch works and **[tools/README.md](tools/README.md)**
for technical history (build/deploy/uninstall via PowerShell).

```powershell
pip install lief
python tools\build_proxy.py --target SHFolder --source-dir C:\Windows\System32
powershell -Verb RunAs -ExecutionPolicy Bypass -File tools\deploy_proxy.ps1 -Stem SHFolder
```

Uninstall: `tools\restore_proxy.ps1 -Stem SHFolder` (elevated).

---

## Legacy auto-password tool

The original pywinauto-based launcher (`auto_password_simple.py`) still exists
for installs without the baked-in patch. It is detected/intermittent with itzmx
update #33; prefer the patch above.

```bat
pip install -r requirements.txt
python auto_password_simple.py
```

Build standalone exe: `build_simple.bat`
