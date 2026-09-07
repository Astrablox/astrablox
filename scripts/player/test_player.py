"""Controlled helper tests. No Studio inputs, Play, or camera operations."""
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from .capture import select_window, validate_crop
from .protocol import ControlFailure, keyboard_batch, validate_action, validate_result
from .record import ffmpeg_command, record_window


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.lease = dict(kind="PLAY_EXCLUSIVE", run_id="r", session_id="s", owner="p",
                          build_id="b", mode="instrumented", hwnd=1, expires_at=110)
        self.action = dict(self.lease, kind="key", action_id="a", observation_id="o",
                           observed_at=99, duration_ms=250, key="W")

    def test_valid_action(self):
        self.assertIs(validate_action(self.action, self.lease, now=100), self.action)

    def test_expired_action_or_lease(self):
        for subject in (self.action, self.lease):
            subject["expires_at"] = 100
            with self.assertRaises(ControlFailure):
                validate_action(self.action, self.lease, now=100)
            subject["expires_at"] = 110

    def test_stale_future_observation(self):
        for value in (80, 101):
            with self.subTest(value=value), self.assertRaises(ControlFailure):
                validate_action(dict(self.action, observed_at=value), self.lease, now=100)

    def test_wrong_owner_session_build_or_mode(self):
        for field in ("owner", "session_id", "build_id", "mode", "hwnd"):
            with self.subTest(field=field), self.assertRaises(ControlFailure):
                validate_action(dict(self.action, **{field: "other"}), self.lease, now=100)

    def test_finite_bounded_duration(self):
        for value in (float("nan"), float("inf"), 0, 2001, True, "100"):
            with self.subTest(value=value), self.assertRaises(ControlFailure):
                validate_action(dict(self.action, duration_ms=value), self.lease, now=100)

    def test_action_needs_time_to_release(self):
        with self.assertRaises(ControlFailure):
            validate_action(dict(self.action, expires_at=100.5), self.lease, now=100)

    def test_look_bounds(self):
        validate_action(dict(self.action, kind="look", dx=50, dy=-20), self.lease, now=100)
        with self.assertRaises(ControlFailure):
            validate_action(dict(self.action, kind="look", dx=301, dy=0), self.lease, now=100)

    def test_input_key_allowlist(self):
        with self.assertRaises(ControlFailure):
            validate_action(dict(self.action, key="F5"), self.lease, now=100)

    def test_mcp_macro_contains_release(self):
        batch = keyboard_batch("W", 200)
        self.assertEqual([item["action"] for item in batch], ["keyDown", "wait", "keyUp"])
        self.assertEqual(batch[1]["wait_time_ms"], 200)

    def test_result_requires_actual_evidence(self):
        with self.assertRaises(ControlFailure):
            validate_result({"mode": "visual", "outcome": "PASS"})
        base = dict(mode="visual", outcome="PASS", build_id="b", session_id="s",
                    visible_completion_artifact="frame.png", oracle_completion_artifact="oracle.json",
                    ordinary_input_only=True, hidden_information_received=False)
        validate_result(base)
        for mutation in ({"bypasses": ["teleport"]}, {"hidden_information_received": True}):
            with self.assertRaises(ControlFailure):
                validate_result(dict(base, **mutation))


class CaptureTests(unittest.TestCase):
    def test_ambiguous_target_rejected(self):
        windows = [{"hwnd": 1, "title": "Roblox Studio"}, {"hwnd": 2, "title": "Roblox Studio"}]
        with patch("scripts.player.capture.list_windows", return_value=windows):
            with self.assertRaises(ControlFailure):
                select_window(title_match="Roblox Studio")
            self.assertEqual(select_window(hwnd=2)["hwnd"], 2)

    def test_empty_or_missing_target_rejected(self):
        for kwargs in ({}, {"title_match": ""}, {"hwnd": 1, "title_match": "Studio"}):
            with self.assertRaises(ControlFailure):
                select_window(**kwargs)

    def test_explicit_crop_bounds(self):
        self.assertEqual(validate_crop([0, 2, 64, 48], (64, 48)), (0, 2, 64, 48))
        for crop in ([0, 0, 65, 48], [-1, 0, 64, 48], [1, 1, 1, 2], [0, 0, 1.2, 2]):
            with self.assertRaises(ControlFailure):
                validate_crop(crop, (64, 48))

    def test_encoder_command_is_argument_list(self):
        command = ffmpeg_command("C:/path with spaces/ffmpeg.exe", (64, 48), 4, "out file.mp4")
        self.assertIn("rawvideo", command)
        self.assertEqual(command[-1], "out file.mp4")
        with self.assertRaises(ControlFailure):
            ffmpeg_command("ffmpeg", (63, 48), 4, "out.mp4")

    def test_watchdog_cleanup_without_real_inputs(self):
        from .input import watchdog, owner_paths
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "input.lock"
            lock.write_text(json.dumps({"token": "fixture"}))
            paths = owner_paths(lock, "fixture")
            paths["done"].write_text("fixture")
            with patch("scripts.player.input.release_all", return_value=[]) as release:
                watchdog(lock, time.monotonic() + 0.1, "fixture")
            release.assert_called_once()
            self.assertFalse(lock.exists())
            self.assertEqual(json.loads(owner_paths(lock, "fixture")["cleanup.json"].read_text())["failures"], [])

    def test_watchdog_retains_lock_on_release_failure(self):
        from .input import watchdog, owner_paths
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "input.lock"
            lock.write_text(json.dumps({"token": "fixture"}))
            with patch("scripts.player.input.release_all", return_value=["fixture key-up failure"]):
                watchdog(lock, time.monotonic() - 1, "fixture")
            self.assertTrue(lock.exists())
            self.assertEqual(len(json.loads(owner_paths(lock, "fixture")["cleanup.json"].read_text())["failures"]), 1)

    def test_stop_prevents_any_host_input(self):
        from .input import execute
        now = time.time()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "gamemaster").mkdir()
            (root / "gamemaster" / "STOP").touch()
            lease = dict(kind="PLAY_EXCLUSIVE", run_id="r", session_id="s", owner="p",
                         build_id="b", mode="instrumented", hwnd=1, expires_at=now + 30)
            action = dict(lease, kind="key", action_id="a", observation_id="o", observed_at=now,
                          key="W", duration_ms=200)
            (root / "lease.json").write_text(json.dumps(lease))
            (root / "action.json").write_text(json.dumps(action))
            with patch("scripts.player.input.ROOT", root), patch("scripts.player.input.send_input") as send:
                with self.assertRaisesRegex(ControlFailure, "STOP"):
                    execute(root / "action.json", root / "lease.json", root / "result.json")
                send.assert_not_called()

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg unavailable")
    def test_real_encoder_with_timed_synthetic_frames(self):
        # This is explicitly an encoder fixture, never claimed as gameplay footage.
        from PIL import Image
        counter = 0
        def fixture(*_):
            nonlocal counter
            counter += 1
            return Image.new("RGB", (64, 48), (counter * 30 % 255, 10, 20)), {
                "captured_at_utc": str(time.time()), "pixel_sha256": str(counter), "capture_duration_seconds": 0}
        with tempfile.TemporaryDirectory() as folder, patch("scripts.player.record.capture_window", side_effect=fixture):
            output = Path(folder) / "fixture.mp4"
            result = record_window({"hwnd": 1}, output, 1, fps=4,
                                   context={"mode": "instrumented", "fixture": "synthetic encoder test"})
            self.assertEqual(result["status"], "RECORDED")
            self.assertEqual(result["frames_captured"], 4)
            self.assertGreaterEqual(result["capture_wall_seconds"], 0.95)
            self.assertGreater(output.stat().st_size, 100)
            if result["ffprobe"]:
                video = result["ffprobe"]["streams"][0]
                self.assertEqual(int(video["nb_frames"]), 4)
                self.assertAlmostEqual(float(video["duration"]), 1, delta=0.1)


if __name__ == "__main__":
    unittest.main()
