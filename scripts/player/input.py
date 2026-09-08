"""Explicit-lease Windows input fallback. No game state access or navigation."""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from ctypes import wintypes

from .capture import select_window, windows_api, validate_crop
from .protocol import (ControlFailure, KEYS, validate_action, write_json,
                       write_evidence_json, reserve_artifacts)

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).resolve().parent / ".runtime" / "input.lock"


def send_input(vk=None, up=False, dx=0, dy=0, mouse_flags=0):
    if os.name != "nt":
        raise ControlFailure("SendInput requires Windows")
    class Mouse(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
    class Keyboard(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
    class Union(ctypes.Union):
        _fields_ = [("mi", Mouse), ("ki", Keyboard)]
    class Input(ctypes.Structure):
        _anonymous_ = ("value",)
        _fields_ = [("type", wintypes.DWORD), ("value", Union)]
    value = Input()
    if vk is not None:
        value.type = 1
        value.ki = Keyboard(vk, 0, 2 if up else 0, 0, 0)
    else:
        value.type = 0
        value.mi = Mouse(int(dx), int(dy), 0, mouse_flags, 0, 0)
    function = ctypes.windll.user32.SendInput
    function.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
    function.restype = wintypes.UINT
    if function(1, ctypes.byref(value), ctypes.sizeof(value)) != 1:
        raise ControlFailure("SendInput rejected event")


def release_all(ownership_check=None):
    failures = []
    for key in KEYS.values():
        try:
            if ownership_check is not None and not ownership_check():
                raise ControlFailure("cleanup lost ownership")
            send_input(vk=key, up=True)
        except Exception as exc:
            failures.append(str(exc))
    for flag in (0x0004, 0x0010, 0x0040):
        try:
            if ownership_check is not None and not ownership_check():
                raise ControlFailure("cleanup lost ownership")
            send_input(mouse_flags=flag)
        except Exception as exc:
            failures.append(str(exc))
    return failures


def owner_paths(lock_path, token):
    stem = Path(lock_path).with_name(f"input.{token}")
    return {name: Path(str(stem) + "." + name) for name in ("ready", "done", "fenced", "cleanup.json")}


def owns_lock(lock_path, token):
    try:
        return json.loads(Path(lock_path).read_text(encoding="utf-8")).get("token") == token
    except (OSError, ValueError):
        return False


def watchdog(lock_path, deadline, token):
    """Timeout fences the sender and RETAINS ownership for producer recovery."""
    lock_path = Path(lock_path)
    paths = owner_paths(lock_path, token)
    if not owns_lock(lock_path, token):
        return
    paths["ready"].write_text(token, encoding="ascii")
    while time.monotonic() < deadline and not paths["done"].exists():
        if not owns_lock(lock_path, token):
            return
        time.sleep(0.025)
    acknowledged = paths["done"].exists() and time.monotonic() < deadline
    if not acknowledged:
        paths["fenced"].touch(exist_ok=True)
    failures = release_all(lambda: owns_lock(lock_path, token)) if owns_lock(lock_path, token) else ["ownership lost"]
    write_json(paths["cleanup.json"], {"token": token, "released_at": time.time(),
                                     "timed_out": not acknowledged, "failures": failures})
    # done is written only after the executor has permanently left its send phase.
    # A timed-out executor may still be alive/stalled, so only producer recovery can unlock it.
    if acknowledged and not failures and owns_lock(lock_path, token):
        lock_path.unlink()


def execute(action_path, lease_path, result_path):
    with reserve_artifacts([result_path]):
        return _execute(action_path, lease_path, result_path)


def _execute(action_path, lease_path, result_path):
    action = json.loads(Path(action_path).read_text(encoding="utf-8"))
    lease_path = Path(lease_path)
    lease = json.loads(lease_path.read_text(encoding="utf-8"))
    validate_action(action, lease)
    if (ROOT / "STOP").exists():
        raise ControlFailure("STOP is set")
    target = select_window(hwnd=action["hwnd"])
    if target["pid"] != lease.get("pid") or "roblox studio" not in target["title"].casefold():
        raise ControlFailure("lease PID/title does not identify selected Roblox Studio")
    gui, _, _ = windows_api()
    rect = gui.GetWindowRect(target["hwnd"])
    viewport = lease.get("viewport_physical")
    if viewport is None:
        raise ControlFailure("lease requires explicitly calibrated viewport_physical")
    validate_crop(viewport, (rect[2] - rect[0], rect[3] - rect[1]))
    if gui.GetForegroundWindow() != target["hwnd"]:
        raise ControlFailure("target must already be foreground; helper does not steal focus")
    if lease.get("client_viewport_focused") is not True:
        raise ControlFailure("producer must confirm Client viewport focus in the lease")
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    history = LOCK.parent / "used-actions"
    history.mkdir(exist_ok=True)
    import hashlib
    action_key = hashlib.sha256((action["session_id"] + "\0" + action["action_id"]).encode()).hexdigest()
    token = uuid.uuid4().hex
    try:
        with LOCK.open("x", encoding="utf-8") as handle:
            json.dump({"token": token, "executor_pid": os.getpid(), "action": action}, handle)
    except FileExistsError:
        raise ControlFailure("another controller or unresolved cleanup owns input.lock")
    paths = owner_paths(LOCK, token)
    guard = None
    deadline = time.monotonic() + 4
    finished_sending = False
    planned_end = None
    result = {"token": token, "action": action, "started_at": time.time(), "status": "CONTROL_FAILURE", "events": []}

    def check_before_send():
        nonlocal planned_end
        # Immediate cooperative checks. The OS focus check and actual SendInput are not atomic.
        if finished_sending or not owns_lock(LOCK, token) or paths["fenced"].exists():
            raise ControlFailure("sender fenced or lost ownership token")
        if guard is None or guard.poll() is not None or time.monotonic() >= deadline:
            raise ControlFailure("watchdog exited or deadline reached")
        if (ROOT / "STOP").exists():
            raise ControlFailure("STOP is set")
        current_lease = json.loads(lease_path.read_text(encoding="utf-8"))
        if current_lease != lease:
            raise ControlFailure("full lease changed during input")
        if planned_end is None:
            # Full duration/freshness validation applies once, immediately before starting.
            validate_action(action, current_lease)
        else:
            # Keep the original finish fixed; elapsed hold time is not reserved again.
            now = time.time()
            expiry = min(action["expires_at"], current_lease["expires_at"])
            remaining = max(0, planned_end - time.monotonic())
            if now >= expiry:
                raise ControlFailure("action or lease expired during input")
            if now + remaining + 0.5 >= expiry:
                raise ControlFailure("remaining action cannot finish before expiry")
        current_target = select_window(hwnd=action["hwnd"])
        if current_target != target or gui.GetWindowRect(target["hwnd"]) != rect:
            raise ControlFailure("target PID/title/geometry changed; recalibration required")
        if gui.GetForegroundWindow() != target["hwnd"]:
            raise ControlFailure("foreground changed during input")
        # Catch changes during the checks as closely to the OS call as practicable.
        if not owns_lock(LOCK, token) or paths["fenced"].exists() or guard.poll() is not None or time.monotonic() >= deadline:
            raise ControlFailure("watchdog ownership changed before send")
        if planned_end is None:
            validate_action(action, current_lease)
            planned_end = time.monotonic() + action["duration_ms"] / 1000

    try:
        try:
            (history / action_key).touch(exist_ok=False)
        except FileExistsError:
            raise ControlFailure("action ID already consumed; create a fresh observation and ID")
        guard = subprocess.Popen([sys.executable, "-m", "scripts.player", "_watchdog",
                                  "--lock", str(LOCK), "--deadline", str(deadline), "--token", token],
                                 cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW)
        while not paths["ready"].exists():
            if guard.poll() is not None or time.monotonic() > deadline - 2.5:
                raise ControlFailure("independent release watchdog failed to start")
            time.sleep(0.01)
        if paths["ready"].read_text(encoding="ascii") != token:
            raise ControlFailure("watchdog readiness token mismatch")
        if action["kind"] == "key":
            check_before_send()
            send_input(vk=KEYS[action["key"]])
            result["events"].append({"key_down": action["key"], "at": time.time()})
        elif action.get("button", "right") == "right":
            x = rect[0] + (viewport[0] + viewport[2]) // 2
            y = rect[1] + (viewport[1] + viewport[3]) // 2
            check_before_send()
            gui.SetCursorPos((x, y))
            check_before_send()
            send_input(mouse_flags=0x0008)
        if planned_end is None:
            check_before_send()
        moved = False
        while time.monotonic() < planned_end:
            check_before_send()
            if action["kind"] == "look" and not moved:
                check_before_send()
                send_input(dx=action["dx"], dy=action["dy"], mouse_flags=0x0001)
                result["events"].append({"relative_mouse": [action["dx"], action["dy"]], "at": time.time()})
                moved = True
            time.sleep(0.01)
        check_before_send()
        result["status"] = "DELIVERED"
        result["note"] = "Input delivery only; inspect a fresh live frame for gameplay effect."
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        finished_sending = True
        # Release events must remain possible after STOP/focus loss, but never cross owners.
        result["release_failures"] = release_all(lambda: owns_lock(LOCK, token)) if owns_lock(LOCK, token) else ["ownership lost"]
        if guard is not None:
            if owns_lock(LOCK, token):
                paths["done"].write_text(token, encoding="ascii")
            try:
                guard.wait(timeout=5)
                cleanup = paths["cleanup.json"]
                if guard.returncode != 0 or not cleanup.exists() or owns_lock(LOCK, token):
                    result["error"] = "independent cleanup unresolved; retained token lock requires producer recovery"
                    result["status"] = "CONTROL_FAILURE"
            except subprocess.TimeoutExpired:
                result["error"] = "watchdog did not acknowledge cleanup; lock retained"
                result["status"] = "CONTROL_FAILURE"
        elif not result["release_failures"] and owns_lock(LOCK, token):
            LOCK.unlink()
        if result["release_failures"]:
            result["status"] = "CONTROL_FAILURE"
        result["ended_at"] = time.time()
        write_evidence_json(result_path, result)
    return result
