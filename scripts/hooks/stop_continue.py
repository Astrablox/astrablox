"""Stop hook of a lane session (v0.3). Keeps a lane working while the board has work for it.

Codex fires this hook when a session is about to end its turn. Inside the studio every session runs
with ASTRA_SESSION=<lane> (set by scripts/run_studio.*). The hook lets the turn end unless all of
these hold: ASTRA_SESSION is set; no STOP file exists in the checkout root; the lane has a claimable
task (board.py next) or, for the lead, any task on the board is not done; and the lane has not been
pushed more than MAX_IDLE_CONTINUES times in a row without touching its heartbeat. Then it blocks the
stop with a short instruction to continue from the board. Fail closed: any error allows the stop.
The supervisor's WAKE signal covers the cases this hook lets through.
"""
import json
import os
import pathlib
import subprocess
import sys

MAX_IDLE_CONTINUES = 3


def _counter_path(root, session):
    return root / "board" / "heartbeats" / f"{session}.continue.json"


def evaluate(payload, environment=None):
    environment = os.environ if environment is None else environment
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "Stop":
        return None
    session = environment.get("ASTRA_SESSION")
    cwd = payload.get("cwd")
    if not session or not cwd or session == "supervisor":
        return None
    root = pathlib.Path(cwd).resolve()
    if (root / "STOP").exists():
        return None
    board = root / "tools" / "board" / "board.py"
    if not board.exists():
        return None
    try:
        hb = root / "board" / "heartbeats" / f"{session}.json"
        stamp = hb.read_text(encoding="utf-8") if hb.exists() else ""   # read before board.py next, which refreshes it
        if session == "lead":
            out = subprocess.run([sys.executable, str(board), "--root", str(root), "list"], capture_output=True, text=True, timeout=20).stdout
            pending = any(s in out for s in (" open", " claimed", " returned", " blocked"))
            if not pending:
                return None
            instruction = "Continue the scene cycle from board/STATE.md and the scene card: accept finished cards by their artifacts, publish the next build, dispatch the next cards."
        else:
            out = subprocess.run([sys.executable, str(board), "--root", str(root), "next", "--lane", session], capture_output=True, text=True, timeout=20)
            if out.returncode != 0 or not out.stdout.strip() or out.stdout.strip().startswith("NONE"):
                return None
            instruction = f"A task is waiting for the {session} lane: run `python tools/board/board.py next --lane {session}`, claim it, refresh the heartbeat, do the work, report with board.py done."
        cp = _counter_path(root, session)
        state = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {"stamp": None, "count": 0}
        count = state["count"] + 1 if state.get("stamp") == stamp else 1
        if count > MAX_IDLE_CONTINUES:
            return None
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps({"stamp": stamp, "count": count}), encoding="utf-8")
        return {"decision": "block", "reason": f"AstraBlox {session}: {instruction} STOP file absent; continuation {count}/{MAX_IDLE_CONTINUES} without new heartbeat."}
    except Exception:
        return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    response = evaluate(payload)
    if response:
        print(json.dumps(response))


if __name__ == "__main__":
    main()
