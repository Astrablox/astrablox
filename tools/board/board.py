#!/usr/bin/env python3
"""board.py: the task board of the AstraBlox studio (docs/contract.md §3-§6, §8).

What it does: creates, claims, closes and lists task cards in board/tasks/, checks reports in
board/reports/, sends bus signals through `codex queue` and records them in board/queue.log,
holds scene claims for parallel studio instances. Every lane uses it instead of editing cards by hand, so the
front matter, the section order and the queue log stay identical for everybody.

When to use: lead — `new` to dispatch a task, `return` to send it back once, `signal` after every
dispatch and acceptance. Any lane — `next` to find work, `claim` before starting, `done`/`blocked`
with a report when finished (next is a read-only query). Instances — `claim-scene <id>` before working a scene,
`release-scene <id> [--accepted]` after; `scenes` lists who holds what.

Returns: ids and file paths on stdout; exit 0 on success, 1 on a refusal (wrong lane, wrong
status, missing report marker, bad signal) with the reason on stderr.

Examples:
  board.py new --lane world --scene harbour --goal "Build the pier kit" --input game/scenes/harbour/target.png \\
      --output assets/world/pier/pier.glb --acceptance "export_glb.py verify OK; side-by-side reads as the target" \\
      --must-survive "existing quay pieces" --depends 041 042 --deadline 2026-09-09T18:00:00Z
  board.py next --lane world            # first open/returned card of the lane whose depends_on are done
  board.py claim 043 --lane world
  board.py done 043 --report board/reports/043.md
  board.py return 043 --notes "Silhouette flat from the far camera; roof pitch too low"
  board.py signal --to world "TASK 043 OPEN board/tasks/043.md"   # --dry-run prints, no codex call
  board.py report-check board/reports/043.md
  board.py claim-scene harbour ; board.py release-scene harbour --accepted ; board.py scenes
  board.py list --lane world --status open ; board.py show 043 ; board.py state

Root: the checkout root is found by walking up from the current directory to a folder that
contains board/; override with --root or the ASTRA_ROOT environment variable. The acting session
is taken from --from / --lane or the ASTRA_SESSION environment variable.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

STATUSES = ("open", "claimed", "done", "blocked", "returned")
FRONT_KEYS = ("id", "lane", "scene", "status", "created", "claimed_by", "claimed_at", "deadline", "depends_on")
SECTIONS = ("Goal", "Input", "Output", "Acceptance", "Must survive", "Notes")
REPORT_MARKERS = ("DELIVERED:", "EVIDENCE:", "ASSUMPTIONS:", "WEAKEST:", "OPEN:", "STATUS:")
SIGNAL_FORMS = [
    re.compile(r"^TASK \d+ (DONE|BLOCKED|RETURNED|OPEN) \S+$"),
    re.compile(r"^BUILD \d+ READY \S+$"),
    re.compile(r"^SCENE \S+ ACCEPTED$"),
    re.compile(r"^SCENE \S+ BLOCKED \S+$"),
    re.compile(r"^RETRO \S+ READY \S+$"),
    re.compile(r"^(WAKE|STOP)$"),
]
HERE = pathlib.Path(__file__).resolve().parent


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(s):
    if not s:
        return None
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def lanes():
    return [l["name"] for l in json.loads((HERE / "lanes.json").read_text(encoding="utf-8"))["lanes"]]


def find_root(explicit=None):
    if explicit:
        return pathlib.Path(explicit).resolve()
    env = os.environ.get("ASTRA_ROOT")
    if env:
        return pathlib.Path(env).resolve()
    p = pathlib.Path.cwd().resolve()
    for cand in (p, *p.parents):
        if (cand / "board").is_dir():
            return cand
    return p


class Board:
    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.tasks = self.root / "board" / "tasks"
        self.reports = self.root / "board" / "reports"
        for d in (self.tasks, self.reports):
            d.mkdir(parents=True, exist_ok=True)

    # ----- cards -----
    def path(self, tid):
        return self.tasks / f"{self.norm(tid)}.md"

    @staticmethod
    def norm(tid):
        tid = str(tid).strip()
        return tid.zfill(3) if tid.isdigit() else tid

    def next_id(self):
        nums = [int(p.stem) for p in self.tasks.glob("*.md") if p.stem.isdigit()]
        return f"{(max(nums) + 1) if nums else 1:03d}"

    def read(self, tid):
        p = self.path(tid)
        if not p.exists():
            raise SystemExit(f"no task {tid} at {p}")
        return parse_card(p.read_text(encoding="utf-8"))

    def write(self, tid, front, body):
        self.path(tid).write_text(render_card(front, body), encoding="utf-8")

    def all(self):
        return [parse_card(p.read_text(encoding="utf-8")) for p in sorted(self.tasks.glob("*.md"))]

    def deps_done(self, front):
        for d in front.get("depends_on", []):
            p = self.path(d)
            if not p.exists():
                return False
            if parse_card(p.read_text(encoding="utf-8"))[0].get("status") != "done":
                return False
        return True

    def next_for(self, lane):
        for front, _ in self.all():
            if front.get("lane") == lane and front.get("status") in ("open", "returned") and self.deps_done(front):
                return front
        return None


def parse_card(text):
    """Return (front: dict, body: str). depends_on is a list of ids."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        raise SystemExit("card has no front matter")
    front = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        front[k.strip()] = v.strip()
    deps = front.get("depends_on", "")
    front["depends_on"] = [d.strip() for d in deps.strip("[]").split(",") if d.strip()]
    return front, m.group(2)


def render_card(front, body):
    lines = ["---"]
    for k in FRONT_KEYS:
        v = front.get(k, "")
        if k == "depends_on":
            v = "[" + ", ".join(v) + "]"
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.rstrip("\n") + "\n"


def section(body, name):
    m = re.search(rf"^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    return m.group(1).strip() if m else ""


def append_to_section(body, name, text):
    """Append text to section `name`; create the section at the end when it is missing."""
    m = re.search(rf"^## {re.escape(name)}\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    if not m:
        return body.rstrip("\n") + f"\n\n## {name}\n{text}\n"
    old = m.group(1).rstrip("\n")
    new = (old + "\n" if old else "") + text + "\n\n"
    return body[: m.start(1)] + new + body[m.end(1):]


def lines_or_dash(items):
    return "\n".join(f"- {i}" for i in items) if items else "-"


def acting_session(args):
    return getattr(args, "from_", None) or getattr(args, "lane", None) or os.environ.get("ASTRA_SESSION", "")


# ----- report check -----
def check_report(path, root):
    """Return a list of problems (empty = report complete). Paths under DELIVERED: must exist relative to root."""
    p = pathlib.Path(path)
    if not p.exists():
        return [f"report not found: {path}"]
    text = p.read_text(encoding="utf-8")
    problems = []
    for marker in REPORT_MARKERS:
        if not re.search(rf"^{re.escape(marker)}", text, re.M):
            problems.append(f"missing marker {marker}")
    m = re.search(r"^STATUS:\s*(\S+)", text, re.M)
    if m and m.group(1) not in ("DONE", "BLOCKED"):
        problems.append(f"STATUS must be DONE or BLOCKED, got {m.group(1)}")
    for line in delivered_lines(text):
        first = line.split()[0] if line.split() else ""
        if not first:
            continue
        cand = pathlib.Path(first)
        if not (cand.is_absolute() and cand.exists()) and not (root / first).exists():
            problems.append(f"DELIVERED path does not exist: {first}")
    return problems


def delivered_lines(text):
    """Lines of the DELIVERED block: the marker line's remainder plus following indented/bulleted lines up to the next marker."""
    out = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("DELIVERED:"):
            rest = lines[i][len("DELIVERED:"):].strip()
            if rest:
                out.append(rest)
            i += 1
            while i < len(lines) and not any(lines[i].startswith(mk) for mk in REPORT_MARKERS) and not re.match(r"^[A-Z_]+:", lines[i]):
                s = lines[i].strip().lstrip("-*").strip()
                if s:
                    out.append(s)
                i += 1
            continue
        i += 1
    return [o for o in out if o and o != "-"]


# ----- signal -----
def send_signal(root, to, text, sender="", dry_run=False):
    """Validate the signal against §3, run `codex queue`, append to board/queue.log. Returns the log line."""
    text = text.strip()
    if not any(f.match(text) for f in SIGNAL_FORMS):
        raise SystemExit(f"signal does not match §3 forms: {text!r}")
    if to not in lanes():
        raise SystemExit(f"unknown session {to!r}; sessions: {', '.join(lanes())}")
    cmd = ["codex", "queue", "--session", to, text]
    tag = ""
    if dry_run:
        tag = "DRYRUN"
        print("+", " ".join(cmd))
    elif shutil.which("codex") is None:
        tag = "NOQUEUE"
    else:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            tag = f"FAILED({r.returncode})"
            sys.stderr.write(r.stderr)
    line = f"{now_iso()} from={sender or '-'} to={to} {text}" + (f" [{tag}]" if tag else "")
    log = root / "board" / "queue.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)
    return line


# ----- commands -----
def cmd_new(b, a):
    tid = b.next_id()
    front = {"id": tid, "lane": a.lane, "scene": a.scene, "status": "open", "created": now_iso(),
             "claimed_by": "", "claimed_at": "", "deadline": a.deadline or "", "depends_on": [b.norm(d) for d in a.depends or []]}
    body = "\n".join([
        "## Goal", a.goal.strip(), "",
        "## Input", lines_or_dash(a.input), "",
        "## Output", lines_or_dash(a.output), "",
        "## Acceptance", (a.acceptance or "As in the lane file.").strip(), "",
        "## Must survive", (a.must_survive or "-").strip(), "",
        "## Notes", (a.notes or "-").strip(),
    ])
    b.write(tid, front, body)
    print(tid)


def cmd_claim(b, a):
    front, body = b.read(a.id)
    if front["lane"] != a.lane:
        raise SystemExit(f"task {front['id']} belongs to lane {front['lane']}, not {a.lane}")
    if front["status"] not in ("open", "returned"):
        raise SystemExit(f"task {front['id']} is {front['status']}, only open/returned can be claimed")
    if not b.deps_done(front):
        raise SystemExit(f"task {front['id']} waits on depends_on {front['depends_on']}")
    front.update(status="claimed", claimed_by=a.lane, claimed_at=now_iso())
    if not front.get("deadline") and a.hours:
        front["deadline"] = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=a.hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    b.write(front["id"], front, body)
    print(f"claimed {front['id']} by {a.lane} deadline {front.get('deadline') or '-'}")


def cmd_close(b, a, status):
    front, body = b.read(a.id)
    if front["status"] != "claimed":
        raise SystemExit(f"task {front['id']} is {front['status']}, only claimed tasks can be closed")
    problems = check_report(a.report, b.root)
    text = pathlib.Path(a.report).read_text(encoding="utf-8") if pathlib.Path(a.report).exists() else ""
    want = "DONE" if status == "done" else "BLOCKED"
    if text and not re.search(rf"^STATUS:\s*{want}\b", text, re.M):
        problems.append(f"report STATUS must be {want} for `{status}`")
    if problems:
        raise SystemExit("report incomplete:\n  " + "\n  ".join(problems))
    front["status"] = status
    b.write(front["id"], front, body)
    print(f"{status} {front['id']} report {a.report}")


def cmd_return(b, a):
    front, body = b.read(a.id)
    if front["status"] not in ("done", "blocked", "claimed"):
        raise SystemExit(f"task {front['id']} is {front['status']}; return applies to done/blocked/claimed")
    if section(body, "Return") and not a.force:
        raise SystemExit(f"task {front['id']} was already returned once (one round, §4); what remains goes to studio/inventory.md. Use --force to override.")
    notes = a.notes
    if pathlib.Path(notes).is_file():
        notes = pathlib.Path(notes).read_text(encoding="utf-8").strip()
    body = append_to_section(body, "Return", f"{now_iso()} by {acting_session(a) or 'lead'}:\n{notes}")
    front["status"] = "returned"
    b.write(front["id"], front, body)
    print(f"returned {front['id']}")


def cmd_list(b, a):
    rows = [f for f, _ in b.all() if (not a.lane or f["lane"] == a.lane) and (not a.status or f["status"] == a.status) and (not a.scene or f["scene"] == a.scene)]
    for f in rows:
        deps = ",".join(f["depends_on"]) or "-"
        print(f"{f['id']}  {f['status']:<8} {f['lane']:<9} {f['scene']:<12} deps={deps:<10} by={f.get('claimed_by') or '-'}")
    if not rows:
        print("(no tasks)")


def cmd_show(b, a):
    print(b.path(a.id).read_text(encoding="utf-8"))


def cmd_next(b, a):
    if a.lane not in lanes():
        raise SystemExit(f"unknown lane {a.lane}")
    f = b.next_for(a.lane)
    if f:
        print(f"{f['id']} {b.path(f['id']).relative_to(b.root).as_posix()}")
    else:
        print("NONE")


def cmd_signal(b, a):
    send_signal(b.root, a.to, a.text, acting_session(a), a.dry_run)


def cmd_state(b, a):
    p = b.root / "board" / "STATE.md"
    print(p.read_text(encoding="utf-8") if p.exists() else f"(no {p})")


def _scene_path(b, scene):
    d = b.root / "board" / "scenes"; d.mkdir(parents=True, exist_ok=True)
    return d / f"{scene}.json"


def cmd_claim_scene(b, a):
    p = _scene_path(b, a.scene)
    who = a.by or os.environ.get("ASTRA_INSTANCE") or os.environ.get("ASTRA_SESSION") or f"pid-{os.getpid()}"
    if p.exists():
        cur = json.loads(p.read_text(encoding="utf-8"))
        if cur.get("status") == "claimed" and cur.get("by") != who:
            raise SystemExit(f"scene {a.scene} is held by {cur.get('by')} since {cur.get('since')}")
        if cur.get("status") == "accepted":
            raise SystemExit(f"scene {a.scene} is already accepted")
    p.write_text(json.dumps({"scene": a.scene, "status": "claimed", "by": who, "since": now_iso()}, indent=1), encoding="utf-8")
    print(f"{a.scene} claimed by {who}")


def cmd_release_scene(b, a):
    p = _scene_path(b, a.scene)
    rec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"scene": a.scene}
    rec.update(status="accepted" if a.accepted else "open", released=now_iso())
    p.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"{a.scene} {rec['status']}")


def cmd_scenes(b, a):
    d = b.root / "board" / "scenes"
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        r = json.loads(p.read_text(encoding="utf-8")); print(f"{r.get('scene'):12} {r.get('status'):9} {r.get('by', '')} {r.get('since', '')}")


def cmd_report_check(b, a):
    problems = check_report(a.path, b.root)
    if problems:
        print("INCOMPLETE " + a.path)
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print("OK " + a.path)


def build_parser():
    ap = argparse.ArgumentParser(prog="board.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="checkout root (default: walk up to a folder with board/, or $ASTRA_ROOT)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="create a task card, print its id")
    p.add_argument("--lane", required=True, choices=lanes())
    p.add_argument("--scene", required=True)
    p.add_argument("--goal", required=True)
    p.add_argument("--input", action="append", default=[], metavar="PATH")
    p.add_argument("--output", action="append", default=[], metavar="PATH")
    p.add_argument("--acceptance")
    p.add_argument("--must-survive", dest="must_survive")
    p.add_argument("--notes")
    p.add_argument("--depends", nargs="*", default=[], metavar="ID")
    p.add_argument("--deadline", help="ISO time, e.g. 2026-09-09T18:00:00Z")
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("claim", help="claim an open/returned task for a lane")
    p.add_argument("id"); p.add_argument("--lane", required=True, choices=lanes())
    p.add_argument("--hours", type=float, default=4.0, help="deadline = now + hours when the card has none (0 = leave empty)")
    p.set_defaults(fn=cmd_claim)

    for name in ("done", "blocked"):
        p = sub.add_parser(name, help=f"mark a claimed task {name}; the report must pass report-check with STATUS {name.upper()}")
        p.add_argument("id"); p.add_argument("--report", required=True)
        p.set_defaults(fn=lambda b, a, s=name: cmd_close(b, a, s))

    p = sub.add_parser("return", help="return a task to its lane with addressed notes (one round)")
    p.add_argument("id"); p.add_argument("--notes", required=True, help="text or path to a file with the addressed list")
    p.add_argument("--from", dest="from_"); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_return)

    p = sub.add_parser("list", help="list tasks"); p.add_argument("--lane"); p.add_argument("--status", choices=STATUSES); p.add_argument("--scene")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show", help="print a task card"); p.add_argument("id"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("next", help="first open/returned task of a lane whose depends_on are done (prints NONE if none)")
    p.add_argument("--lane", required=True); p.set_defaults(fn=cmd_next)

    p = sub.add_parser("signal", help="send a §3 signal with `codex queue` and log it to board/queue.log")
    p.add_argument("--to", required=True); p.add_argument("text", help='one line, e.g. "TASK 043 OPEN board/tasks/043.md"')
    p.add_argument("--from", dest="from_", help="sender (default $ASTRA_SESSION)"); p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_signal)

    sub.add_parser("state", help="print board/STATE.md").set_defaults(fn=cmd_state)
    p = sub.add_parser("claim-scene", help="claim a scene for this studio instance (refused when another instance holds it)")
    p.add_argument("scene"); p.add_argument("--by", default=None); p.set_defaults(fn=cmd_claim_scene)
    p = sub.add_parser("release-scene", help="release a scene claim; --accepted records the scene as accepted")
    p.add_argument("scene"); p.add_argument("--accepted", action="store_true"); p.set_defaults(fn=cmd_release_scene)
    sub.add_parser("scenes", help="list scene claims").set_defaults(fn=cmd_scenes)
    p = sub.add_parser("report-check", help="check §5 markers and that every DELIVERED path exists (exit 1 when incomplete)")
    p.add_argument("path"); p.set_defaults(fn=cmd_report_check)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    b = Board(find_root(a.root))
    a.fn(b, a)


if __name__ == "__main__":
    main()
