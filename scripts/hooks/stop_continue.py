"""Stop hook of a studio instance (v1.0). Keeps the lead working while the board has work.

Codex fires this hook when a session is about to end its turn. A studio instance runs with
ASTRA_SESSION=lead (set by scripts/run_studio.*). The hook lets the turn end unless all of these hold:
ASTRA_SESSION is "lead"; no STOP file exists in the checkout root; the board has a task that is not
done (open, claimed, returned or blocked) or a scene in game/PLAN.md is not accepted; and the lead has
not been pushed more than MAX_IDLE_CONTINUES times in a row without board/STATE.md changing. Then it
blocks the stop with a short instruction to continue from the board. Fail closed: any error allows the
stop. Lanes are subagents, not sessions, so the hook never applies to them.
"""
import json
import os
import pathlib
import subprocess
import sys

MAX_IDLE_CONTINUES = 3


def evaluate(payload, environment=None):
    environment = os.environ if environment is None else environment
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "Stop":
        return None
    session = environment.get("ASTRA_SESSION")
    cwd = payload.get("cwd")
    if session != "lead" or not cwd:
        return None
    root = pathlib.Path(cwd).resolve()
    if (root / "STOP").exists():
        return None
    board = root / "tools" / "board" / "board.py"
    if not board.exists():
        return None
    try:
        out = subprocess.run([sys.executable, str(board), "--root", str(root), "list"], capture_output=True, text=True, timeout=20).stdout
        pending = any(s in out for s in (" open", " claimed", " returned", " blocked"))
        plan = root / "game" / "PLAN.md"
        unfinished_scene = plan.exists() and any(line.strip().startswith(("-", "1", "2", "3", "4", "5", "6", "7", "8", "9")) and "accepted" not in line.lower() for line in plan.read_text(encoding="utf-8").splitlines())
        if not pending and not unfinished_scene:
            return None
        state = root / "board" / "STATE.md"
        stamp = str(state.stat().st_mtime_ns) if state.exists() else ""
        cp = root / "board" / "lead.continue.json"
        prev = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {"stamp": None, "count": 0}
        count = prev["count"] + 1 if prev.get("stamp") == stamp else 1
        if count > MAX_IDLE_CONTINUES:
            return None
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps({"stamp": stamp, "count": count}), encoding="utf-8")
        return {"decision": "block", "reason": f"AstraBlox lead: the board still has work. Continue the scene cycle from board/STATE.md and the scene card: collect finished lanes by their artifacts, publish the next build, spawn the next cards. STOP file absent; continuation {count}/{MAX_IDLE_CONTINUES} without a change to STATE.md."}
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
