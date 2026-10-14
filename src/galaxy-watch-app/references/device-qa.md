# Device access and QA recipes (Galaxy Watch)

`ADB="$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe"`, `export ANDROID_SERIAL="<watch-ip>:<port>"`.

## Connecting
1. First time only (or after "forget"): the user opens Developer options → Wireless debugging →
   *Pair new device* and sends the **pairing** `IP:port` + 6-digit code (they expire in minutes).
   The port on the Wireless-debugging main screen is the **connect** port and is different -
   `adb mdns services` shows it as `_adb-tls-connect._tcp`.
   `adb pair IP:PAIRPORT CODE` then `adb connect IP:PORT`.
2. Later: `adb connect <watch-ip>:<port>` only. "failed to connect" = wrong port or Wireless
   debugging turned itself off (it does after reboot) - ask for the current port.
3. After pairing, two transports show in `adb devices -l` (IP and mDNS). Disconnect one or set
   `ANDROID_SERIAL`; if the mDNS transport is the survivor, commands may suddenly fail with
   "device not found" - reconnect over IP.
4. Device facts: `getprop ro.product.model ro.build.version.sdk ro.build.version.release`.
5. **`device offline` / connect timeout (10060)** after the watch has been idle on the table for a
   while: its Wi-Fi went to sleep. `adb disconnect` then `adb connect` again; if that still times
   out, the watch must be woken (press the side button / put it on) or Wireless debugging re-enabled.
   Plan device work in one stretch rather than leaving the watch idle between steps.

6. **adb keeps dropping as soon as the display dozes**: Galaxy Watch Wi-Fi in "Auto" turns itself off
   while the phone is connected over Bluetooth. Ask the user to set Wi-Fi → "Always on" for the session
   (and back afterwards). Work around short drops with an on-watch monitor:
   `adb shell 'nohup sh /data/local/tmp/mon.sh > /data/local/tmp/mon.log 2>&1 &'`, then read the log.
   From Git Bash set `MSYS_NO_PATHCONV=1`, or `/data/...` arguments are rewritten to `C:/Program Files/Git/...`.
7. Shell `am start` cannot start a non-exported activity (SecurityException) - launch the exported
   launcher activity, or the app's own debug hook.

8. **Never use `monkey` to launch an app on a real device** (`monkey -p <pkg> -c LAUNCHER 1`): besides
   the launch it injects random events, and one of them is a rotation event that leaves
   `system accelerometer_rotation=1` - the whole watch UI then rotates with the wrist. Happened on
   a real watch. Launch with `am start -n <pkg>/<activity>` (find it with
   `cmd package resolve-activity --brief <pkg>`). Repair: `cmd window user-rotation lock 0`.

## The 15-second trap
`screen_off_timeout` is 15000 and with `ambient_touch_to_wake=0` a tap does not wake. Every
`input tap` issued more than ~15 s after the last wake hits a black screen and silently does
nothing. Pattern that works:
```bash
"$ADB" shell input keyevent KEYCODE_WAKEUP; sleep 1; "$ADB" shell am start -n <pkg>/.MainActivity >/dev/null; sleep 2
"$ADB" exec-out screencap -p > "$S/pre.png"      # look BEFORE tapping
"$ADB" shell input tap 240 405; sleep 4
```
For long QA sessions set `settings put system screen_off_timeout 60000` and **restore 15000 at the
end** (it is a user-visible setting; the baseline diff must be empty).

## Screenshots
`"$ADB" exec-out screencap -p > file.png` then view with the Read tool. ~2 KB = black screen.
Layout coordinates on the 480×480 home screen: chips stack from y≈300; after two
`input swipe 240 420 240 60 300` the primary button sits around (240, 405).

## Reading state
| Question | Command |
|---|---|
| What is on top | `dumpsys activity activities \| grep -m1 topResumedActivity` |
| Display state | `dumpsys display \| grep -m1 mState=` (ON / DOZE_SUSPEND / OFF) |
| Awake? | `dumpsys power \| grep mWakefulness` |
| DND | `dumpsys notification \| grep -m1 mZenMode`; `settings get global zen_mode` |
| Service running | `dumpsys activity services <pkg> \| grep -E "ServiceRecord\|isForeground"` |
| Alarms | `dumpsys alarm \| grep -B2 -A3 <Receiver>` |
| Permissions | `dumpsys package <pkg> \| grep -E "PERMISSION: granted=true"`; `appops get <pkg> SYSTEM_ALERT_WINDOW` |
| Why the screen woke | `logcat -d \| grep -E "PowerManagerService: (Waking up\|Going to sleep)"` |
| Ambient decisions | `logcat -d \| grep -E "AmbientTaskStackManager\|AmbientTaskStateMachine\|AmbientDream"` |
| App crashes | `logcat -d \| grep -A20 AndroidRuntime` |
| Activity launches and BAL verdicts | `logcat -d \| grep "ActivityTaskManager: START"` |

`logcat -c` before a test, `logcat -d` after - the buffer is large enough for minutes.

## Settings before/after diff (proves clean restore)
```bash
D="$LOCALAPPDATA/<name>-build/settings-snapshots"; mkdir -p "$D"
for ns in global secure system; do "$ADB" shell settings list $ns | sort > "$D/baseline-$ns.txt"; done
# ... run the feature, deactivate ...
for ns in global secure system; do "$ADB" shell settings list $ns | sort > "$D/after-$ns.txt"; diff "$D/baseline-$ns.txt" "$D/after-$ns.txt" | grep -E "^[<>]" | grep -v -E "wifi|bluetooth|_time|boot_count|cache|last_|sync|stat"; done
```
An empty filtered diff after deactivation is the acceptance criterion for anything that touches
system settings.

## Timed behaviour
Sleep in the Bash tool with `sleep N` inside one command (foreground `sleep` works; give the
tool a timeout ≥ N+60 s). Poll every 10 s printing `dumpsys display` state to see doze
transitions. Compute expected auto-off instants from the app's own log line and wait past them -
a check 5 s early looks like a failure.

## Reboot caution
`adb reboot` usually turns Wireless debugging off; you then need the user to re-pair. Test reboot
paths only when he is available.

## Battery estimate
`dumpsys batterystats --reset` at start, `dumpsys batterystats` after ≥2 h on the wrist;
extrapolate to 26/50/74 h. Not yet measured.
