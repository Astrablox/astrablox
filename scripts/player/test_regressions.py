"""Host-review regressions: mocked controls/processes only, no Studio operations."""
import json
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PIL import Image

from .capture import save_capture
from .input import execute, owner_paths, watchdog
from .protocol import ControlFailure
from .record import record_window


class HostReviewRegressions(unittest.TestCase):
    def input_fixture(self, root, startup):
        now = time.time()
        lease = dict(kind="PLAY_EXCLUSIVE", run_id="r", session_id="s", owner="p", build_id="b",
                     mode="instrumented", hwnd=1, pid=2, expires_at=now + 60,
                     viewport_physical=[0, 0, 640, 480], client_viewport_focused=True)
        action = dict(lease, kind="key", action_id="a", observation_id="o", observed_at=now,
                      key="W", duration_ms=10)
        lease_path, action_path = root / "lease.json", root / "action.json"
        lease_path.write_text(json.dumps(lease))
        action_path.write_text(json.dumps(action))
        gui = MagicMock()
        gui.GetWindowRect.return_value = (0, 0, 640, 480)
        gui.GetForegroundWindow.return_value = 1
        lock = root / "runtime" / "input.lock"
        guard = MagicMock()
        guard.returncode = 0
        guard.poll.return_value = None
        def launch(command, **_):
            token = command[command.index("--token") + 1]
            deadline = float(command[command.index("--deadline") + 1])
            paths = owner_paths(lock, token)
            paths["ready"].write_text(token)
            startup(root, gui, lease_path, lock, token, guard)
            def finish(**_):
                if guard.poll.return_value is None:
                    watchdog(lock, deadline, token)
                return 0
            guard.wait.side_effect = finish
            return guard
        stack = ExitStack()
        stack.enter_context(patch("scripts.player.input.ROOT", root))
        stack.enter_context(patch("scripts.player.input.LOCK", lock))
        stack.enter_context(patch("scripts.player.input.select_window", return_value={"hwnd": 1, "pid": 2, "title": "Game - Roblox Studio"}))
        stack.enter_context(patch("scripts.player.input.windows_api", return_value=(gui, None, None)))
        stack.enter_context(patch("scripts.player.input.subprocess.Popen", side_effect=launch))
        sends = stack.enter_context(patch("scripts.player.input.send_input"))
        stack.enter_context(patch("scripts.player.input.release_all", return_value=[]))
        return stack, action_path, lease_path, lock, sends, gui

    def test_startup_focus_stop_full_lease_geometry_changes_send_nothing(self):
        for change in ("focus", "STOP", "lease", "geometry"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                def startup(root, gui, lease_path, *_):
                    if change == "focus":
                        gui.GetForegroundWindow.return_value = 99
                    elif change == "STOP":
                        (root / "STOP").touch()
                    elif change == "geometry":
                        gui.GetWindowRect.return_value = (1, 1, 641, 481)
                    else:
                        lease = json.loads(lease_path.read_text())
                        lease["pid"] = 999
                        lease_path.write_text(json.dumps(lease))
                stack, action, lease, _, sends, gui = self.input_fixture(root, startup)
                with stack:
                    result = execute(action, lease, root / "result.json")
                self.assertEqual(result["status"], "CONTROL_FAILURE")
                sends.assert_not_called()
                gui.SetCursorPos.assert_not_called()

    def test_valid_near_expiry_action_holds_full_duration_without_extending_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stack, action_path, lease_path, lock, sends, _ = self.input_fixture(root, lambda *_: None)
            elapsed = [0.0]
            def advance(seconds):
                elapsed[0] = round(elapsed[0] + seconds, 9)
            clock = SimpleNamespace(time=lambda: 1000 + elapsed[0],
                                    monotonic=lambda: elapsed[0], sleep=advance)
            expiry = 1000.8  # 0.2 + 0.5 fits; 2*0.2 + 0.5 does not.
            for path in (action_path, lease_path):
                data = json.loads(path.read_text())
                data["expires_at"] = expiry
                if path == action_path:
                    data["duration_ms"] = 200
                    data["observed_at"] = 1000
                path.write_text(json.dumps(data))
            sent_at, released_at = [], []
            sends.side_effect = lambda **_: sent_at.append(clock.monotonic())
            def released(*_):
                released_at.append(clock.monotonic())
                return []
            # File I/O and scheduler delay consume no virtual setup allowance.
            with stack, patch("scripts.player.input.release_all", side_effect=released), \
                 patch("scripts.player.input.time", clock), patch("scripts.player.protocol.time", clock):
                result = execute(action_path, lease_path, root / "result.json")
            self.assertEqual(result["status"], "DELIVERED", result)
            self.assertEqual(len(sent_at), 1)
            held = released_at[0] - sent_at[0]
            self.assertAlmostEqual(held, 0.2, places=9)
            self.assertAlmostEqual(elapsed[0], 0.2, places=9)
            self.assertFalse(lock.exists())

    def test_inflight_expiry_or_revocation_still_aborts_and_releases(self):
        for failure in ("expiry", "revocation"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                stack, action_path, lease_path, _, sends, _ = self.input_fixture(root, lambda *_: None)
                action = json.loads(action_path.read_text())
                action["duration_ms"] = 200
                action_path.write_text(json.dumps(action))
                real_time = time.time
                offset = [0]
                def after_key_down(**_):
                    if failure == "expiry":
                        offset[0] = 100  # Model an actual epoch expiry after input began.
                    else:
                        lease = json.loads(lease_path.read_text())
                        lease["client_viewport_focused"] = False
                        lease_path.write_text(json.dumps(lease))
                sends.side_effect = after_key_down
                with stack, patch("scripts.player.input.time.time", side_effect=lambda: real_time() + offset[0]), \
                     patch("scripts.player.input.release_all", return_value=[]) as release:
                    result = execute(action_path, lease_path, root / "result.json")
                self.assertEqual(result["status"], "CONTROL_FAILURE")
                self.assertEqual(sends.call_count, 1)
                self.assertGreaterEqual(release.call_count, 1)
                self.assertIn("expired" if failure == "expiry" else "lease changed", result["error"])

    def test_look_variants_share_fixed_action_finish(self):
        for button in ("right", "none"):
            with self.subTest(button=button), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                stack, action_path, lease_path, _, sends, gui = self.input_fixture(root, lambda *_: None)
                action = json.loads(action_path.read_text())
                action.update(kind="look", dx=10, dy=-5, button=button, duration_ms=30)
                action_path.write_text(json.dumps(action))
                with stack:
                    result = execute(action_path, lease_path, root / "result.json")
                self.assertEqual(result["status"], "DELIVERED", result)
                sends.assert_any_call(dx=10, dy=-5, mouse_flags=0x0001)
                self.assertEqual(gui.SetCursorPos.call_count, 1 if button == "right" else 0)

    def test_timed_out_live_sender_is_fenced_and_second_owner_cannot_acquire(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def startup(_, gui, lease, lock, token, guard):
                watchdog(lock, time.monotonic() - 1, token)
                guard.poll.return_value = 0
            stack, action, lease, lock, sends, _ = self.input_fixture(root, startup)
            with stack:
                result = execute(action, lease, root / "result1.json")
                self.assertTrue(lock.exists())
                with self.assertRaisesRegex(ControlFailure, "another controller"):
                    execute(action, lease, root / "result2.json")
            self.assertEqual(result["status"], "CONTROL_FAILURE")
            sends.assert_not_called()

    def test_old_watchdog_cannot_release_or_remove_new_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "input.lock"
            lock.write_text(json.dumps({"token": "new-owner"}))
            with patch("scripts.player.input.release_all") as release:
                watchdog(lock, time.monotonic() - 1, "old-owner")
            release.assert_not_called()
            self.assertEqual(json.loads(lock.read_text())["token"], "new-owner")

    def test_capture_extension_competing_reservation_and_writer_preserve_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "frame.png"
            with patch("scripts.player.capture.capture_window") as capture:
                with self.assertRaises(ControlFailure):
                    save_capture({}, output.with_suffix(".json"))
                capture.assert_not_called()
            def capture(*_):
                with self.assertRaisesRegex(ControlFailure, "reserved"):
                    save_capture({}, output)
                output.write_bytes(b"competing creator sentinel")
                return Image.new("RGB", (4, 4)), {}
            with patch("scripts.player.capture.capture_window", side_effect=capture):
                with self.assertRaises(FileExistsError):
                    save_capture({}, output)
            self.assertEqual(output.read_bytes(), b"competing creator sentinel")
            self.assertFalse(output.with_suffix(".json").exists())

    def test_existing_record_log_and_input_result_rejected_before_work(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "run.mp4"
            output.with_suffix(".ffmpeg.log").write_text("log sentinel")
            with patch("scripts.player.record.capture_window") as capture:
                with self.assertRaises(ControlFailure):
                    record_window({}, output, 1)
                capture.assert_not_called()
            result = root / "result.json"
            result.write_text("result sentinel")
            with patch("scripts.player.input._execute") as executor:
                with self.assertRaises(ControlFailure):
                    execute("missing-action", "missing-lease", result)
                executor.assert_not_called()
            self.assertEqual(result.read_text(), "result sentinel")
            self.assertEqual(output.with_suffix(".ffmpeg.log").read_text(), "log sentinel")

    def test_final_pipe_write_delay_is_control_failure_with_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "late.mp4"
            process = MagicMock()
            process.stdin.write.side_effect = lambda _: time.sleep(0.7)
            process.wait.return_value = 0
            def launch(*_, **__):
                output.write_bytes(b"partial mocked video; not footage")
                return process
            frame = (Image.new("RGB", (4, 4)), {"captured_at_utc": "fixture", "pixel_sha256": "fixture", "capture_duration_seconds": 0})
            with patch("scripts.player.record.capture_window", return_value=frame), \
                 patch("scripts.player.record.subprocess.run", return_value=SimpleNamespace(stdout="libx264 fixture", returncode=0)), \
                 patch("scripts.player.record.subprocess.Popen", side_effect=launch), \
                 patch("scripts.player.record.shutil.which", return_value=None):
                with self.assertRaisesRegex(ControlFailure, "encoder pipe"):
                    record_window({}, output, 0.25, fps=4, ffmpeg="fixture-ffmpeg")
            metadata = json.loads(output.with_suffix(".json").read_text())
            self.assertEqual(metadata["status"], "CONTROL_FAILURE")
            self.assertGreater(metadata["capture_wall_seconds"], 0.65)
            self.assertFalse(metadata["live_client_verified"])
            self.assertIn("-n", metadata["ffmpeg_command"])


if __name__ == "__main__":
    unittest.main()
