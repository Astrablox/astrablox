"""Optional WGC recorder: .venv-wgc/Scripts/python -m scripts.player.fast_record --help.

No capture occurs on import. Exact-window capture runs only in a bounded child process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import queue
import time
from fractions import Fraction
from pathlib import Path

from .capture import select_window, validate_crop, windows_api
from .protocol import ControlFailure, MODES, number, reserve_artifacts, write_evidence_json


def check_target(target):
    gui, _, process = windows_api()
    hwnd = target["hwnd"]
    if not gui.IsWindow(hwnd) or process.GetWindowThreadProcessId(hwnd)[1] != target["pid"]:
        raise ControlFailure("selected HWND disappeared or changed PID")
    if gui.IsIconic(hwnd):
        raise ControlFailure("selected window is minimized")
    if "roblox studio" not in gui.GetWindowText(hwnd).casefold():
        raise ControlFailure("selected HWND is no longer a Roblox Studio window")


class FrameBuffer:
    """Bounded callback queue. Native and host clocks must advance; no fabricated frames."""
    def __init__(self, capacity=4):
        self.queue = queue.Queue(maxsize=capacity)
        self.sequence = 0
        self.last_native = None
        self.last_host = None
        self.dropped = 0
        self.stale = 0
        self.ledger = []

    def offer(self, pixels, native_time, host_ns):
        self.sequence += 1
        item = {"sequence": self.sequence, "native_timespan": native_time, "callback_monotonic_ns": host_ns}
        if ((self.last_native is not None and native_time <= self.last_native)
                or (self.last_host is not None and host_ns <= self.last_host)):
            self.stale += 1
            item["state"] = "REJECTED_STALE_TIMESTAMP"
        else:
            self.last_native, self.last_host = native_time, host_ns
            if self.queue.full():
                self.dropped += 1
                item["state"] = "DROPPED_QUEUE_FULL"
            else:
                # Native buffers cannot be retained past their callback without an owned copy.
                self.queue.put_nowait((pixels.copy(), item))
                item["state"] = "QUEUED"
        self.ledger.append(item)


class Encoder:
    """Silent H.264 MP4; actual callback intervals become frame presentation timestamps."""
    def __init__(self, output, size, nominal_rate=30):
        import av
        if any(type(n) is not int or n <= 0 or n % 2 for n in size):
            raise ControlFailure("WGC crop width/height must be positive even integers")
        self.av = av
        self.handle = Path(output).open("xb")
        self.container = None
        self.frames = 0
        self.first_ns = None
        self.last_pts = -1
        try:
            self.container = av.open(self.handle, mode="w", format="mp4")
            self.stream = self.container.add_stream("libx264", rate=nominal_rate,
                                                    options={"preset": "ultrafast", "crf": "23", "tune": "zerolatency"})
            self.stream.width, self.stream.height = size
            self.stream.pix_fmt = "yuv420p"
            self.stream.time_base = Fraction(1, 1_000_000)
            self.stream.codec_context.time_base = Fraction(1, 1_000_000)
        except Exception:
            if self.container is not None:
                self.container.close()
            self.handle.close()
            raise

    def add(self, pixels, host_ns):
        if self.first_ns is None:
            self.first_ns = host_ns
        pts = (host_ns - self.first_ns) // 1000
        if pts <= self.last_pts:
            raise ControlFailure("encoder presentation timestamp did not advance")
        frame = self.av.VideoFrame.from_ndarray(pixels, format="bgra")
        frame.pts, frame.time_base = pts, Fraction(1, 1_000_000)
        for packet in self.stream.encode(frame):
            self.container.mux(packet)
        self.last_pts = pts
        self.frames += 1

    def close(self):
        try:
            for packet in self.stream.encode():
                self.container.mux(packet)
        finally:
            try:
                self.container.close()
            finally:
                self.handle.close()


def _worker(config, cancellation, result_queue):
    """Native stop/encoding may block; supervisor owns the outer termination deadline."""
    started = time.monotonic()
    buffer = FrameBuffer()
    callback_error = []
    encoder = None
    control = None
    size = None
    crop_bounds = None
    target = config["target"]
    deadline = started + config["seconds"]
    accepting = True
    result = {"status": "CONTROL_FAILURE", "target": target, "live_client_verified": False}
    try:
        from windows_capture import WindowsCapture
        check_target(target)
        # None keeps the fresh WGC session's documented default (secondary windows excluded).
        # False invokes the newer IncludeSecondaryWindows setter even when merely disabling it,
        # which windows-capture rejects on platforms predating that optional API.
        capture = WindowsCapture(window_hwnd=target["hwnd"], monitor_index=None,
                                 window_name=None, secondary_window=None, cursor_capture=False)

        @capture.event
        def on_frame_arrived(frame, internal_control):
            nonlocal accepting
            now = time.monotonic()
            if not accepting or cancellation.is_set() or now >= deadline:
                accepting = False
                internal_control.stop()
                return
            try:
                check_target(target)
                buffer.offer(frame.frame_buffer, int(frame.timespan), time.monotonic_ns())
            except Exception as exc:
                callback_error.append(str(exc))
                accepting = False
                internal_control.stop()

        @capture.event
        def on_closed():
            nonlocal accepting
            if time.monotonic() < deadline and not cancellation.is_set():
                callback_error.append("capture window closed before requested duration")
            accepting = False

        control = capture.start_free_threaded()
        while time.monotonic() < deadline and not cancellation.is_set():
            if callback_error:
                raise ControlFailure(callback_error[0])
            if control.is_finished():
                raise ControlFailure("native capture ended before requested duration")
            try:
                pixels, entry = buffer.queue.get(timeout=0.05)
            except queue.Empty:
                if encoder is None and time.monotonic() - started >= 3:
                    raise ControlFailure("zero-frame startup timeout")
                continue
            frame_size = (pixels.shape[1], pixels.shape[0])
            if size is None:
                size = frame_size
                crop_bounds = validate_crop(config.get("crop"), size)
                l, t, r, b = crop_bounds
                encoder = Encoder(config["output"], (r - l, b - t), config["nominal_rate"])
            elif frame_size != size:
                raise ControlFailure("WGC frame dimensions changed; recalibrate crop")
            l, t, r, b = crop_bounds
            encoder.add(pixels[t:b, l:r], entry["callback_monotonic_ns"])
            entry["state"] = "ENCODED"
            entry["pts_microseconds"] = encoder.last_pts
        accepting = False
        # Stop producer before drain. If the native call blocks the supervisor terminates us.
        control.stop()
        control = None
        if callback_error:
            raise ControlFailure(callback_error[0])
        if encoder is None:
            raise ControlFailure("no frames captured")
        while not buffer.queue.empty():
            pixels, entry = buffer.queue.get_nowait()
            if (pixels.shape[1], pixels.shape[0]) != size:
                raise ControlFailure("frame dimensions changed during drain")
            l, t, r, b = crop_bounds
            encoder.add(pixels[t:b, l:r], entry["callback_monotonic_ns"])
            entry["state"] = "ENCODED"
            entry["pts_microseconds"] = encoder.last_pts
        result["status"] = "CANCELLED" if cancellation.is_set() else "RECORDED_UNVERIFIED"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        accepting = False
        if control is not None:
            try:
                control.stop()
            except Exception as exc:
                result["error"] = str(exc)
                result["status"] = "CONTROL_FAILURE"
        if encoder is not None:
            result["encoded_frames"] = encoder.frames
            result["encoded_first_to_last_seconds"] = max(0, encoder.last_pts) / 1_000_000
            span = result["encoded_first_to_last_seconds"]
            result["observed_encoded_fps"] = (encoder.frames - 1) / span if span > 0 else None
            if result["status"] == "RECORDED_UNVERIFIED" and span < max(0, config["seconds"] - 1):
                result.update(status="CONTROL_FAILURE", error="fresh encoded frames did not cover requested interval")
            try:
                encoder.close()
            except Exception as exc:
                result["error"] = f"encoder close: {exc}"
                result["status"] = "CONTROL_FAILURE"
        result.update(callbacks_received=buffer.sequence, queue_drops=buffer.dropped,
                      stale_timestamps=buffer.stale, upstream_lost_frames="UNKNOWN",
                      worker_wall_seconds=time.monotonic() - started, crop_physical=crop_bounds,
                      wgc_frame_size=size, callback_ledger=buffer.ledger)
        if len(buffer.ledger) >= 2:
            callback_span = (buffer.ledger[-1]["callback_monotonic_ns"] - buffer.ledger[0]["callback_monotonic_ns"]) / 1e9
            result["observed_callback_fps"] = (len(buffer.ledger) - 1) / callback_span if callback_span > 0 else None
        # Persist the potentially larger ledger outside multiprocessing's result pipe.
        try:
            write_evidence_json(config["ledger"], buffer.ledger)
            result.pop("callback_ledger")
        except Exception as exc:
            result.pop("callback_ledger", None)
            result["status"], result["error"] = "CONTROL_FAILURE", str(exc)
        result_queue.put(result)


def record(hwnd, output, seconds, crop=None, nominal_rate=30, context=None):
    number(seconds, "seconds", 1, 30)
    number(nominal_rate, "nominal_rate", 1, 60)
    output = Path(output)
    if output.suffix.lower() != ".mp4":
        raise ControlFailure("output must be a new .mp4")
    ledger = output.with_suffix(".frames.json")
    metadata = output.with_suffix(".json")
    with reserve_artifacts([output, metadata, ledger]):
        target = select_window(hwnd=hwnd)
        check_target(target)
        config = dict(target=target, output=str(output.resolve()), ledger=str(ledger.resolve()),
                      seconds=seconds, crop=crop, nominal_rate=int(nominal_rate))
        ctx = mp.get_context("spawn")
        cancellation, result_queue = ctx.Event(), ctx.Queue(maxsize=1)
        worker = ctx.Process(target=_worker, args=(config, cancellation, result_queue), daemon=True)
        started = time.monotonic()
        worker.start()
        result = None
        reason = None
        try:
            while time.monotonic() - started < seconds + 10:
                try:
                    result = result_queue.get(timeout=0.1)
                    break
                except queue.Empty:
                    if not worker.is_alive():
                        reason = "capture worker exited without result"
                        break
        except KeyboardInterrupt:
            reason = "owner cancelled recording"
        finally:
            cancellation.set()
            worker.join(timeout=2)
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=2)
                reason = reason or "capture worker exceeded bounded shutdown"
            if worker.is_alive():
                worker.kill()
                worker.join(timeout=2)
                reason = "capture worker required forced termination"
            result_queue.close()
        if result is None:
            result = {"status": "CONTROL_FAILURE", "error": reason or "capture deadline exceeded"}
        if reason and result.get("status") != "CONTROL_FAILURE":
            result.update(status="CONTROL_FAILURE", error=reason)
        result.update(context or {})
        result.update(target=target, requested_seconds=seconds, nominal_encoder_rate=nominal_rate,
                      capture_method="Windows Graphics Capture exact HWND", audio=False,
                      live_client_verified=False, supervisor_wall_seconds=time.monotonic() - started,
                      artifact=str(output.resolve()), callback_ledger_artifact=str(ledger.resolve()),
                      worker_stopped=not worker.is_alive(), worker_exitcode=worker.exitcode)
        if output.exists():
            result["file_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
            try:
                import av
                with av.open(str(output)) as media:
                    stream = media.streams.video[0]
                    result["encoded_stream"] = {"frames": stream.frames,
                        "duration_seconds": float(stream.duration * stream.time_base) if stream.duration else None,
                        "average_rate": str(stream.average_rate), "width": stream.width, "height": stream.height}
            except Exception as exc:
                result.update(status="CONTROL_FAILURE", error=f"encoded artifact unreadable: {exc}")
        write_evidence_json(metadata, result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hwnd", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=float, default=20)
    parser.add_argument("--crop", nargs=4, type=int)
    parser.add_argument("--nominal-rate", type=int, default=30)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    for field in ("build-id", "session-id", "studio-id"):
        parser.add_argument("--" + field, required=True)
    args = parser.parse_args()
    try:
        result = record(args.hwnd, args.output, args.seconds, args.crop, args.nominal_rate,
                        {"mode": args.mode, "build_id": args.build_id, "session_id": args.session_id,
                         "studio_id": args.studio_id})
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "RECORDED_UNVERIFIED" else 1
    except (ControlFailure, OSError, ValueError) as exc:
        print(json.dumps({"status": "CONTROL_FAILURE", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
