# Connects adb to the watch over Wi-Fi.
# First time: run with -PairPort and -Code from the watch's "Pair new device" screen.
# Afterwards only -Ip and -Port (from the Wireless debugging main screen) are needed.
param(
    [Parameter(Mandatory = $true)][string]$Ip,
    [Parameter(Mandatory = $true)][int]$Port,
    [int]$PairPort = 0,
    [string]$Code = ""
)

$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) { throw "adb not found at $adb - run sdkmanager first" }

if ($PairPort -gt 0 -and $Code -ne "") {
    & $adb pair "${Ip}:${PairPort}" $Code
}
& $adb connect "${Ip}:${Port}"
& $adb devices -l
& $adb shell getprop ro.build.version.sdk
& $adb shell getprop ro.build.version.release
& $adb shell getprop ro.product.model
