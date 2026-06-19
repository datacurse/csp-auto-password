# Log detailed info for every visible CSP window during startup.
$ErrorActionPreference = "Continue"
$log = Join-Path $PSScriptRoot "output\splash_probe.txt"
"=== splash probe $(Get-Date -Format o) ===" | Set-Content $log

Add-Type @"
using System;using System.Text;using System.Runtime.InteropServices;
public class W {
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f,IntPtr l);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out RECT r);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
 public delegate bool EnumProc(IntPtr h,IntPtr l);
}
"@

function Get-CspPids {
  $ids=@{}
  Get-Process CLIPStudioPaint -ErrorAction SilentlyContinue | ForEach-Object { $ids[[uint32]$_.Id]=$true }
  return $ids
}

function Snapshot($pids) {
  $lines = New-Object System.Collections.Generic.List[string]
  $cb=[W+EnumProc]{ param($h,$l)
    $op=0;[W]::GetWindowThreadProcessId($h,[ref]$op)|Out-Null
    if(-not $pids.ContainsKey([uint32]$op) -or -not [W]::IsWindowVisible($h)){ return $true }
    $t=New-Object Text.StringBuilder 400;[W]::GetWindowTextW($h,$t,400)|Out-Null
    $c=New-Object Text.StringBuilder 200;[W]::GetClassNameW($h,$c,200)|Out-Null
    $r=New-Object W+RECT; [W]::GetWindowRect($h,[ref]$r)|Out-Null
    $w=$r.R-$r.L; $hgt=$r.B-$r.T
    $lines.Add("class=$($c) title=$($t) rect=${w}x${hgt} hwnd=$($h.ToInt64())")
    return $true }
  [W]::EnumWindows($cb,[IntPtr]::Zero)|Out-Null
  return ,$lines.ToArray()
}

Get-Process CLIPStudioPaint -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500

try { Set-Date -Adjust (New-TimeSpan -Days 1) | Out-Null } catch {}

$exe="C:\Program Files\CELSYS\CLIP STUDIO 1.5\CLIP STUDIO PAINT\CLIPStudioPaint.exe"
$proc=Start-Process $exe -PassThru
"launched pid=$($proc.Id)" | Add-Content $log

$t0=Get-Date
for($i=0;$i -lt 80;$i++){
  Start-Sleep -Milliseconds 100
  $pids=Get-CspPids
  if($pids.Count -eq 0){ continue }
  $ms=[int]((Get-Date)-$t0).TotalMilliseconds
  $snap=Snapshot $pids
  if($snap.Count -gt 0){
    "+${ms}ms" | Add-Content $log
    $snap | Add-Content $log
  }
}

Get-Process CLIPStudioPaint -ErrorAction SilentlyContinue | Stop-Process -Force
try { Set-Date -Adjust (New-TimeSpan -Days -1) | Out-Null } catch {}
"=== end $(Get-Date -Format o) ===" | Add-Content $log
