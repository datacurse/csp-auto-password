# Snapshot patch-relevant files in the CSP install folder.
# Virgin itzmx CSP (before our patch): NO SHFolder.dll, NO deitzmx.* in this folder.
param(
    [string]$Install = "C:\Program Files\CELSYS\CLIP STUDIO 1.5\CLIP STUDIO PAINT"
)

$names = @(
    "SHFolder.dll",
    "SHFolder.dll.itzmx-backup",
    "SHFolder_orig.dll",
    "deitzmx.dll",
    "deitzmx.config",
    "deitzmx_hook.js",
    "CLIPStudioPaint.exe"
)

Write-Output "Install: $Install"
Write-Output ""

foreach ($n in $names) {
    $p = Join-Path $Install $n
    if (Test-Path $p) {
        $item = Get-Item $p
        Write-Output ("{0,-28} {1,12} bytes  {2}" -f $n, $item.Length, $item.LastWriteTime)
    } else {
        Write-Output ("{0,-28} (absent)" -f $n)
    }
}

Write-Output ""
Write-Output "Virgin itzmx CSP: SHFolder.dll and deitzmx.* should all be absent."
Write-Output "Our patch adds exactly those five sidecar files (+ optional backup during install)."
