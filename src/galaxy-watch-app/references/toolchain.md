# Toolchain on a Windows PC (verified 2026-09-27)

## Installed pieces
| Piece | Where | Notes |
|---|---|---|
| JDK 17 (Temurin 17.0.20.1) | `%USERPROFILE%\.jdk\jdk-17.0.20.1+1` | Portable zip. `winget install` of Temurin **hangs on a UAC prompt** (`consent.exe`) in a non-interactive session - never use winget for JDKs here. Zip source: `https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk` |
| Android SDK | `%LOCALAPPDATA%\Android\Sdk` | `cmdline-tools\latest\bin\sdkmanager.bat --sdk_root=<sdk> "platform-tools" "platforms;android-34" "build-tools;34.0.0"`; licenses accepted with `yes \| sdkmanager --licenses` |
| adb | `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe` | Not on PATH - use the full path or `$ADB` |
| Env | `JAVA_HOME`, `ANDROID_HOME` set with `setx` | New terminals see them; the Claude Bash tool often does not - export explicitly |
| Gradle | wrapper 8.11.1 in the template | `--no-daemon --console=plain` keeps output parseable |

Bash tool snippet that always works:
```bash
export JAVA_HOME="$(ls -d "$USERPROFILE"/.jdk/jdk-17* | head -1)"
ADB="$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe"; export ANDROID_SERIAL="<watch-ip>:<port>"
```

## Build traps and fixes (each cost a rebuild)

1. **Hebrew (non-ASCII) project path.** AGP refuses to configure: add
   `android.overridePathCheck=true` to `gradle.properties` (template has it). Then
   `assembleDebug` works but **unit tests fail with `ClassNotFoundException`** for every test
   class - Gradle's Windows test worker cannot load a classpath containing the Hebrew path.
   Junctions do not help (Gradle canonicalises). Moving the folder is not an option while VS Code
   has it open. Fix that works: root `build.gradle.kts` redirects **all build outputs** to an
   ASCII dir:
   ```kotlin
   val asciiBuildRoot: File? = System.getenv("LOCALAPPDATA")?.let { File(it, "${rootProject.name}-build") }
   allprojects { if (asciiBuildRoot != null) layout.buildDirectory.set(File(asciiBuildRoot, project.name)) }
   ```
   Consequence: APK, test results and lint reports live under `%LOCALAPPDATA%\<name>-build\app\...`,
   never under `app/build`. Scripts must use that path.
2. **`local.properties`**: write `sdk.dir=C:/Users/<you>/AppData/Local/Android/Sdk` with forward
   slashes. `C\:\Users\...` is mis-unescaped by Java Properties (`\U` → `U`) and yields
   "The filename, directory name, or volume label syntax is incorrect".
3. **Version catalog aliases in Kotlin DSL**: `libs.core-ktx` parses as `libs.core - ktx`
   (a subtraction). Use `libs.core.ktx`, `libs.wear.compose.material`, etc.
4. **`androidx.core:core-ktx` 1.15+ requires compileSdk 35.** With compileSdk 34 pin
   `core-ktx = 1.13.1` (template does). Alternatively install `platforms;android-35`.
5. **Lint false positive** `InvalidFragmentVersionForActivityResult` when using
   `registerForActivityResult` without Fragments - disabled in the template's `lint {}` block
   together with the version-nag checks (`GradleDependency`, `AndroidGradlePluginVersion`).
6. **Remaining lint warnings that are intentional in watch apps**: `WearBackNavigation`
   (swipe-to-dismiss disabled on purpose for a kiosk-like screen), `WearRecents`
   (`FLAG_ACTIVITY_NEW_TASK` needed when launching from a service), `MissingPermission` on
   exact alarms (we declare `USE_EXACT_ALARM`).
7. **`minSdk 34`** matches the watch and removes `InlinedApi`/`ObsoleteSdkInt` noise
   (`FOREGROUND_SERVICE_TYPE_SPECIAL_USE`, `mipmap-anydpi-v26`).
8. **Python heredocs writing Kotlin**: a `"\uD83D"` inside a Python string is a surrogate escape
   and crashes the write (and can truncate the file). Write files with emoji via the Write tool.
9. **Git Bash mangles `/system/...` arguments** passed to `adb shell` (MSYS path conversion):
   prefix with `MSYS_NO_PATHCONV=1` or quote the whole shell command.

## Dependency policy that held up
- `androidx.wear:wear` (AmbientLifecycleObserver), `androidx.wear:wear-ongoing` (OngoingActivity),
  `androidx.wear.compose:compose-material` + `compose-foundation`, `activity-compose`,
  `lifecycle-runtime-compose` + `lifecycle-service`, `datastore-preferences`, coroutines. Nothing else
  was needed for a full app.
- Calendar/zmanim: `com.kosherjava:zmanim:2.5.0` (LGPL 2.1, pure Java). Hebrew-date display alone
  needs no library - a tested `HebrewDate.kt` is ~120 lines.
