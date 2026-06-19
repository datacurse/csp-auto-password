# Capture the full text of the itzmx password prompt (title + every child control).
# Run elevated. Patch should be REMOVED first so the dialog stays open for capture.
$ErrorActionPreference = "Continue"
$log = Join-Path $PSScriptRoot "output\password_probe.txt"
"=== password probe $(Get-Date -Format o) ===" | Set-Content $log

Add-Type @"
using System;using System.Text;using System.Runtime.InteropServices;
public class PW{
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f,IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,EnumProc f,IntPtr l);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out RECT r);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int SendMessageW(IntPtr h,int msg,IntPtr w,StringBuilder l);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
 public delegate bool EnumProc(IntPtr h,IntPtr l);
}
"@

function Get-CspPids {
  $ids=@{}
  Get-Process CLIPStudioPaint -ErrorAction SilentlyContinue | ForEach-Object { $ids[[uint32]$_.Id]=$true }
  return $ids
}

function Text($h){
  $sb=New-Object Text.StringBuilder 2048
  [PW]::GetWindowTextW($h,$sb,2048)|Out-Null
  $t=$sb.ToString()
  if([string]::IsNullOrEmpty($t)){
    # WM_GETTEXT fallback for controls that don't answer GetWindowTextW
    $sb2=New-Object Text.StringBuilder 2048
    [PW]::SendMessageW($h,0x000D,[IntPtr]2048,$sb2)|Out-Null
    $t=$sb2.ToString()
  }
  return $t
}
function Cls($h){ $sb=New-Object Text.StringBuilder 256;[PW]::GetClassNameW($h,$sb,256)|Out-Null;return $sb.ToString() }
function Rect($h){ $r=New-Object PW+RECT;[PW]::GetWindowRect($h,[ref]$r)|Out-Null;return "$($r.R-$r.L)x$($r.B-$r.T)" }

function Dump-Children($parent){
  $cb=[PW+EnumProc]{ param($h,$l)
    $c=Cls $h; $t=Text $h; $rc=Rect $h
    "    child class=$c rect=$rc text=[$t]" | Add-Content $log
    return $true }
  [PW]::EnumChildWindows($parent,$cb,[IntPtr]::Zero)|Out-Null
}

Get-Process CLIPStudioPaint -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500
try { Set-Date -Adjust (New-TimeSpan -Days 1) | Out-Null; "clock advanced" | Add-Content $log } catch { "clock err: $($_.Exception.Message)" | Add-Content $log }

$exe="C:\Program Files\CELSYS\CLIP STUDIO 1.5\CLIP STUDIO PAINT\CLIPStudioPaint.exe"
$proc=Start-Process $exe -PassThru
"launched pid=$($proc.Id)" | Add-Content $log

$captured=$false
for($i=0;$i -lt 60 -and -not $captured;$i++){
  Start-Sleep -Milliseconds 400
  $pids=Get-CspPids
  $cb=[PW+EnumProc]{ param($h,$l)
    $op=0;[PW]::GetWindowThreadProcessId($h,[ref]$op)|Out-Null
    if(-not $pids.ContainsKey([uint32]$op)){ return $true }
    $c=Cls $h; $t=Text $h; $rc=Rect $h; $vis=[PW]::IsWindowVisible($h)
    "TOP class=$c vis=$vis rect=$rc text=[$t] hwnd=$($h.ToInt64())" | Add-Content $log
    Dump-Children $h
    return $true }
  $marker="--- scan $([int]((Get-Date)-$proc.StartTime).TotalMilliseconds)ms ---"
  $marker | Add-Content $log
  [PW]::EnumWindows($cb,[IntPtr]::Zero)|Out-Null
  # stop once we've seen the password dialog a couple of times
  if((Get-Content $log -Raw) -match 'password to start'){ $captured=$true }
}

Get-Process CLIPStudioPaint -ErrorAction SilentlyContinue | Stop-Process -Force
try { Set-Date -Adjust (New-TimeSpan -Days -1) | Out-Null; "clock restored" | Add-Content $log } catch { "restore err: $($_.Exception.Message)" | Add-Content $log }
"=== end $(Get-Date -Format o) ===" | Add-Content $log
