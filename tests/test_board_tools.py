"""Board tools on a temporary copy of board/: board.py new/claim/done/next/return/report-check/signal,
supervisor --once reopening an overdue task, build_publish creating builds/<n>/ with CHANGES.md.
No codex binary is needed (signals log with NOQUEUE or --dry-run).
Run: python -B tests/test_board_tools.py
"""
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
BOARD = ROOT / "tools/board/board.py"
SUPERVISOR = ROOT / "tools/board/supervisor.py"
PUBLISH = ROOT / "tools/board/build_publish.py"


def run(*args, root, env=None, check=True):
    e = dict(os.environ, ASTRA_ROOT=str(root))
    if env:
        e.update(env)
    r = subprocess.run([sys.executable, "-B", *map(str, args)], capture_output=True, text=True, timeout=60, env=e, cwd=root)
    if check and r.returncode != 0:
        raise AssertionError(f"{args} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r


class TempStudio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="astra-board-")
        self.root = pathlib.Path(self.tmp)
        shutil.copytree(ROOT / "board", self.root / "board", ignore=shutil.ignore_patterns("tasks", "reports", "heartbeats", "*.log"))
        shutil.copytree(ROOT / "game", self.root / "game")
        (self.root / "assets/world/pier").mkdir(parents=True)
        (self.root / "assets/world/pier/pier.glb").write_bytes(b"glb")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def card(self, tid):
        return (self.root / "board/tasks" / f"{tid}.md").read_text(encoding="utf-8")

    def report(self, tid, status="DONE", delivered="assets/world/pier/pier.glb glb_verified"):
        p = self.root / "board/reports" / f"{tid}.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text("\n".join([
            "The pier reads as the target from the far camera; the near camera shows flat planks.", "",
            f"DELIVERED: {delivered}", "EVIDENCE: out/renders/final_far.png", "ASSUMPTIONS: none",
            "WEAKEST: plank texture", "OPEN: -", f"STATUS: {status}", ""]), encoding="utf-8")
        return p


class BoardTests(TempStudio):
    def new(self, lane="world", **kw):
        args = ["new", "--lane", lane, "--scene", "harbour", "--goal", "Build the pier kit",
                "--input", "game/scenes/harbour/target.png", "--output", "assets/world/pier/pier.glb",
                "--acceptance", "verify OK", "--must-survive", "quay pieces"]
        for k, v in kw.items():
            args += [f"--{k}", *(v if isinstance(v, list) else [v])]
        return run(BOARD, *args, root=self.root).stdout.strip()

    def test_new_card_matches_contract(self):
        tid = self.new()
        self.assertEqual(tid, "001")
        text = self.card(tid)
        head = text.split("---")[1]
        for key in ("id: 001", "lane: world", "scene: harbour", "status: open", "created: ", "claimed_by:", "claimed_at:", "deadline:", "depends_on: []"):
            self.assertIn(key, head, text)
        body = text.split("---", 2)[2]
        order = [body.index(f"## {s}") for s in ("Goal", "Input", "Output", "Acceptance", "Must survive", "Notes")]
        self.assertEqual(order, sorted(order), "sections out of §4 order")
        self.assertEqual(self.new(), "002")

    def test_claim_refuses_wrong_lane_and_status(self):
        tid = self.new()
        r = run(BOARD, "claim", tid, "--lane", "code", root=self.root, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("belongs to lane world", r.stderr)
        run(BOARD, "claim", tid, "--lane", "world", root=self.root)
        text = self.card(tid)
        self.assertIn("status: claimed", text); self.assertIn("claimed_by: world", text)
        self.assertTrue((self.root / "board/heartbeats/world.json").exists())
        r = run(BOARD, "claim", tid, "--lane", "world", root=self.root, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("is claimed", r.stderr)

    def test_next_respects_depends_on(self):
        a = self.new()
        b = self.new(depends=[a])
        self.assertEqual(run(BOARD, "next", "--lane", "world", root=self.root).stdout.split()[0], a)
        run(BOARD, "claim", a, "--lane", "world", root=self.root)
        self.assertEqual(run(BOARD, "next", "--lane", "world", root=self.root).stdout.strip(), "NONE")
        run(BOARD, "done", a, "--report", self.report(a), root=self.root)
        self.assertEqual(run(BOARD, "next", "--lane", "world", root=self.root).stdout.split()[0], b)
        self.assertEqual(run(BOARD, "next", "--lane", "vfx", root=self.root).stdout.strip(), "NONE")

    def test_done_needs_complete_report(self):
        tid = self.new()
        run(BOARD, "claim", tid, "--lane", "world", root=self.root)
        bad = self.root / "board/reports" / f"{tid}.md"; bad.parent.mkdir(exist_ok=True)
        bad.write_text("DELIVERED: assets/world/pier/pier.glb\nSTATUS: DONE\n", encoding="utf-8")
        r = run(BOARD, "done", tid, "--report", bad, root=self.root, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("missing marker EVIDENCE:", r.stderr)
        self.report(tid, delivered="assets/world/pier/missing.glb")
        r = run(BOARD, "done", tid, "--report", bad, root=self.root, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("does not exist", r.stderr)
        self.report(tid, status="BLOCKED")
        r = run(BOARD, "done", tid, "--report", bad, root=self.root, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("STATUS must be DONE", r.stderr)
        run(BOARD, "blocked", tid, "--report", bad, root=self.root)
        self.assertIn("status: blocked", self.card(tid))

    def test_return_is_one_round(self):
        tid = self.new()
        run(BOARD, "claim", tid, "--lane", "world", root=self.root)
        run(BOARD, "done", tid, "--report", self.report(tid), root=self.root)
        run(BOARD, "return", tid, "--notes", "far camera: roof pitch too low", "--from", "lead", root=self.root)
        text = self.card(tid)
        self.assertIn("status: returned", text); self.assertIn("## Return", text); self.assertIn("roof pitch too low", text)
        run(BOARD, "claim", tid, "--lane", "world", root=self.root)
        run(BOARD, "done", tid, "--report", self.report(tid), root=self.root)
        r = run(BOARD, "return", tid, "--notes", "again", root=self.root, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("inventory.md", r.stderr)

    def test_report_check_cli(self):
        p = self.report("009")
        self.assertIn("OK", run(BOARD, "report-check", p, root=self.root).stdout)
        p.write_text(p.read_text(encoding="utf-8").replace("WEAKEST:", "WEAK:"), encoding="utf-8")
        r = run(BOARD, "report-check", p, root=self.root, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("WEAKEST:", r.stdout)

    def test_signal_logs_and_validates(self):
        r = run(BOARD, "signal", "--to", "world", "TASK 001 OPEN board/tasks/001.md", "--dry-run", root=self.root, env={"ASTRA_SESSION": "lead"})
        self.assertIn("codex queue --session world", r.stdout)
        log = (self.root / "board/queue.log").read_text(encoding="utf-8")
        self.assertIn("from=lead to=world TASK 001 OPEN board/tasks/001.md [DRYRUN]", log)
        r = run(BOARD, "signal", "--to", "world", "please build the pier", root=self.root, check=False)
        self.assertEqual(r.returncode, 1); self.assertIn("§3", r.stderr)
        r = run(BOARD, "signal", "--to", "nobody", "WAKE", root=self.root, check=False)
        self.assertEqual(r.returncode, 1)
        if shutil.which("codex") is None:
            run(BOARD, "signal", "--to", "lead", "BUILD 3 READY builds/003/", root=self.root)
            self.assertIn("[NOQUEUE]", (self.root / "board/queue.log").read_text(encoding="utf-8"))

    def test_list_show_state_heartbeat(self):
        tid = self.new()
        self.assertIn("harbour", run(BOARD, "list", "--lane", "world", "--status", "open", root=self.root).stdout)
        self.assertIn("## Goal", run(BOARD, "show", tid, root=self.root).stdout)
        self.assertIn("Studio state", run(BOARD, "state", root=self.root).stdout)
        run(BOARD, "heartbeat", "--session", "vfx", "--task", tid, root=self.root)
        hb = json.loads((self.root / "board/heartbeats/vfx.json").read_text(encoding="utf-8"))
        self.assertEqual((hb["session"], hb["task"]), ("vfx", tid)); self.assertIn("T", hb["time"])


class SupervisorTests(TempStudio):
    def test_once_reopens_overdue_and_wakes(self):
        run(BOARD, "new", "--lane", "world", "--scene", "harbour", "--goal", "x", root=self.root)
        run(BOARD, "claim", "001", "--lane", "world", "--hours", "0", root=self.root)
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=9)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        p = self.root / "board/tasks/001.md"
        lines = [f"claimed_at: {old}" if l.startswith("claimed_at:") else l for l in p.read_text(encoding="utf-8").splitlines()]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        hb = self.root / "board/heartbeats/world.json"
        hb.write_text(json.dumps({"session": "world", "time": old, "task": "001"}), encoding="utf-8")
        run(BOARD, "new", "--lane", "vfx", "--scene", "harbour", "--goal", "y", root=self.root)  # vfx has no heartbeat at all
        r = run(SUPERVISOR, "--once", "--task-hours", "4", "--stale", "15", root=self.root)
        res = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(res["reopened"], ["001"])
        self.assertIn("vfx", res["missing"]); self.assertIn("codex --session-name vfx", r.stdout)
        text = p.read_text(encoding="utf-8")
        self.assertIn("status: open", text); self.assertIn("claimed_by: \n", text); self.assertIn("supervisor: returned to open", text.split("## Notes")[1])
        self.assertTrue((self.root / "board/supervisor.log").exists())
        # second pass: the reopened world task + stale heartbeat -> WAKE world
        r = run(SUPERVISOR, "--once", root=self.root)
        res = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertIn("world", res["woke"])
        self.assertIn("to=world WAKE", (self.root / "board/queue.log").read_text(encoding="utf-8"))

    def test_stop_file(self):
        (self.root / "STOP").write_text("stop", encoding="utf-8")
        r = run(SUPERVISOR, "--once", root=self.root)
        res = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(res["stopped"])
        log = (self.root / "board/queue.log").read_text(encoding="utf-8")
        self.assertIn("to=lead STOP", log); self.assertIn("to=dev STOP", log)


class BuildPublishTests(TempStudio):
    def test_publish_creates_folder_and_changes(self):
        renders = self.root / "work/renders"; renders.mkdir(parents=True)
        target = self.root / "game/scenes/harbour/target.png"; target.parent.mkdir(parents=True)
        shutil.copy(ROOT / "game/scenes/_template/card.md", target.parent / "card.md")
        try:
            from PIL import Image
            Image.new("RGB", (64, 36), (90, 120, 200)).save(renders / "final_far.png")
            Image.new("RGB", (64, 36), (200, 150, 90)).save(target)
            have_pil = True
        except ImportError:
            (renders / "final_far.png").write_bytes(b"png"); target.write_bytes(b"png"); have_pil = False
        r = run(PUBLISH, "--scene", "harbour", "--renders", renders, "--target", target, "--changes", "pier kit in", root=self.root)
        self.assertIn("BUILD 1 READY builds/001/", r.stdout.strip().splitlines()[-1])
        folder = self.root / "builds/001"
        self.assertTrue((folder / "renders/final_far.png").exists()); self.assertTrue((folder / "target.png").exists())
        changes = (folder / "CHANGES.md").read_text(encoding="utf-8")
        self.assertIn("pier kit in", changes); self.assertIn("builds/001/renders/final_far.png", changes)
        if have_pil:
            self.assertTrue((folder / "side_by_side_final_far.png").exists())
        self.assertIn("Current build: 1  (builds/001/)", (target.parent / "card.md").read_text(encoding="utf-8"))
        r = run(PUBLISH, "--scene", "harbour", "--renders", renders, "--target", target, "--changes", "second", root=self.root)
        self.assertIn("BUILD 2 READY builds/002/", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
