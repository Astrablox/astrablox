"""Stop hook fixtures (v1.0): the lead is pushed back to the board while it has work, and released otherwise.
Run: python -B tests/test_stop_hook.py
"""
import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("astra_stop_hook", ROOT / "scripts/hooks/stop_continue.py")
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class StopHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="astra-hook-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / "tools/board").mkdir(parents=True)
        for f in ("board.py", "lanes.json"):
            shutil.copy2(ROOT / "tools/board" / f, self.root / "tools/board" / f)
        (self.root / "board").mkdir()
        self.payload = {"hook_event_name": "Stop", "cwd": str(self.root), "session_id": "x"}

    def board(self, *args):
        return subprocess.run([sys.executable, str(self.root / "tools/board/board.py"), "--root", str(self.root), *args], capture_output=True, text=True)

    def test_no_session_stop_file_or_lane_allows_stop(self):
        self.assertIsNone(hook.evaluate(self.payload, {}))
        self.assertIsNone(hook.evaluate(self.payload, {"ASTRA_SESSION": "world"}))
        (self.root / "STOP").touch()
        self.assertIsNone(hook.evaluate(self.payload, {"ASTRA_SESSION": "lead"}))

    def test_lead_pushed_while_board_has_work_then_released(self):
        self.assertIsNone(hook.evaluate(self.payload, {"ASTRA_SESSION": "lead"}))
        r = self.board("new", "--lane", "world", "--scene", "pier", "--goal", "one lantern")
        self.assertEqual(r.returncode, 0, r.stderr)
        env = {"ASTRA_SESSION": "lead"}
        for i in range(hook.MAX_IDLE_CONTINUES):
            res = hook.evaluate(self.payload, env)
            self.assertIsNotNone(res, f"continue {i}"); self.assertEqual(res["decision"], "block")
        self.assertIsNone(hook.evaluate(self.payload, env))
        (self.root / "board/STATE.md").write_text("# state\nGoal: pier\n")
        self.assertIsNotNone(hook.evaluate(self.payload, env))

    def test_unfinished_plan_keeps_lead_going(self):
        (self.root / "game").mkdir(); (self.root / "game/PLAN.md").write_text("# Plan\n1. pier — the waterfront (status: open)\n")
        self.assertIsNotNone(hook.evaluate(self.payload, {"ASTRA_SESSION": "lead"}))
        (self.root / "game/PLAN.md").write_text("# Plan\n1. pier — the waterfront (status: accepted)\n")
        self.assertIsNone(hook.evaluate(self.payload, {"ASTRA_SESSION": "lead"}))


if __name__ == "__main__":
    unittest.main()
