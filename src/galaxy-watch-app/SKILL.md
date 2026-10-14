---
name: galaxy-watch-app
description: >-
  Build, install and QA Wear OS apps for a Samsung Galaxy Watch (proven on Galaxy Watch 7, Wear OS 6 / One UI 8
  Watch) from a Windows PC - Kotlin + Compose for Wear OS, sideloaded over adb Wireless debugging, no Android
  Studio. Use this skill for ANY request that touches the watch - a new watch app, a watch face, a complication
  or tile, changing an existing watch app, reading watch settings, screenshots or logs from the watch, or "does
  the watch support X" - even when the user just says "השעון", "השעון שלי", "גלקסי ווטש", "Galaxy Watch", "Wear
  OS", "אפליקציה לשעון", "תתקין על השעון", "תצלם את השעון". It carries the toolchain setup, a ready project
  template, the adb pairing/permission scripts, the Wear OS traps that cost hours (ambient timeouts, screen
  wake-ups, non-ASCII build paths) and the on-device QA recipes. Not for phone (Android mobile) apps, not for
  Apple Watch / watchOS, not for Samsung Health data analysis.
---

# Galaxy Watch app (Wear OS) - build, install, QA

Everything here was proven while building a real full-screen watch app (a Shabbat-mode
clock) on a Galaxy Watch 7. Reuse it instead of rediscovering: the first project cost
~4 hours, most of it on traps listed in `references/`.

## Reference setup (verified)

| | |
|---|---|
| Watch | Samsung Galaxy Watch 7 40mm (SM-L310), 480×480 round, 340 dpi. Other Galaxy Watches on Wear OS 5+ behave the same way; check with `getprop` |
| OS | **Wear OS 6** = Android 16, SDK **36**, One UI 8 Watch |
| adb | Wireless debugging over the home Wi-Fi: `adb connect <watch-ip>:<port>` (the port changes after reboot / toggling Wireless debugging - ask the user for the current one) |
| JDK | Temurin 17, portable zip under `%USERPROFILE%\.jdk\jdk-17*` (`scripts/install.ps1` finds it there) |
| SDK | `%LOCALAPPDATA%\Android\Sdk` - platform-tools (adb), platforms;android-34, build-tools;34.0.0, cmdline-tools |
| Build | Gradle 8.11.1 wrapper, AGP 8.7.3, Kotlin 2.1.0, Compose BOM 2024.12, wear-compose 1.4.0, minSdk 34 |
| No | Android Studio, no emulator (the real watch is the test device), no Play Store |

Fonts on the watch include `SamsungColorEmoji.ttf` and `NotoColorEmoji.ttf` - emoji render.
Hebrew renders correctly, RTL layout works in Compose.

## Workflow

### 0. First run on a new PC
Check `java -version` / `%USERPROFILE%\.jdk`, `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe`.
Anything missing: install it as described in `references/toolchain.md` (portable JDK zip,
`sdkmanager` packages, licenses). Ask the user once for the watch IP and ports
(Settings → Developer options → Wireless debugging).

### 1. Scaffold a new project (do not hand-write Gradle files)
```powershell
powershell -File "$env:USERPROFILE\.claude\skills\galaxy-watch-app\scripts\new-project.ps1" `
  -Dir "<project folder>" -Package com.example.<slug> -AppName "<app name>"
```
The template (`assets/template/`) is a proven skeleton: version catalog, wrapper,
`gradle.properties` with `android.overridePathCheck=true`, root `build.gradle.kts` that sends
build outputs to `%LOCALAPPDATA%\<rootProject.name>-build` (required for non-ASCII folders -
see `references/toolchain.md`), a Wear theme with swipe-to-dismiss disabled, launcher icon,
and a minimal `MainActivity` + `HomeScreen` (Scaffold + ScalingLazyColumn + Chip).
Then `git init` and commit.

### 2. Build
```bash
export JAVA_HOME="$(ls -d "$USERPROFILE"/.jdk/jdk-17* | head -1)"
./gradlew.bat assembleDebug testDebugUnitTest lintDebug --no-daemon --console=plain 2>&1 | grep -E "^e: |BUILD|Lint found|tests completed"
```
APK lands in `%LOCALAPPDATA%\<rootProject.name>-build\app\outputs\apk\debug\app-debug.apk`,
test XML in `...\app\test-results\testDebugUnitTest\`, lint in `...\app\reports\`.
Build errors you will meet and their one-line fixes: `references/toolchain.md`.

### 3. Connect, install, grant
```powershell
.\scripts\watch-connect.ps1 -Ip <watch-ip> -Port <port> [-PairPort <p> -Code <6 digits>]   # pairing only the first time
.\scripts\install.ps1                                                                     # build + adb install -r + launch
.\scripts\watch-grant.ps1 -Package com.example.<slug>                                      # once per app (survives reinstall)
```
`watch-grant.ps1` grants what a sideloaded app cannot ask for itself: `WRITE_SECURE_SETTINGS`
(`pm grant`), DND policy access (`cmd notification allow_dnd`), `SYSTEM_ALERT_WINDOW` and
`WRITE_SETTINGS` app-ops, `POST_NOTIFICATIONS`. Only grant what the app declares.
Two adb transports appear after pairing (IP and mDNS) - `adb disconnect` the mDNS one or set
`ANDROID_SERIAL=<watch-ip>:<port>`; otherwise every command fails with "more than one device".

### 4. QA on the device - use the recipes, not guesses
`references/device-qa.md` has the exact commands: screenshots (and why a tap 15 s after a
screenshot silently misses), reading the top activity / display state / DND / alarms /
services, diffing system settings before-after, a debug-only intent hook for timed tests,
and logcat filters. Verify each claim on the watch before reporting it done.

### 5. Wear OS behaviour that is not in the docs
Read `references/wear-os-gotchas.md` before designing anything that stays on screen, runs in
the background, changes system settings, or wakes the screen. Headlines:
- An app in ambient mode is bounced to the watch face after **20 s** unless it has an
  **OngoingActivity** (`androidx.wear:wear-ongoing`) on its foreground-service notification.
- `android:turnScreenOn` + a "relaunch if hidden" service = the screen wakes every minute in
  doze. Relaunch only while `PowerManager.isInteractive`.
- Samsung turns the always-on display **off when the watch is off-wrist** (`reason=offbody`).
  On the table, ambient screenshots are black - that is not a bug.
- A coroutine started from `rememberCoroutineScope()` dies when the composable leaves the
  screen - long transitions belong in an app-level scope with `NonCancellable`.
- Background activity launches from a service work only with the `SYSTEM_ALERT_WINDOW`
  app-op (`BAL_ALLOW_SAW_PERMISSION` in logcat proves it).
- Wake-gesture / AOD settings keys that exist on the Galaxy Watch 7 are listed there (verified).

## Building blocks that worked (write them in this shape)
| Need | Shape |
|---|---|
| Ambient-capable full-screen activity that swallows touch | `AmbientLifecycleObserver` + a full-screen Compose root that consumes pointer input |
| Foreground service that keeps the app on screen | `specialUse` foreground service + `OngoingActivity`, relaunch only while interactive |
| Read/write/snapshot/restore system settings | one gateway class over `Settings.System/Secure/Global`, snapshot before, restore after |
| DND on/off | `NotificationManager.setInterruptionFilter` after policy access is granted |
| Exact alarm | `USE_EXACT_ALARM` + `AlarmManager.setExactAndAllowWhileIdle` |
| State that survives reboot | DataStore preferences + a `BOOT_COMPLETED` receiver |
| Zmanim / Hebrew calendar | `com.kosherjava:zmanim:2.5.0` (pure Java) |

## Preferences
Ask the user once per project for the design style and the language of the UI, and record
the answer in the project. Hebrew UI: `values/strings.xml` in Hebrew, `values-en` English,
RTL by default. Keep files under 500 lines and functions under 30 - split `ui/`, `mode/`,
`clock/` style.

## Reporting
State plainly what was verified on the watch and what was not (e.g. reboot, battery, on-wrist
ambient). A green build is not a working watch app; a screenshot from the device is.
