# Builds the debug APK of the project in the current directory (or -Project) and installs it.
# Build outputs live under %LOCALAPPDATA%\<rootProject.name>-build (see references/toolchain.md).
param(
    [string]$Project = (Get-Location).Path,
    [string]$Serial = ""
)
$ErrorActionPreference = "Stop"
$adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
if (-not $env:JAVA_HOME) {
    $jdk = Get-ChildItem "$env:USERPROFILE\.jdk" -Directory -Filter "jdk-17*" | Select-Object -First 1
    if ($jdk) { $env:JAVA_HOME = $jdk.FullName }
}
if ($Serial -ne "") { $env:ANDROID_SERIAL = $Serial }

$settings = Get-Content (Join-Path $Project "settings.gradle.kts") -Raw
if ($settings -notmatch 'rootProject\.name\s*=\s*"([^"]+)"') { throw "rootProject.name not found in settings.gradle.kts" }
$slug = $Matches[1]
$apk = Join-Path $env:LOCALAPPDATA "$slug-build\app\outputs\apk\debug\app-debug.apk"

$manifest = Get-Content (Join-Path $Project "app\build.gradle.kts") -Raw
$pkg = if ($manifest -match 'applicationId\s*=\s*"([^"]+)"') { $Matches[1] } else { "" }

Push-Location $Project
try {
    & .\gradlew.bat assembleDebug --no-daemon --console=plain
    if ($LASTEXITCODE -ne 0) { throw "Gradle build failed" }
    & $adb install -r $apk
    if ($LASTEXITCODE -ne 0) { throw "adb install failed - is the watch connected? (scripts/watch-connect.ps1)" }
    if ($pkg -ne "") { & $adb shell am start -n "$pkg/.MainActivity" }
} finally {
    Pop-Location
}
