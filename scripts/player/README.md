# Local player evidence harness

Run these helpers from the repository root with Python 3.13. Windows capture needs Pillow and pywin32; both were already installed on the tested host. Recording also needs ffmpeg with `libx264`; the installed 2013 build and ffprobe passed the controlled encoder test. No HTTP proxy, server, credentials or game-side controller is introduced.

This is a capture/recording and bounded input foundation. It is not a real-time autonomous planner, and it does not establish that a game is completable. The agent still observes, chooses one bounded intent and inspects its result. MCP tools remain the primary Studio interface.

## Proven versus pending

- Verified: exact-window PrintWindow PNG capture, physical-pixel metadata, PNG/pixel hashes, target ambiguity rejection, explicit crop validation, real ffmpeg encoding of one second of timed synthetic fixture frames, ffprobe frame count/duration, action validation and mocked watchdog cleanup.
- Pending runtime lease: live Client freshness after visible movement, yaw and pitch calibration, host SendInput delivery/focus, independent watchdog release after a real interrupted hold, actual gameplay recording, earned completion and replay. The helper never sets `live_client_verified` to true automatically.
- Producer preflight found MCP keyboard W hold/release works, MCP Play capture fails, and MCP mouse drag returned success without observed camera rotation. Those are supplied preflight observations, not claims established by these helper tests.

## Modes

`visual` permits only fresh player-view pixels, visible UI, the player-visible goal/controls and action history. Use a clean-context planner. No scripts, hierarchy, coordinates, hidden inventory, camera override or navigation helper. A separate observer can append the completion oracle after the attempt.

`instrumented` permits architecture and read-only diagnostics, but earned completion still requires ordinary inputs and physical passage. `regression` follows a known bounded route with checkpoints on a fixed build. Report all bypasses; a bypass invalidates completion and requires a fresh run. A control failure is not a game defect. `validate_result` checks report requirements; it cannot semantically establish victory from artifact names.

## Capture

```powershell
python -m scripts.player windows
python -m scripts.player capture --hwnd 459576 --output builds/1/captures/frame-001.png --mode instrumented --build-id ACCEPTED_BUILD --session-id RUN_SESSION --studio-id STUDIO_UUID
```

`windows` lists only visible Roblox Studio windows. A capture target must be either an exact HWND or a unique `--title-match`; ambiguous/missing targets fail. HWND/PID identity is retained throughout recording. Minimized windows fail. The capture uses the selected window DC and `PrintWindow(PW_RENDERFULLCONTENT=2)`, not a desktop rectangle; unrelated overlapping apps are excluded. The complete Studio window may still contain its own assistant/output panes. Review before sharing, or supply a calibrated crop.

Add `--crop LEFT TOP RIGHT BOTTOM` using physical pixels relative to the entire window. Bounds are exclusive at right/bottom. Recalibrate after window layout/size/DPI changes. No toolbar/pane offsets are hardcoded. The sidecar JSON contains method, UTC capture timestamp, duration, HWND/PID/title, window rect, crop, dimensions, mode/build/Studio/session and hashes. Capture requires a `.png` output and distinct JSON sidecar. Each artifact family is exclusively reserved before capture/encoder work; actual PNG/JSON/log writes also use exclusive creation. Existing evidence, reused input-result paths, competing reservations and recorder log paths are rejected. ffmpeg uses `-n` (no overwrite). Reservations are cooperative coordination files, while exclusive writes also protect against an unrelated creator racing the actual write. A leftover reservation after a crash requires producer inspection; never remove one owned by a live process.

A successful Windows capture may still be stale or show Edit UI. Under the runtime lease, compare before/after frames containing the real PlayerGui after ordinary movement and yaw/pitch. A different timestamp/hash alone does not prove a live Client view: animation or editor chrome can change independently.

## Real-time video

```powershell
python -m scripts.player record --hwnd 459576 --output builds/1/captures/run-01.mp4 --seconds 15 --fps 8 --mode instrumented --build-id ACCEPTED_BUILD --session-id RUN_SESSION --studio-id STUDIO_UUID
```

Run only when the producer authorizes the capture scenario; recording may run alongside the same owner's ordinary inputs. It does not move the camera or issue input. Full-window dimensions or an explicit crop must be even for yuv420p. Duration is bounded to 0.25–120 seconds and rate to 1–30 FPS. Start at 8 FPS; lower it if capture cannot sustain that rate. The encoder receives newly captured, paced RGB frames through a rawvideo pipe. A timeout kills a stuck encoder; GDI/subprocess resources are released.

The JSON records each actual capture timestamp/hash, capture wall duration, nominal encoded duration, requested FPS, captured frames, ffmpeg version/command, encoder status and ffprobe stream/container results when available. Check both real capture time and encoded duration. The recorder checks lag after every pipe write, including the final write, and checks final wall duration against the nominal schedule before classifying RECORDED. It fails explicitly when capture or the encoder pipe falls materially behind; partial artifacts/logs are retained as CONTROL_FAILURE, never presented as successful footage. Output is silent video; audio recording is not implemented. No frame-sequence slideshow is labeled as a live replay.

## Input fallback: explicit runtime lease required

Prefer calibrated MCP keyboard batches. `protocol.keyboard_batch("W", 200)` builds keyDown/wait/keyUp using the producer-tested schema; it does not call MCP and cannot guarantee independent cleanup after a stalled MCP call. The producer must coordinate release on transport failures.

For host input, the studio lane first takes PLAY_EXCLUSIVE, starts normal Play, confirms the exact Roblox Studio Client viewport is foreground/focused and calibrates its window-relative physical rectangle. The helper deliberately refuses to steal focus or start Play. A lease JSON is an explicit coordination assertion, not a cryptographic permission system or a substitute for the board's task ownership. Example field values below are placeholders and expire immediately until regenerated:

```json
{
  "kind": "PLAY_EXCLUSIVE",
  "run_id": "cycle-001",
  "session_id": "fresh-play-01",
  "owner": "computer-player",
  "build_id": "accepted-build-id",
  "mode": "instrumented",
  "hwnd": 459576,
  "pid": 15836,
  "expires_at": 0,
  "viewport_physical": [16, 262, 1584, 938],
  "client_viewport_focused": true
}
```

Do not copy that viewport as a constant. It illustrates the shape only. Re-measure it for the current layout. Create one action JSON from a fresh real observation:

```json
{
  "run_id": "cycle-001",
  "session_id": "fresh-play-01",
  "action_id": "unique-action-001",
  "observation_id": "frame-001",
  "owner": "computer-player",
  "build_id": "accepted-build-id",
  "mode": "instrumented",
  "hwnd": 459576,
  "expires_at": 0,
  "observed_at": 0,
  "kind": "key",
  "key": "W",
  "duration_ms": 200
}
```

```powershell
python -m scripts.player input --lease path/to/lease.json --action path/to/action.json --result path/to/action-result.json
```

`observed_at` and `expires_at` are Unix epoch seconds. Observations must be at most 15 seconds old and cannot be from the future. The action must fit inside both expiries with release margin. Full duration and observation freshness are validated immediately before the first input. Once started, the action uses one fixed monotonic finish; in-flight checks reserve only the remaining duration plus the 0.5-second release margin, and never extend that finish or charge elapsed hold time again. Actual expiry, revoked/changed lease, STOP, focus/identity/geometry, token and guard failures still abort and release. Allowed keys are W/A/S/D/E/SPACE and arrow keys; duration is 1–2000 ms. `kind: "look"` instead takes finite `dx`/`dy` in -300..300 and `button: "right"` or `"none"`. Right-look positions the cursor in the calibrated viewport center, holds RMB, sends relative mouse movement and releases. `none` is for an already calibrated locked-pointer camera. Neither proves the camera rotated.

The helper rejects STOP, mismatched owner/run/build/session/mode/HWND, wrong PID/title, absent focus assertion, concurrent controller lock and reused action IDs. Immediately before each key-down, mouse-down/move or cursor operation, it rechecks STOP, the full unchanged lease, current exact HWND/PID/title, calibrated window geometry, foreground, unique ownership token, guard liveness, fence and monotonic deadline. It repeats checks during holds. It releases in `finally`; an independent process also releases after completion or a four-second deadline if the executor dies/hangs. Release-only events remain possible after STOP/focus loss but check ownership before each key/button release. Every owner has unique ready/done/fenced/cleanup paths. On timeout, the guard fences the sender and **retains the lock even if release succeeded**, because that executor may still be alive. Normal unlocking requires a done acknowledgment emitted only after the executor permanently leaves its send phase. A resumed sender checks the fence/deadline before further calls. Old cleanup cannot signal/remove another token's files, and release callbacks check current ownership. Cleanup failure also retains the lock and reports CONTROL_FAILURE. OS foreground checks and event delivery cannot be atomic: arbitrary suspension or focus change in the tiny interval between the final check and the OS call remains possible. This is cooperative fencing, not a kernel input permission boundary; retaining ownership prevents a second controller from taking over that unresolved sender. A crashed watchdog plus crashed executor or OS shutdown cannot be covered by this software contract. No autonomous Play/Stop, reset, remote firing, teleport or game-state access occurs.

Replaceable controller state under `scripts/player/.runtime/` contains the controller lock, consumed action IDs and per-token `input.TOKEN.ready`, `.done`, `.fenced`, `.cleanup.json` acknowledgments; it is separate from immutable result evidence. Do not delete a retained lock to bypass a live controller. The producer must first confirm/stop the previous owner, release inputs, inspect that token's `input.TOKEN.cleanup.json`, confirm the old executor/guard are stopped, and verify Studio state; then it can remove a demonstrably stale lock as recovery. Session IDs must change after restart/respawn and the producer must replace/revoke the lease; this host helper cannot independently detect Roblox respawn.

Input result `DELIVERED` means that sending events completed. A fresh frame and, in instrumented mode, an independent read-only state check establish any visible/gameplay effect. On failure, retain the trace and classify CONTROL_FAILURE, GAME_FAILURE or INCONCLUSIVE based on evidence.

## Validation and next calibration

```powershell
python -m unittest scripts.player.test_player scripts.player.test_regressions -v
```

The focused tests never issue real input, start/stop Play or move the Studio camera. The ffmpeg test encodes timed **synthetic** frames in a temporary directory; it is not a game recording. Re-run relevant tests after helper changes. Final runtime acceptance must separately prove live capture, ordinary forward/release, yaw/pitch, timeout cleanup, a short actual MP4 with consistent metadata, then the authorized earned route and fresh replay. Preserve console baseline/delta and complete cleanup before returning the runtime lease.

Host-review regression tests additionally simulate focus/STOP/full-lease/geometry changes during guard startup, a delayed live sender after guard timeout plus rejected second-owner acquisition, old-token cleanup against a new owner, `.json` capture collision and competing creators, existing recorder log/reused result, and a late final pipe write. These use mocked input/process operations; they never drive Studio.


## Optional faster exact-window recorder (historical implementation notes)

Baseline note, 2026-09-07: the implementation history below records earlier pending checks, not the final state of the example. The later known-route recording and its measured 12.130 FPS are described in [artifacts/README.md](../../artifacts/README.md). Privacy/occlusion stress and broad host calibration remain unestablished. For a fresh isolated dependency setup use [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md); the historical system-site-packages command below documents the original host only.

The bounded follow-up inspected `windows-capture` **2.0.1** as an optional Windows Graphics Capture backend. Its released Windows AMD64 ABI3 wheel includes `WindowsCapture(window_hwnd=...)`, frame callbacks with native timespans, and capture control methods. The exact HWND path is suitable for this privacy boundary; do not choose `monitor_index`, Desktop Duplication, desktop rectangles, or substring `window_name` as the final target. Windows provides a single-window capture item API. Sources: [released package](https://pypi.org/project/windows-capture/2.0.1/), [package API](https://github.com/NiiightmareXD/windows-capture/blob/main/windows-capture-python/windows_capture/__init__.py), [Microsoft single-window capture API](https://learn.microsoft.com/en-us/windows/win32/api/windows.graphics.capture.interop/nf-windows-graphics-capture-interop-igraphicscaptureiteminterop-createforwindow).

The subsequent authorized implementation created `.venv-wgc` with system-site packages and installed `windows-capture==2.0.1` plus OpenCV 5.0.0.93 there. NumPy 2.2.3 and PyAV 18.0.0 are reused from the host. Native imports passed; capture has not yet started. The executed setup was:

```powershell
python -m venv --system-site-packages .venv-wgc
.venv-wgc/Scripts/python -m pip install --only-binary=:all: windows-capture==2.0.1
```

Before selecting the candidate, implement it separately from the current `record` CLI: validate exact HWND/PID, disable secondary-window inclusion, accept only an explicit crop calibrated against the WGC frame dimensions, copy fresh callback buffers into a bounded queue, and attach callback sequence/monotonic time/native timespan to each accepted frame. Encode silent MP4 from actual frame timestamps; report callback rate, encoded rate, queue drops, stale/duplicate timestamps, actual duration and any missing interval. A requested update interval does not guarantee a frame rate. Unknown upstream losses must remain unknown rather than inferred from queue counts.

Use a separate bounded capture worker process so a blocked native stop can be terminated after a grace period. Preserve the existing immutable artifact-family reservation, exclusive result/log creation and partial-failure metadata contract. Test zero-frame timeout, queue saturation, resize/closed/reused HWND, cancellation and encoder failure before live acceptance. Under an exclusive capture lease, verify an occluding unrelated app never appears, Client motion is fresh, crop is calibrated, shutdown is bounded and sustained recorded FPS is measured. A configured 30 FPS does not establish actual capture rate. The PrintWindow preview path remains available.


The separate CLI is now implemented in `scripts/player/fast_record.py`; the original `record` CLI is unchanged:

```powershell
.venv-wgc/Scripts/python -m scripts.player.fast_record --hwnd 459576 --output builds/1/captures/wgc-preview-01.mp4 --seconds 20 --mode instrumented --build-id BUILD_ID --session-id SESSION_ID --studio-id STUDIO_UUID
.venv-wgc/Scripts/python -m unittest scripts.player.test_fast_record -v
```

Select the current exact HWND; the numeric example is not a persisted identity. The module verifies HWND/PID and a Roblox Studio title before capture and callbacks. It passes `window_hwnd`, `secondary_window=None`, `monitor_index=None`, `window_name=None`, captures no cursor, and never moves/focuses the window. Optional `--crop LEFT TOP RIGHT BOTTOM` is relative to the actual WGC frame, independently calibrated. Width/height must be even. Duration is 1?30 seconds (default 20). `--nominal-rate 30` is encoder configuration, **not a promised capture FPS**.

Each fresh eligible callback records host monotonic time, sequence and raw native timespan. Copied BGRA arrays enter a four-frame bounded queue; stale timestamps and queue-full drops are counted explicitly. PyAV/libx264 encodes silent MP4 with presentation timestamps from actual callback intervals. The callback ledger is `.frames.json`; final `.json` metadata records observed callback/encoded rates, frame span/count, queue drops, unknown upstream losses, actual worker/supervisor durations and decoded MP4 stream metadata. All three artifacts share an exclusive reservation. Existing files are never overwritten. `RECORDED_UNVERIFIED` and `live_client_verified: false` deliberately require independent live-frame review; inadequate temporal coverage is a failure, not a fabricated padded clip.

The supervisor starts a separate spawn worker and bounds it to requested duration plus 10 seconds, then finite join/terminate/kill grace periods (up to six additional seconds). Ctrl+C requests cancellation and follows the same cleanup path. A stuck native stop or encoder cannot leave an unbounded recording worker; partial files and failure metadata remain. Recalibrate after resize and use a new output name on retry. Nine focused tests passed with mocked capture/window/process operations; a real PyAV synthetic fixture verified variable frame PTS at 0, 0.1 and 0.4 seconds. These tests are not actual gameplay footage. Under the next authorized capture lease, benchmark the new backend and inspect foreground-overlap privacy, actual first-person framing, smoothness and shutdown before selecting it for the owner's clip. Do not bundle `.venv-wgc` into the portable release; reproduce dependencies explicitly.


Compatibility note: the first live WGC attempt reported that the host lacks the optional secondary-window API. Passing `secondary_window=False` invoked that unsupported setter even though inclusion was being disabled. The corrected constructor uses `None`, which the released Python/Rust binding maps to the default branch without calling the setter; a fresh WGC session defaults to **excluding secondary windows**. Exact HWND/PID checks and null monitor/name targeting remain unchanged. Microsoft documents this property's false default and Windows 11 24H2 introduction: [IncludeSecondaryWindows](https://learn.microsoft.com/en-us/uwp/api/windows.graphics.capture.graphicscapturesession.includesecondarywindows). No monitor fallback or secondary-window opt-in is introduced. The failed recording artifact is preserved; retry with a new output name under the producer's capture lease. Ten focused tests now pass, including an older-platform constructor mock, but the corrected native capture still requires a live retry.
