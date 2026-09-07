"""Pure validation shared by capture/input adapters and controlled tests."""
from __future__ import annotations

import json
import math
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

MODES = {"visual", "instrumented", "regression"}
KEYS = {"W": 0x57, "A": 0x41, "S": 0x53, "D": 0x44,
        "E": 0x45, "SPACE": 0x20, "LEFT": 0x25, "RIGHT": 0x27,
        "UP": 0x26, "DOWN": 0x28}


class ControlFailure(RuntimeError):
    """Transport/lease failure, never evidence of a game defect."""


def number(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ControlFailure(f"{name} must be numeric")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ControlFailure(f"{name} must be finite within {minimum}..{maximum}")
    return value


def validate_action(action, lease, now=None):
    """Caller must additionally check STOP, window identity, focus and one-owner lock."""
    now = time.time() if now is None else now
    for field in ("run_id", "session_id", "action_id", "observation_id", "owner", "build_id"):
        if not isinstance(action.get(field), str) or not action[field].strip():
            raise ControlFailure(f"missing {field}")
    if action.get("mode") not in MODES:
        raise ControlFailure("mode must be visual, instrumented, or regression")
    if lease.get("kind") != "PLAY_EXCLUSIVE":
        raise ControlFailure("PLAY_EXCLUSIVE lease required")
    for field in ("run_id", "session_id", "owner", "build_id", "mode", "hwnd"):
        if action.get(field) != lease.get(field):
            raise ControlFailure(f"lease {field} mismatch")
    number(action.get("hwnd"), "hwnd", 1, 2**64 - 1)
    for item, label in ((action, "action"), (lease, "lease")):
        expires = number(item.get("expires_at"), f"{label} expiry", 0, 1e12)
        if now >= expires:
            raise ControlFailure(f"{label} expired")
    observed = number(action.get("observed_at"), "observed_at", 0, 1e12)
    if not 0 <= now - observed <= 15:
        raise ControlFailure("observation is stale or from the future")
    duration = number(action.get("duration_ms"), "duration_ms", 1, 2000)
    if now + duration / 1000 + 0.5 >= min(action["expires_at"], lease["expires_at"]):
        raise ControlFailure("action cannot finish before expiry")
    kind = action.get("kind")
    if kind == "key":
        if action.get("key") not in KEYS:
            raise ControlFailure("unsupported key")
    elif kind == "look":
        number(action.get("dx"), "dx", -300, 300)
        number(action.get("dy"), "dy", -300, 300)
        if action.get("button", "right") not in ("right", "none"):
            raise ControlFailure("look button must be right or none")
    else:
        raise ControlFailure("kind must be key or look")
    return action


def keyboard_batch(key, duration_ms):
    """Build a bounded MCP payload; delivery and independent timeout are not guaranteed."""
    if key not in KEYS:
        raise ControlFailure("unsupported key")
    number(duration_ms, "duration_ms", 1, 2000)
    return [{"action": "keyDown", "key_code": key},
            {"action": "wait", "wait_time_ms": duration_ms},
            {"action": "keyUp", "key_code": key}]


def write_json(path, data):
    """Replaceable controller state only; never use for final evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_evidence_json(path, data):
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


@contextmanager
def reserve_artifacts(paths):
    """Coordinate a family before slow work; actual writers still use exclusive creation."""
    paths = [Path(path).resolve() for path in paths]
    if len(set(paths)) != len(paths):
        raise ControlFailure("artifact and sidecar paths must be distinct")
    # The shared metadata stem also excludes PNG/MP4 collisions with the same basename.
    reservation = paths[0].with_suffix(".artifact-reservation")
    reservation.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    try:
        with reservation.open("x", encoding="ascii") as handle:
            handle.write(token)
    except FileExistsError:
        raise ControlFailure("artifact family is already reserved")
    try:
        if any(path.exists() for path in paths):
            raise ControlFailure("refusing to overwrite existing evidence in artifact family")
        yield
    finally:
        if reservation.exists() and reservation.read_text(encoding="ascii") == token:
            reservation.unlink()


def validate_result(result):
    """Evidence rules do not turn a logged input delivery into earned victory."""
    if result.get("mode") not in MODES:
        raise ControlFailure("missing test mode")
    if result.get("outcome") not in {"PASS", "GAME_FAILURE", "CONTROL_FAILURE", "INCONCLUSIVE"}:
        raise ControlFailure("invalid outcome")
    if result["outcome"] == "PASS":
        for field in ("build_id", "session_id", "visible_completion_artifact", "oracle_completion_artifact"):
            if not result.get(field):
                raise ControlFailure(f"PASS requires {field}")
        if result.get("bypasses") or not result.get("ordinary_input_only"):
            raise ControlFailure("PASS requires earned ordinary-input completion")
        if result["mode"] == "visual" and result.get("hidden_information_received", True):
            raise ControlFailure("visual PASS cannot receive hidden information")
    return result
