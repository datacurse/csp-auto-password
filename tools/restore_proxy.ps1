# Restore CSP install folder to pre-patch (virgin itzmx) state. Run elevated.
# Fresh CSP does NOT ship SHFolder.dll locally — our patch is purely additive.
# Uninstall = delete every file we added; do not leave SHFolder.dll behind.
param([string]$Stem = "SHFolder")
$ErrorActionPreference = "Stop"

$Install = "C:\Program Files\CELSYS\CLIP STUDIO 1.5\CLIP STUDIO PAINT"
$real   = Join-Path $Install "$Stem.dll"
$backup = Join-Path $Install "$Stem.dll.itzmx-backup"

function Test-OurProxy([string]$Path) {
    if (-not (Test-Path $Path)) { return $false }
    try {
        $text = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($Path))
        return ($text -match 'SHFolder_orig') -or ($text -match 'deitzmx_anchor')
    } catch { return $false }
}

if (Test-Path $backup) {
    if (Test-OurProxy $backup) {
        Remove-Item $backup -Force
        if (Test-Path $real) { Remove-Item $real -Force }
        Write-Output "Removed corrupt proxy backup and $Stem.dll"
    } else {
        Copy-Item $backup $real -Force
        Remove-Item $backup -Force
        Write-Output "Restored original $Stem.dll from backup"
    }
} elseif (Test-Path $real) {
    Remove-Item $real -Force
    Write-Output "Removed additive shadow $Stem.dll (virgin CSP has no local copy)"
}

foreach ($f in @("$Stem`_orig.dll","deitzmx.dll","deitzmx.config","deitzmx_hook.js")) {
    $p = Join-Path $Install $f
    if (Test-Path $p) { Remove-Item $p -Force; Write-Output "Removed $f" }
}
Write-Output "DONE"
