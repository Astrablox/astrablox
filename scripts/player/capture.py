"""Capture only one explicitly selected Windows window, including when occluded."""
from __future__ import annotations

import ctypes
import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .protocol import ControlFailure, write_evidence_json, reserve_artifacts


def windows_api():
    if os.name != "nt":
        raise ControlFailure("Windows capture requires Windows")
    import win32gui
    import win32ui
    import win32process
    # Establish physical pixel coordinates before any geometry query.
    ctypes.windll.user32.SetProcessDPIAware()
    return win32gui, win32ui, win32process


def list_windows():
    gui, _, process = windows_api()
    result = []
    def each(hwnd, _):
        title = gui.GetWindowText(hwnd)
        if title and gui.IsWindowVisible(hwnd):
            result.append({"hwnd": hwnd, "title": title,
                           "pid": process.GetWindowThreadProcessId(hwnd)[1]})
    gui.EnumWindows(each, None)
    return result


def select_window(hwnd=None, title_match=None):
    if (hwnd is None) == (title_match is None):
        raise ControlFailure("select exactly one of --hwnd or --title-match")
    if title_match is not None and not title_match.strip():
        raise ControlFailure("title match cannot be empty")
    candidates = [w for w in list_windows()
                  if (w["hwnd"] == hwnd if hwnd is not None else title_match.casefold() in w["title"].casefold())]
    if len(candidates) != 1:
        raise ControlFailure(f"expected exactly one visible target window, matched {len(candidates)}")
    return candidates[0]


def validate_crop(crop, size):
    if crop is None:
        return (0, 0, *size)
    if len(crop) != 4 or any(type(v) is not int for v in crop):
        raise ControlFailure("crop must have four integer physical-pixel bounds")
    left, top, right, bottom = crop
    if not (0 <= left < right <= size[0] and 0 <= top < bottom <= size[1]):
        raise ControlFailure("crop falls outside current window")
    return tuple(crop)


def capture_window(target, crop=None):
    from PIL import Image
    gui, ui, process = windows_api()
    hwnd = target["hwnd"]
    if not gui.IsWindow(hwnd) or process.GetWindowThreadProcessId(hwnd)[1] != target["pid"]:
        raise ControlFailure("target window disappeared or was reused")
    if gui.IsIconic(hwnd):
        raise ControlFailure("target is minimized; fresh rendered frame cannot be assumed")
    rect = gui.GetWindowRect(hwnd)
    width, height = rect[2] - rect[0], rect[3] - rect[1]
    if not 1 <= width <= 16384 or not 1 <= height <= 16384:
        raise ControlFailure("invalid or excessive window dimensions")
    bounds = validate_crop(crop, (width, height))
    started = time.perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()
    dc_handle = gui.GetWindowDC(hwnd)
    if not dc_handle:
        raise ControlFailure("GetWindowDC failed")
    source = memory = bitmap = old = None
    try:
        source = ui.CreateDCFromHandle(dc_handle)
        memory = source.CreateCompatibleDC()
        bitmap = ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(source, width, height)
        old = memory.SelectObject(bitmap)
        user32 = ctypes.windll.user32
        user32.PrintWindow.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        user32.PrintWindow.restype = ctypes.c_int
        if not user32.PrintWindow(hwnd, memory.GetSafeHdc(), 2):
            raise ControlFailure("PrintWindow failed")
        frame = Image.frombuffer("RGB", (width, height), bitmap.GetBitmapBits(True),
                                 "raw", "BGRX", 0, 1).copy().crop(bounds)
    finally:
        if old is not None and memory is not None:
            memory.SelectObject(old)
        if bitmap is not None:
            gui.DeleteObject(bitmap.GetHandle())
        if memory is not None:
            memory.DeleteDC()
        if source is not None:
            source.DeleteDC()
        gui.ReleaseDC(hwnd, dc_handle)
    metadata = {"capture_method": "PrintWindow(PW_RENDERFULLCONTENT=2)",
                "captured_at_utc": timestamp, "captured_at_epoch": time.time(),
                "capture_duration_seconds": time.perf_counter() - started,
                "target": target, "window_rect_physical": rect, "crop_physical": bounds,
                "width": frame.width, "height": frame.height,
                "pixel_sha256": hashlib.sha256(frame.tobytes()).hexdigest(),
                "live_client_verified": False}
    return frame, metadata


def save_capture(target, output, crop=None, context=None):
    output = Path(output)
    if output.suffix.lower() != ".png":
        raise ControlFailure("capture output must be .png with a distinct JSON sidecar")
    with reserve_artifacts([output, output.with_suffix(".json")]):
        frame, metadata = capture_window(target, crop)
        with output.open("xb") as handle:
            frame.save(handle, format="PNG")
        metadata.update(context or {})
        metadata["file_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
        metadata["artifact"] = str(output.resolve())
        write_evidence_json(output.with_suffix(".json"), metadata)
    return metadata
