"""Bounded root Stop hook. Fail closed (allow stopping) on missing/invalid state.

Only scripts/run.ps1 arms a run, with an inherited ASTRA_RUN_ID and matching
RUN/run.json identity. This hook is the sole continuation mechanism; no launcher
restart loop exists. Time limits are cooperative boundaries, not process kills.
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


def read_json(path):
    with path.open(encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("expected object")
    return value


def atomic_json(path, value):
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError("invalid " + name)
    return value


def evaluate(payload, environment=None, now=None):
    """Return a hook response, or None to allow the turn to finish."""
    environment = os.environ if environment is None else environment
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "Stop":
        return None
    run_id = environment.get("ASTRA_RUN_ID")
    if not run_id or not payload.get("cwd"):
        return None
    gm = Path(payload["cwd"]).resolve() / "gamemaster"
    run_flag, stop_flag = gm / "RUN", gm / "STOP"
    if stop_flag.exists() or not run_flag.exists():
        return None
    # A manually armed/older run cannot attach to an unrelated conversation.
    if run_flag.read_text(encoding="utf-8-sig").strip() != run_id:
        return None
    lock = gm / "hook.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None
    os.close(descriptor)
    try:
        run = read_json(gm / "run.json")
        if run.get("run_id") != run_id:
            return None
        if Path(run["workspace"]).resolve() != gm.parent:
            raise ValueError("workspace mismatch")
        session = str(UUID(payload["session_id"]))
        if run.get("session_id") and run["session_id"] != session:
            return None
        # Stop is a root event; SubagentStop must never consume root budget.
        run["session_id"] = session
        atomic_json(gm / "session.json", {"workspace": str(gm.parent), "session_id": session})
        mode = run["mode"]
        if mode not in ("PLAN", "BUILD", "PLAY", "REVIEW", "IMPROVE"):
            raise ValueError("invalid mode")
        limit = integer(run["max_continues"], "max_continues")
        count = integer(run["continues"], "continues")
        # Legacy operator cap may reduce, but never extend, the launch budget.
        limit_path = gm / "MAX_CONTINUES"
        if limit_path.exists():
            cap = int(limit_path.read_text(encoding="utf-8-sig").strip())
            if cap < 0:
                raise ValueError("negative MAX_CONTINUES")
            limit = min(limit, cap)
        deadline = datetime.fromisoformat(run["deadline_utc"].replace("Z", "+00:00"))
        if deadline.tzinfo is None:
            raise ValueError("deadline must have a timezone")
        now = now or datetime.now(timezone.utc)
        reason = None
        if run.get("status") != "active":
            reason = "run is " + str(run.get("status"))
        elif now >= deadline:
            run["status"], reason = "budget_exhausted", "deadline reached"
        elif count >= limit:
            run["status"], reason = "budget_exhausted", "continuation limit reached"
        if stop_flag.exists():
            run["status"], reason = "stopped", "STOP requested"
        if reason:
            run["stop_reason"] = reason
            atomic_json(gm / "run.json", run)
            run_flag.unlink(missing_ok=True)
            return None
        # Commit count before issuing continuation. Failed persistence cannot loop.
        run["continues"] = count + 1
        atomic_json(gm / "run.json", run)
        (gm / "logs").mkdir(exist_ok=True)
        (gm / "logs" / "continues.count").write_text(str(count + 1), encoding="utf-8")
        if stop_flag.exists():
            run_flag.unlink(missing_ok=True)
            return None
        return {
            "decision": "block",
            "reason": (
                f"Bounded AstraBlox run {run_id}, mode {mode}, continuation {count + 1}/{limit}. "
                f"Deadline UTC: {run['deadline_utc']}. "
                "Read gamemaster/run.json and the task checkpoint. Continue only the authorized "
                "objective using the Studio lease barrier. Honor newer owner instructions and STOP. "
                "If acceptance is satisfied, set run status complete; if externally blocked, set "
                "blocked with evidence; then release Studio/input and finish. At the deadline "
                "checkpoint and clean up. Do not start extra roadmap work or change the budget."
            ),
        }
    except Exception as error:
        # Stop safely; do not include payload/source/credentials in error text.
        run_flag.unlink(missing_ok=True)
        print("AstraBlox continuation disabled: invalid/unwritable run state (" +
              type(error).__name__ + "). Start a new bounded run after fixing it.", file=sys.stderr)
        return None
    finally:
        lock.unlink(missing_ok=True)


def main():
    try:
        payload = json.load(sys.stdin)
        response = evaluate(payload)
        if response:
            print(json.dumps(response))
    except Exception as error:
        print("AstraBlox Stop hook allowed stopping (" + type(error).__name__ + ").",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
