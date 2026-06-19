# De-itzmx patch — how it works (success write-up)

This document describes the **working baked-in patch** for CLIP Studio Paint v4.2.0
Patch1 (itzmx build). After deploy, you launch CSP normally — desktop icon, Start
menu, double-click the exe — and land on the canvas without the daily password,
without the itzmx splash, and without tamper/marketing pop-ups.

For build/deploy commands see [tools/README.md](tools/README.md). For the old
pywinauto launcher see [README.md](README.md).

---

## What you get

| Before patch | After patch |
|--------------|-------------|
| Daily password dialog (`Application requires password to start`) | Auto-filled invisibly in the background |
| Full-screen itzmx splash (anime + `BBS.ITZMX.COM` banner) | Hidden before you notice it |
| Chinese tamper / anti-resale message boxes | Auto-dismissed |
| Random itzmx document pop-ups via `ShellExecuteW` | Blocked |
| External Python launcher each time | Not needed |

The password and splash are **once per calendar day** on an unpatched install. On
days when CSP would not prompt, the patch is effectively invisible — it just
starts faster and cleaner.

---

## Architecture (30-second version)

```
CLIPStudioPaint.exe          ← never modified (protector checks exe integrity)
  │
  └─► SHFolder.dll           ← tiny proxy dropped in the CSP install folder
        ├─ forwards SHGetFolderPathA/W → SHFolder_orig.dll (real System32 DLL)
        └─ DllMain → worker thread (250 ms delay)
              └─ LoadLibrary("deitzmx.dll")     ← frida-gadget, renamed
                    └─ reads deitzmx.config
                          └─ runs deitzmx_hook.js  ← copy of tools/frida_deitzmx.js
```

**Why this shape:** the itzmx protector exits immediately (code 1) if you edit
`CLIPStudioPaint.exe` or inject into it too early. Shadowing an early-loaded
system DLL (`SHFolder.dll`, not in Windows KnownDLLs) lets us load Frida ~350 ms
after process start — early enough for the password (~2.2 s) and splash (~0.6 s),
late enough to avoid tripping anti-tamper.

---

## What the hook script does

Source: `tools/frida_deitzmx.js` → deployed as `deitzmx_hook.js`.

All changes are **Win32 UI hooks only**. Memory patches inside the encrypted exe
were tried and consistently triggered the Chinese “do not tamper with language
files” warning.

### 1. Daily password

On prompt days, itzmx shows a dialog titled `Application requires password to start`.

The hook:

1. Finds the dialog by title (`FindWindowW`).
2. **Hides it** with `ShowWindow(SW_HIDE)` — never brings it to the foreground.
3. Recursively finds the nested `Edit` control (`EnumChildWindows`).
4. Pastes the daily password via clipboard + `WM_PASTE` (the method the patch
   author expects; fast `WM_SETTEXT` is penalized in itzmx update #33).
5. Clicks OK (`BM_CLICK`) or sends Enter.

A 100 ms timer retries until the dialog is gone.

### 2. Splash screen

The itzmx splash is **not** a normal IE window. Measured at runtime it is:

| Window | Class | Title | Size (typical) |
|--------|-------|-------|----------------|
| Full-screen splash | `Window` | *(empty)* | ~1024×576 |
| Marketing overlay | `742DEA58-…-6571DDC4-…` | *(empty)* | ~512×314 |

The hook hides these by intercepting:

- `ShowWindow` — redirect show → `SW_HIDE` for matching windows
- `SetWindowPos` — strip `SWP_SHOWWINDOW` for matching windows
- `SetForegroundWindow` — block for matching windows
- A short startup sweep (`EnumWindows`, ~12 s) as a safety net

It also zeroes `Sleep(1000–6000)` calls so the splash timer does not stall startup.

**Important:** we only **hide** splash windows. Sending `WM_CLOSE` to them was
tested and **breaks launch** — itzmx treats that as aborting startup.

### 3. Tamper warnings and marketing

- `MessageBoxW/A`, `DialogBox*`, `CreateDialog*` — return `IDOK` when title/text
  matches itzmx / Chinese tamper strings.
- `ShellExecuteW` — blank out paths that match itzmx marketing URLs.

---

## Files in the CSP install folder

All five are required. If any are missing, behavior degrades silently or obviously:

| File | Required | Role |
|------|----------|------|
| `SHFolder.dll` | yes | Proxy; loads the gadget after 250 ms |
| `SHFolder_orig.dll` | yes | Real System32 SHFolder (forward target) |
| `deitzmx.dll` | yes | frida-gadget (~23 MB) |
| `deitzmx.config` | **yes** | Points gadget at the hook script |
| `deitzmx_hook.js` | **yes** | Runtime suppression logic |

**Common failure:** deploy copies `deitzmx.dll` and `SHFolder.dll` but skips
`deitzmx.config` and `deitzmx_hook.js` when CSP is still running and DLLs are
locked. The gadget loads but **runs no hooks** — you see the full password +
splash exactly as in an unpatched session.

`deploy_proxy.ps1` now kills CSP first, deploys the hook payload before the
proxy DLLs, and reports `DEPLOY INCOMPLETE` if required files are missing.

---

## GUI installer (recommended for end users)

One exe bundles the five patch files and a Russian CustomTkinter UI (same style as
[csp-lang-switch](https://github.com/datacurse/csp-lang-switch)):

- **Version combo** — `5.0.0` and `4.2.0` (only versions with bundled payloads)
- **Установить патч** / **Удалить патч** — install or remove the proxy payload
- **Status** — detects CSP install, shows whether the patch is active
- **Saved state** — `%LOCALAPPDATA%\deitzmx-patch\state.json` and `settings.json`

Build the installer:

```powershell
pip install -r requirements.txt
build_installer.bat
```

Output: `dist\csp-password-patch.exe`. Run once; confirm UAC when prompted.

Dev run without building exe:

```powershell
python tools\stage_version_payload.py --rebuild
python src\main.py
```

---

## Deploy manually (elevated)

Close CSP completely (including system tray), then:

```powershell
pip install lief
python tools\build_proxy.py --target SHFolder --source-dir C:\Windows\System32
powershell -Verb RunAs -ExecutionPolicy Bypass -File tools\deploy_proxy.ps1 -Stem SHFolder
```

Verify all five files exist under:

`C:\Program Files\CELSYS\CLIP STUDIO 1.5\CLIP STUDIO PAINT\`

If deploy warns about locked files, quit CSP, reboot if needed, and re-run deploy.

### Hook-only update

After editing `tools/frida_deitzmx.js`:

```powershell
python tools\build_proxy.py --target SHFolder --source-dir C:\Windows\System32
powershell -Verb RunAs -ExecutionPolicy Bypass -File tools\_deploy_hook.ps1
```

Or re-run full `deploy_proxy.ps1`.

### Uninstall

Virgin itzmx CSP **does not ship `SHFolder.dll`** in the install folder — our patch is
purely additive (five new files). Uninstall must **delete** those files entirely;
copying System32 `SHFolder.dll` into the folder or leaving the proxy behind breaks
CSP startup. Inspect baseline with `tools\probe_install.ps1`.

```powershell
powershell -Verb RunAs -ExecutionPolicy Bypass -File tools\restore_proxy.ps1 -Stem SHFolder
```

CSP returns to stock itzmx behavior (password + splash).

---

## Verify it works

On a day when you already authenticated, you will not see the password dialog.
To force a prompt day (elevated — advances system clock +1 day, then restores it):

```powershell
powershell -Verb RunAs -ExecutionPolicy Bypass -File tools\verify_clock.ps1
```

Check `tools/output/verify_timeline.txt`. Success looks like:

```
+2545 ms  APPEAR  742DEA58-…|CLIP STUDIO PAINT
proc_alive=True
```

No `Application requires password to start`, no `Window|` splash line.

Window timeline probe (optional):

```powershell
powershell -Verb RunAs -ExecutionPolicy Bypass -File tools\probe_splash.ps1
```

Output: `tools/output/splash_probe.txt`

---

## Debugging notes (what we learned the hard way)

### Partial deploy → hooks never run

Symptom: password dialog and splash visible; patch files “look” installed.

Cause: `deitzmx.config` / `deitzmx_hook.js` missing while `deitzmx.dll` present.

Fix: ensure all five files; redeploy with CSP fully quit.

### CSP exits immediately (code 1)

Causes we hit:

| Change | Result |
|--------|--------|
| `WM_CLOSE` on splash windows | Process aborts — do not use |
| Hiding all GUID-suffixed CSP internal windows | Breaks Qt init — only hide the known popup suffix |
| Hiding every untitled `Window` class | Too broad — restrict to large splash (~900×500+) |
| `LOAD_DELAY_MS = 0` | Occasionally tripped protector — keep **250 ms** |

Stable rule: **hide, never close** splash; **narrow** window matching; **250 ms**
gadget delay.

### Visible password autofill

Early versions called `SetForegroundWindow` before paste, flashing the dialog.
Current hook hides the dialog first and never foregrounds it.

### Splash mistaken for IE

README originally described an embedded IE browser + 3–4 s sleep. Sleep bypass
helps, but the visible splash is a native `Window` class fullscreen surface.
IE-class hooks alone are not enough.

---

## Target build

| Item | Value |
|------|-------|
| Exe | `CLIPStudioPaint.exe` |
| SHA256 | `868BBC5637563E68BD98220AD1D4EE3A5B7FDEADDCED1C368E7141014C3653CB` |
| Install path | `C:\Program Files\CELSYS\CLIP STUDIO 1.5\CLIP STUDIO PAINT\` |

---

## Repo map

| Path | Purpose |
|------|---------|
| `tools/frida_deitzmx.js` | Hook source |
| `tools/native/deitzmx_helper.c` | Proxy DLL source |
| `tools/build_proxy.py` | Build + stage payload |
| `tools/deploy_proxy.ps1` | Install patch (elevated) |
| `tools/restore_proxy.ps1` | Remove patch |
| `tools/verify_clock.ps1` | Force password day test |
| `tools/probe_splash.ps1` | Window timeline during startup |
| `src/main.py` | GUI installer entry (CustomTkinter, Russian) |
| `deitzmx-patch.spec` | PyInstaller spec for `dist/csp-password-patch.exe` |
| `build_installer.bat` | Stage payload + build installer exe |
| `auto_password_simple.py` | Legacy external launcher (prefer patch) |

---

## Caveats

- **CSP reinstall/update** may delete patch files — re-run deploy.
- **Antivirus** may flag DLL shadowing or frida-gadget.
- **Do not edit `CLIPStudioPaint.exe`** — integrity check kills the process.
- **Fallback proxy targets** if `SHFolder` conflicts: `msimg32`, `uxtheme`,
  `dwmapi` (same `build_proxy.py --target …`).
