# Wakes the watch and saves a screenshot. Usage: .\screenshot.ps1 -Out C:\path\shot.png [-NoWake]
param(
    [Parameter(Mandatory = $true)][string]$Out,
    [switch]$NoWake
)
$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not $NoWake) { & $adb shell input keyevent KEYCODE_WAKEUP; Start-Sleep -Seconds 1 }
& $adb exec-out screencap -p | Set-Content -Path $Out -Encoding Byte
if (-not (Test-Path $Out)) { Write-Host "no screenshot - is the watch connected? (adb devices)"; exit 1 }
$size = (Get-Item $Out).Length
if ($size -eq 0) { Write-Host "empty screenshot - device offline?"; exit 1 }
Write-Host "saved $Out ($size bytes)$(if ($size -lt 4000) { ' - probably a black screen' })"
