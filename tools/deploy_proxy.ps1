# Deploy the search-order-proxy payload (run elevated). Exe is left untouched.
param([string]$Stem = "SHFolder")
$ErrorActionPreference = "Continue"
try { Start-Transcript -Path (Join-Path $PSScriptRoot "output\deploy_log.txt") -Force | Out-Null } catch {}

$Install = "C:\Program Files\CELSYS\CLIP STUDIO 1.5\CLIP STUDIO PAINT"
$Staged  = Join-Path $PSScriptRoot "output\proxy"

Get-Process CLIPStudioPaint -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$real   = Join-Path $Install "$Stem.dll"
$backup = Join-Path $Install "$Stem.dll.itzmx-backup"

if (Test-Path $real) {
    if (-not (Test-Path $backup)) {
        Copy-Item $real $backup -Force
        Write-Output "Backed up existing $Stem.dll -> $backup"
    } else {
        Write-Output "Backup already exists -> $backup (left untouched)"
    }
} else {
    Write-Output "No existing $Stem.dll in install dir -> pure additive shadow (no backup needed)"
}

function Deploy-File($src, $dst, [switch]$Required) {
    if (-not (Test-Path $src)) {
        Write-Output "MISSING staged file: $src"
        if ($Required) { $script:failed = $true }
        return
    }
    try {
        Copy-Item $src $dst -Force
        Write-Output "Deployed $(Split-Path $dst -Leaf)"
    } catch {
        Write-Output "WARN copy failed $(Split-Path $dst -Leaf): $($_.Exception.Message)"
        if ($Required) { $script:failed = $true }
    }
}

$failed = $false

# Hook payload first — without these the gadget runs but does nothing.
foreach ($f in @("deitzmx.dll", "deitzmx.config", "deitzmx_hook.js")) {
    Deploy-File (Join-Path $Staged $f) (Join-Path $Install $f) -Required
}

Deploy-File (Join-Path $Staged "$Stem`_orig.dll") (Join-Path $Install "$Stem`_orig.dll")
Deploy-File (Join-Path $Staged "$Stem.dll") $real -Required

foreach ($req in @("deitzmx.config", "deitzmx_hook.js", "$Stem.dll")) {
    $p = Join-Path $Install $req
    if (-not (Test-Path $p)) {
        Write-Output "ERROR required file missing after deploy: $req"
        $failed = $true
    }
}

if ($failed) {
    Write-Output "DEPLOY INCOMPLETE"
    exit 1
}
Write-Output "DONE"
try { Stop-Transcript | Out-Null } catch {}
