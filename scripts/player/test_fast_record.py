"""Optional recorder fixtures: no live capture/input/window changes."""
import json
import queue
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

from .fast_record import Encoder, FrameBuffer, _worker, check_target, record
from .protocol import ControlFailure


class FastRecordingTests(unittest.TestCase):
    def test_owned_copy_order_and_bounded_queue(self):
        frames = FrameBuffer(capacity=1)
        pixels = np.zeros((4, 6, 4), dtype=np.uint8)
        frames.offer(pixels, 1, 1_000)
        pixels[:] = 255
        frames.offer(pixels, 1, 2_000)
        frames.offer(pixels, 2, 3_000)
        owned, _ = frames.queue.get_nowait()
        self.assertEqual(owned.max(), 0)
        self.assertEqual(frames.stale, 1)
        self.assertEqual(frames.dropped, 1)
        self.assertEqual([i["sequence"] for i in frames.ledger], [1, 2, 3])

    def test_exact_window_reuse_or_wrong_title_rejected(self):
        gui, process = MagicMock(), MagicMock()
        gui.IsWindow.return_value = True
        gui.IsIconic.return_value = False
        process.GetWindowThreadProcessId.return_value = (1, 99)
        target = {"hwnd": 5, "pid": 10}
        with patch("scripts.player.fast_record.windows_api", return_value=(gui, None, process)):
            with self.assertRaisesRegex(ControlFailure, "PID"):
                check_target(target)
            process.GetWindowThreadProcessId.return_value = (1, 10)
            gui.GetWindowText.return_value = "unrelated app"
            with self.assertRaisesRegex(ControlFailure, "Studio"):
                check_target(target)

    def test_no_overwrite_before_target_or_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "fixture.mp4"
            output.with_suffix(".frames.json").write_text("sentinel")
            with patch("scripts.player.fast_record.select_window") as select:
                with self.assertRaises(ControlFailure):
                    record(1, output, 1)
                select.assert_not_called()
            self.assertEqual(output.with_suffix(".frames.json").read_text(), "sentinel")

    def test_real_pyav_variable_timestamps_and_exclusive_output(self):
        import av
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "synthetic-not-gameplay.mp4"
            encoder = Encoder(output, (6, 4))
            for i, timestamp in enumerate((1_000_000_000, 1_100_000_000, 1_400_000_000)):
                encoder.add(np.full((4, 6, 4), i * 80, dtype=np.uint8), timestamp)
            encoder.close()
            with av.open(str(output)) as media:
                times = [float(frame.pts * frame.time_base) for frame in media.decode(video=0)]
                self.assertEqual(len(times), 3)
                for actual, expected in zip(times, (0, 0.1, 0.4)):
                    self.assertAlmostEqual(actual, expected, places=4)
            with self.assertRaises(FileExistsError):
                Encoder(output, (6, 4))

    def worker_fixture(self, root, frame_count=0, crop=None, cancelled=False, constructor_check=None):
        # Controlled monotonic clock makes no-frame timeout independent of scheduling.
        ticks = [0]
        def now():
            ticks[0] += 0.25
            return ticks[0]
        fake_clock = SimpleNamespace(monotonic=now, monotonic_ns=lambda: int(ticks[0] * 1e9))
        control = MagicMock()
        control.is_finished.return_value = False
        capture = SimpleNamespace()
        def event(fn):
            setattr(capture, fn.__name__, fn)
            return fn
        capture.event = event
        def start():
            for i in range(frame_count):
                capture.on_frame_arrived(SimpleNamespace(frame_buffer=np.zeros((4, 6, 4), dtype=np.uint8), timespan=i + 1), MagicMock())
            return control
        capture.start_free_threaded = start
        cancellation = MagicMock()
        cancellation.is_set.return_value = cancelled
        results = queue.Queue()
        config = dict(target={"hwnd": 1, "pid": 2}, output=str(root / "fixture.mp4"),
                      ledger=str(root / "fixture.frames.json"), seconds=5, nominal_rate=30, crop=crop)
        def construct(**kwargs):
            if constructor_check is not None:
                constructor_check(kwargs)
            return capture
        with patch.dict("sys.modules", {"windows_capture": SimpleNamespace(WindowsCapture=construct)}), \
             patch("scripts.player.fast_record.check_target"), patch("scripts.player.fast_record.time", fake_clock):
            _worker(config, cancellation, results)
        return results.get_nowait(), control

    def test_older_platform_omits_secondary_setter_and_keeps_exact_hwnd(self):
        observed = []
        def old_platform_constructor(kwargs):
            # Mirrors the released native API's non-default-setting capability guard.
            if kwargs.get("secondary_window") is not None:
                raise RuntimeError("Capturing secondary windows is not supported")
            observed.append(kwargs)
            self.assertEqual(kwargs["window_hwnd"], 1)
            self.assertIsNone(kwargs["monitor_index"])
            self.assertIsNone(kwargs["window_name"])
        with tempfile.TemporaryDirectory() as folder:
            result, control = self.worker_fixture(Path(folder), constructor_check=old_platform_constructor)
        self.assertEqual(len(observed), 1)
        self.assertIn("zero-frame startup timeout", result["error"])
        self.assertNotIn("secondary windows", result["error"])
        control.stop.assert_called_once()

    def test_zero_frame_timeout_stops_native_control_and_records_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result, control = self.worker_fixture(root)
            self.assertEqual(result["status"], "CONTROL_FAILURE")
            self.assertIn("zero-frame", result["error"])
            control.stop.assert_called_once()
            self.assertEqual(json.loads((root / "fixture.frames.json").read_text()), [])

    def test_invalid_crop_rejected_and_capture_stopped(self):
        with tempfile.TemporaryDirectory() as folder:
            result, control = self.worker_fixture(Path(folder), frame_count=1, crop=[0, 0, 100, 4])
            self.assertEqual(result["status"], "CONTROL_FAILURE")
            self.assertIn("crop", result["error"])
            control.stop.assert_called_once()

    def test_worker_drains_queue_and_closes_encoder(self):
        fake_encoder = MagicMock()
        fake_encoder.frames = 3
        fake_encoder.last_pts = 500_000
        with tempfile.TemporaryDirectory() as folder, patch("scripts.player.fast_record.Encoder", return_value=fake_encoder):
            result, control = self.worker_fixture(Path(folder), frame_count=3)
        self.assertEqual(fake_encoder.add.call_count, 3)
        fake_encoder.close.assert_called_once()
        control.stop.assert_called_once()
        self.assertEqual(result["queue_drops"], 0)

    def test_cancellation_stops_capture_without_success_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            result, control = self.worker_fixture(Path(folder), cancelled=True)
            self.assertNotEqual(result["status"], "RECORDED_UNVERIFIED")
            control.stop.assert_called_once()

    def test_supervisor_terminates_stalled_worker_with_failure_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "stalled.mp4"
            worker, ctx = MagicMock(), MagicMock()
            alive = [True]
            worker.is_alive.side_effect = lambda: alive[0]
            worker.terminate.side_effect = lambda: alive.__setitem__(0, False)
            worker.exitcode = -1
            ctx.Process.return_value = worker
            ctx.Queue.return_value.get.side_effect = queue.Empty
            elapsed = [0]
            def clock():
                elapsed[0] += 10
                return elapsed[0]
            with patch("scripts.player.fast_record.select_window", return_value={"hwnd": 1, "pid": 2}), \
                 patch("scripts.player.fast_record.check_target"), \
                 patch("scripts.player.fast_record.mp.get_context", return_value=ctx), \
                 patch("scripts.player.fast_record.time.monotonic", side_effect=clock):
                result = record(1, output, seconds=1)
            worker.terminate.assert_called_once()
            self.assertTrue(result["worker_stopped"])
            self.assertEqual(result["status"], "CONTROL_FAILURE")
            self.assertEqual(json.loads(output.with_suffix(".json").read_text())["worker_exitcode"], -1)


if __name__ == "__main__":
    unittest.main()
