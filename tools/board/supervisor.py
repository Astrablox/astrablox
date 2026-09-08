#!/usr/bin/env python3
"""supervisor.py: deterministic watchdog of the studio bus (docs/v0.3-contract.md §2, §3).

What it does, every --interval seconds (default 120), for each session in tools/board/lanes.json:
  - the lane has open/returned tasks with satisfied depends_on and its heartbeat is missing or older
    than --stale minutes: sends `WAKE` through board.py signal (logged in board/queue.log);
    a session with no heartbeat file at all is reported as MISSING with the restart command
    `codex --session-name <lane>` (start it with scripts/run_studio.ps1 -Lanes <lane>); nothing is launched here;
  - a `claimed` task whose deadline (or claimed_at + --task-hours when the card has no deadline) has
    passed while the owner's heartbeat is missing or older than --stale minutes: sets status back to
    `open`, clears claimed_by/claimed_at and appends a line to the card's **Notes**;
  - a file named STOP in the checkout root: sends `STOP` to every session, logs it and exits.
Writes board/supervisor.log (one line per action). Prints the same lines to stdout.

When to use: started once by scripts/run_studio.* in its own window; lanes never run it themselves.
Returns: exit 0; with --once a single pass (tests); --dry-run performs no signal and no card change.

Examples:
  supervisor.py                       # loop forever with defaults
  supervisor.py --once --dry-run      # show what would happen now
  supervisor.py --stale 10 --task-hours 6 --interval 60
"""
import argparse
import datetime as dt
import importlib.util
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("astra_board", HERE / "board.py")
board = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(board)


def log(root, line, dry):
    stamp = f"{board.now_iso()} {line}"
    print(stamp, flush=True)
    if not dry:
        p = root / "board" / "supervisor.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(stamp + "\n")


def age_minutes(hb, now):
    if not hb:
        return None
    t = board.parse_iso(hb.get("time", ""))
    return (now - t).total_seconds() / 60 if t else None


def one_pass(root, stale_min, task_hours, dry, now=None):
    """Return a dict with lists: woke, missing, reopened, stopped."""
    now = now or dt.datetime.now(dt.timezone.utc)
    b = board.Board(root)
    lane_names = board.lanes()
    out = {"woke": [], "missing": [], "reopened": [], "stopped": False}

    if (root / "STOP").exists():
        for lane in lane_names:
            if not dry:
                board.send_signal(root, lane, "STOP", "supervisor")
        log(root, "STOP file present: STOP sent to all sessions, exiting", dry)
        out["stopped"] = True
        return out

    for lane in lane_names:
        hb = b.heartbeat_of(lane)
        age = age_minutes(hb, now)
        pending = b.next_for(lane)
        if pending is None:
            continue
        if hb is None:
            out["missing"].append(lane)
            log(root, f"MISSING {lane}: task {pending['id']} open, no heartbeat; restart with: codex --session-name {lane}", dry)
        elif age is None or age > stale_min:
            out["woke"].append(lane)
            log(root, f"WAKE {lane}: task {pending['id']} open, heartbeat {round(age) if age is not None else '?'} min old", dry)
            if not dry:
                board.send_signal(root, lane, "WAKE", "supervisor")

    for front, body in b.all():
        if front.get("status") != "claimed":
            continue
        deadline = board.parse_iso(front.get("deadline"))
        if deadline is None:
            claimed = board.parse_iso(front.get("claimed_at"))
            deadline = claimed + dt.timedelta(hours=task_hours) if claimed else None
        if deadline is None or now <= deadline:
            continue
        owner = front.get("claimed_by", "")
        age = age_minutes(b.heartbeat_of(owner), now) if owner else None
        if age is not None and age <= stale_min:
            continue
        note = f"{board.now_iso()} supervisor: returned to open, deadline {front.get('deadline') or deadline.isoformat()} passed and {owner or 'owner'} heartbeat " + ("missing" if age is None else f"{round(age)} min old")
        out["reopened"].append(front["id"])
        log(root, f"REOPEN {front['id']} ({owner}): {note}", dry)
        if not dry:
            front.update(status="open", claimed_by="", claimed_at="")
            b.write(front["id"], front, board.append_to_section(body, "Notes", note))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="supervisor.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root"); ap.add_argument("--interval", type=float, default=120, help="seconds between passes")
    ap.add_argument("--stale", type=float, default=15, help="minutes without heartbeat before a session counts as idle")
    ap.add_argument("--task-hours", type=float, default=4, help="default task deadline after claimed_at when the card has none")
    ap.add_argument("--once", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    root = board.find_root(a.root)
    log(root, f"supervisor start root={root} stale={a.stale}min task_hours={a.task_hours} dry={a.dry_run}", a.dry_run)
    while True:
        res = one_pass(root, a.stale, a.task_hours, a.dry_run)
        if a.once:
            print(json.dumps(res))
            return 0
        if res["stopped"]:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
