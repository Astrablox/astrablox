"""Bounded real-time window recording, with a timestamp ledger and honest timing checks."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .capture import capture_window
from .protocol import ControlFailure, number, write_evidence_json, reserve_artifacts


def ffmpeg_command(executable, size, fps, output):
    number(fps, "fps", 1, 30)
    if any(type(v) is not int or v <= 0 or v % 2 for v in size):
        raise ControlFailure("MP4 frame dimensions must be positive even integers; use explicit crop")
    return [executable, "-nostdin", "-n", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "pipe:0",
            "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]


def record_window(target, output, seconds, fps=8, crop=None, context=None, ffmpeg=None):
    output = Path(output)
    if output.suffix.lower() != ".mp4":
        raise ControlFailure("use a new .mp4 artifact path")
    with reserve_artifacts([output, output.with_suffix(".json"), output.with_suffix(".ffmpeg.log")]):
        return _record_window(target, output, seconds, fps, crop, context, ffmpeg)


def _record_window(target, output, seconds, fps=8, crop=None, context=None, ffmpeg=None):
    number(seconds, "seconds", 0.25, 120)
    number(fps, "fps", 1, 30)
    output = Path(output)
    metadata_path = output.with_suffix(".json")
    if output.suffix.lower() != ".mp4" or output.exists() or metadata_path.exists():
        raise ControlFailure("use a new .mp4 artifact path")
    executable = ffmpeg or shutil.which("ffmpeg")
    if not executable:
        raise ControlFailure("ffmpeg unavailable")
    # Verify the actual installed encoder rather than assuming a recent build.
    encoders = subprocess.run([executable, "-encoders"], capture_output=True, text=True, timeout=10)
    if "libx264" not in encoders.stdout:
        raise ControlFailure("installed ffmpeg lacks libx264")
    version = subprocess.run([executable, "-version"], capture_output=True, text=True, timeout=10).stdout.splitlines()[0]
    first, _ = capture_window(target, crop)
    command = ffmpeg_command(executable, first.size, fps, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    ledger = []
    error = None
    started = time.perf_counter()
    with output.with_suffix(".ffmpeg.log").open("xb") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
        # This bounds a blocked pipe write as well as encoder shutdown.
        guard = threading.Timer(seconds + 20, process.kill)
        guard.daemon = True
        guard.start()
        try:
            count = max(1, round(seconds * fps))
            for index in range(count):
                due = started + index / fps
                delay = due - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                frame, meta = capture_window(target, crop)
                if frame.size != first.size:
                    raise ControlFailure("window dimensions changed during recording")
                elapsed = time.perf_counter() - started
                ledger.append({"index": index, "elapsed_seconds": elapsed,
                               "captured_at_utc": meta["captured_at_utc"],
                               "pixel_sha256": meta["pixel_sha256"],
                               "capture_duration_seconds": meta["capture_duration_seconds"]})
                if elapsed - index / fps > max(0.5, 2 / fps):
                    raise ControlFailure("capture cannot sustain requested FPS; retry at lower FPS")
                process.stdin.write(frame.tobytes())
                written_at = time.perf_counter() - started
                ledger[-1]["pipe_write_finished_seconds"] = written_at
                if written_at - index / fps > max(0.5, 2 / fps):
                    raise ControlFailure("encoder pipe cannot sustain requested FPS")
            remaining = started + count / fps - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            captured_duration = time.perf_counter() - started
            try:
                process.stdin.close()
            except (OSError, BrokenPipeError):
                pass
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                returncode = process.wait(timeout=5)
                error = error or "encoder shutdown timed out"
            guard.cancel()
    probe = None
    probe_exe = shutil.which("ffprobe")
    if probe_exe and output.exists():
        check = subprocess.run([probe_exe, "-v", "quiet", "-show_format", "-show_streams",
                                "-of", "json", str(output)], capture_output=True, text=True, timeout=10)
        if check.returncode == 0:
            probe = json.loads(check.stdout)
    if returncode != 0:
        error = error or f"encoder exited {returncode}"
    if captured_duration > len(ledger) / fps + max(0.25, 1 / fps):
        error = error or "final capture duration exceeded real-time schedule"
    metadata = {**(context or {}), "target": target, "capture_method": "PrintWindow real-time paced frames",
                "artifact": str(output.resolve()), "requested_seconds": seconds,
                "width": first.width, "height": first.height, "crop_physical": crop,
                "capture_wall_seconds": captured_duration, "requested_fps": fps,
                "frames_captured": len(ledger), "nominal_video_seconds": len(ledger) / fps,
                "frame_ledger": ledger, "ffmpeg_version": version, "ffmpeg_command": command,
                "ffprobe": probe, "status": "CONTROL_FAILURE" if error else "RECORDED",
                "error": error, "live_client_verified": False}
    if output.exists():
        metadata["file_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    write_evidence_json(metadata_path, metadata)
    if error:
        raise ControlFailure(f"{error}; partial recording and metadata preserved at {output}")
    return metadata
