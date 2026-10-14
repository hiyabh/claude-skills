# Wear OS 6 / One UI 8 Watch behaviour learned on the device

Each item below was observed in logcat on a Galaxy Watch 7 (SM-L310) on 2026-09-27, not read in docs.

## Staying on screen
- **Ambient mode for an activity** works with `AmbientLifecycleObserver(activity, callback)`
  (`androidx.wear:wear`) added to `lifecycle`. Callbacks: `onEnterAmbient`, `onUpdateAmbient`
  (once a minute), `onExitAmbient`. Do NOT hold `FLAG_KEEP_SCREEN_ON` if you want ambient; let the
  15 s `screen_off_timeout` move the system to doze.
- **20-second bounce**: `AmbientTaskStackManager` logs `Auto-resume task ... |no-ongoing|`, starts a
  timer and after ~20 s `doLaunchHomeActivity` returns to the watch face. `wear_activity_auto_resume_timeout_ms`
  is 60000 globally. Fix: make the app's foreground-service notification an **OngoingActivity**
  (`androidx.wear:wear-ongoing`). Afterwards the log shows `|ongoing` and the task is kept.
- **"Show last app" timer bounces even an ongoing app (found 2026-10-07, after a real Shabbat)**:
  `AmbientTaskStackManager` keeps an "auto-resume task" candidate per ambient session. If an activity is
  launched while the session is already BEGINNING (e.g. started while dozing), the candidate stays the
  *previous* task ("grace period for recently changed task"), its timer runs out and
  `doLaunchHomeActivity` puts the watch face over your activity - in doze, with nobody to notice.
  The timer is `global wear_activity_auto_resume_timeout_ms` when it differs from the default
  (log: `Google timeout has been changed. Use it <ms>`), otherwise Samsung's
  `global setting_show_last_app_within_time` (seconds; UI offers 20/120/3600 only). Writing a value
  longer than the session (e.g. 96 h) is honoured. Snapshot and restore both.
- **Launching an activity while dozing wakes the screen**, even without `turnScreenOn`:
  `Waking up from Dozing (WAKE_REASON_APPLICATION, details=displayoffload: updateTopActivity while controlling)`.
  A watchdog therefore cannot repair a lost activity in doze silently - prevent the loss instead.
- **Auto brightness** (`system screen_brightness_mode=1`) follows the light sensor in ambient too:
  covered by a sleeve = dim, uncovered = bright. Set 0 (manual) for a fixed screen.
- **Off-body AOD policy**: `AmbientDream: Early exit timeout, reason=offbody` - Samsung turns the
  doze screen OFF when the watch is not worn. Ambient looks black on a table; on the wrist it stays
  dim. Do not chase this as a bug; test on-wrist.
- **`android:turnScreenOn="true"` is a trap**: any relaunch of the activity (even bringing an
  existing singleTask instance forward) wakes the display (`WAKE_REASON_APPLICATION ...
  handleTurnScreenOn`). Combined with a "relaunch when hidden" watchdog it woke the screen every
  minute in doze, because the activity's `onStop` fires when the display dozes too. Rules:
  no `turnScreenOn`; the watchdog relaunches only if `PowerManager.isInteractive`.
- **Background activity start from a service** is denied on Android 14+ unless exempt. Granting
  the `SYSTEM_ALERT_WINDOW` app-op via adb (`appops set <pkg> SYSTEM_ALERT_WINDOW allow`) is enough:
  logcat then shows `START ... (BAL_ALLOW_SAW_PERMISSION)`. The Home button cannot be intercepted;
  relaunch within a few seconds is the best available behaviour.
- Kiosk-like screen: theme `android:windowSwipeToDismiss=false` (disables the swipe-right dismiss)
  and `dispatchTouchEvent(ev) = true` in the activity to swallow touches. The system shade
  (swipe from top) cannot be blocked by an app.

## Background work
- Foreground service on Android 14+: `foregroundServiceType="specialUse"` +
  `<property android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE" .../>` +
  `FOREGROUND_SERVICE_SPECIAL_USE` permission; `startForeground(id, notif, FOREGROUND_SERVICE_TYPE_SPECIAL_USE)`.
  Sideloaded apps are allowed. `LifecycleService` + `lifecycleScope` for the loop.
- Exact alarms: declare `USE_EXACT_ALARM` (granted automatically for targetSdk 33+), then
  `setExactAndAllowWhileIdle`. Verify with `dumpsys alarm | grep <pkg>` (`*walarm*` entry with `OW=`),
  and after cancel the history shows `Reason=alarm_cancelled`.
- Receivers: `BOOT_COMPLETED` for resume-after-reboot; use `goAsync()` + a coroutine.
- A non-exported receiver cannot be triggered from `adb shell am broadcast` (`run-as` fails too).
  For timed QA add a debug-only intent extra on the launcher activity (`BuildConfig.DEBUG` guarded):
  `am start -n <pkg>/.MainActivity --el debug_auto_off_seconds 90`.
- **Coroutine scope trap**: a state transition launched from `rememberCoroutineScope()` in the
  composable that shows the button is cancelled the moment persisted state flips and the composable
  leaves composition - the transition silently stops half-way. Run transitions in an app-level
  `CoroutineScope(SupervisorJob() + Dispatchers.Default)` wrapped in `withContext(NonCancellable)`,
  with logging.
- **Idempotent activation**: if "activate" can run while already active (reinstall, debug hook,
  double tap), snapshot the original settings only on the first activation - otherwise
  deactivation restores the overridden values. Keep the guard service restart-safe:
  on app open, if state is active, start the service again.

## System settings (require `WRITE_SECURE_SETTINGS` via `pm grant`)
Keys that exist on this watch (`settings list global|secure|system`), verified by writing them:

| Namespace | Key | Meaning | Default |
|---|---|---|---|
| global | `ambient_enabled` | Always-on display | 1 |
| global | `ambient_tilt_to_wake` | Raise wrist to wake | 1 |
| global | `ambient_touch_to_wake` | Touch to wake | 1 |
| global | `ambient_tilt_to_bright` | Tilt to bright in ambient | 0 |
| global | `psm_ambient_tilt_to_wake` | Same, power-saving profile | 1 |
| global | `setting_wake_by_turning_bezel` | Samsung: bezel turn wakes | 1 |
| global | `theater_mode_on`, `setting_theater_mode_on`, `setting_bedtime_mode_*` | Samsung modes (not used) | 0 |
| global | `zen_mode` | DND state (read-only view; set via NotificationManager) | 0 |
| secure | `wake_gesture_enabled` | Lift-to-wake (AOSP) | 1 |
| secure | `double_tap_to_wake` | Double tap | 1 |
| system | `screen_off_timeout` | Interactive timeout ms | 15000 |

Discovery method for other keys: `scripts/discover-settings.ps1 -Snapshot before`, toggle one
thing in the watch UI, `-Snapshot after -DiffAgainst before`.

DND: `NotificationManager.setInterruptionFilter(INTERRUPTION_FILTER_NONE)` after
`cmd notification allow_dnd <pkg>` (the Wear settings UI has no policy-access screen; `list_dnd`
does not exist on this build - verify with `dumpsys notification | grep mZenMode`). Restore with
the previous filter; `UNKNOWN` → `ALL`. Shell escape hatch: `cmd notification set_dnd off`.

## Not possible from a third-party app (stop looking)
- Turning off Samsung Health sensors (steps, heart rate) - no API; only the user can pause steps.
- Bluetooth / airplane toggling (Android 13+ blocks third-party apps; broadcast is protected).
- Blocking the hardware Home button or the top-swipe shade.
- Device-owner tricks - provisioning needs a factory reset without accounts.

## UI details
- Emoji: `Paint().hasGlyph()` answers for ONE glyph. Probing `"🕯️🕯️"` returns false even though
  `SamsungColorEmoji.ttf` has the candle; probe a single `"🕯️"`.
- `ScalingLazyColumn` from `androidx.wear.compose.foundation.lazy`; `Chip`, `ToggleChip`,
  `RadioButton`, `Scaffold`, `TimeText` from `androidx.wear.compose.material`. A round 480 px
  screen fits ~5 text lines around a 60 sp clock; keep the bottom line above y≈400.
- `adb shell input swipe` on a Compose list is sometimes interpreted as a click on the chip under
  the finger - screenshot before assuming which screen you are on.
