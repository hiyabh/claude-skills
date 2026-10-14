# One-time grants a sideloaded watch app cannot request itself. Grant only what the app declares.
# Usage: .\watch-grant.ps1 -Package com.example.myapp [-SecureSettings] [-Dnd] [-Overlay] [-WriteSettings] [-Notifications]
# With no switches, everything is granted (the full set a kiosk-style app needs).
param(
    [Parameter(Mandatory = $true)][string]$Package,
    [switch]$SecureSettings,
    [switch]$Dnd,
    [switch]$Overlay,
    [switch]$WriteSettings,
    [switch]$Notifications
)
$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
$all = -not ($SecureSettings -or $Dnd -or $Overlay -or $WriteSettings -or $Notifications)

if ($all -or $SecureSettings) {
    Write-Host "== WRITE_SECURE_SETTINGS (system settings such as wake gestures / AOD) =="
    & $adb shell pm grant $Package android.permission.WRITE_SECURE_SETTINGS
}
if ($all -or $Dnd) {
    Write-Host "== Notification policy access (do not disturb) =="
    & $adb shell cmd notification allow_dnd $Package
}
if ($all -or $Overlay) {
    Write-Host "== SYSTEM_ALERT_WINDOW app-op (background activity launches from a service) =="
    & $adb shell appops set $Package SYSTEM_ALERT_WINDOW allow
}
if ($all -or $WriteSettings) {
    Write-Host "== WRITE_SETTINGS app-op (system namespace, e.g. screen timeout) =="
    & $adb shell appops set $Package WRITE_SETTINGS allow
}
if ($all -or $Notifications) {
    Write-Host "== POST_NOTIFICATIONS =="
    & $adb shell pm grant $Package android.permission.POST_NOTIFICATIONS
}

Write-Host "== Verify =="
& $adb shell dumpsys package $Package | Select-String "WRITE_SECURE_SETTINGS|POST_NOTIFICATIONS"
& $adb shell appops get $Package SYSTEM_ALERT_WINDOW
& $adb shell appops get $Package WRITE_SETTINGS
Write-Host "(DND access has no listing command on this build - the app's isNotificationPolicyAccessGranted tells)"
