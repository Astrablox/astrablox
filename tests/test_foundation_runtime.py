"""Isolated bounded-runtime fixtures; no real Codex sessions or live Studio access.
Run: python tests/test_foundation_runtime.py
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts/hooks/stop_continue.py"
spec = importlib.util.spec_from_file_location("astra_stop_hook", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)
SESSION = "00000000-0000-0000-0000-000000000001"
RUN = "00000000-0000-0000-0000-000000000002"


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="astra-hook-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.gm = self.root / "gamemaster"
        self.gm.mkdir()
        (self.gm / "RUN").write_text(RUN)
        self.now = datetime.now(timezone.utc)
        self.run = dict(run_id=RUN, workspace=str(self.root), session_id=None,
                        mode="BUILD", status="active", max_continues=2, continues=0,
                        deadline_utc=(self.now + timedelta(minutes=10)).isoformat())
        self.save()
        self.payload = dict(hook_event_name="Stop", cwd=str(self.root), session_id=SESSION)

    def save(self):
        (self.gm / "run.json").write_text(json.dumps(self.run))

    def call(self, payload=None, env=None):
        return hook.evaluate(self.payload if payload is None else payload,
                             {"ASTRA_RUN_ID": RUN} if env is None else env, self.now)

    def test_finite_continuations_and_disarm(self):
        self.assertEqual(self.call()["decision"], "block")
        self.assertEqual(self.call()["decision"], "block")
        self.assertIsNone(self.call())
        state = hook.read_json(self.gm / "run.json")
        self.assertEqual(state["continues"], 2)
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertFalse((self.gm / "RUN").exists())
        self.assertEqual(hook.read_json(self.gm / "session.json")["session_id"], SESSION)

    def test_improve_mode_continues_like_build(self):
        self.run["mode"] = "IMPROVE"
        self.save()
        self.assertEqual(self.call()["decision"], "block")
        self.run["mode"] = "DEPLOY"
        self.save()
        self.assertIsNone(self.call())
        self.assertFalse((self.gm / "RUN").exists())

    def test_zero_budget_initial_turn_only(self):
        self.run["max_continues"] = 0
        self.save()
        self.assertIsNone(self.call())

    def test_deadline(self):
        self.run["deadline_utc"] = (self.now - timedelta(seconds=1)).isoformat()
        self.save()
        self.assertIsNone(self.call())
        self.assertEqual(hook.read_json(self.gm / "run.json")["status"], "budget_exhausted")

    def test_stop_and_complete(self):
        (self.gm / "STOP").touch()
        self.assertIsNone(self.call())
        (self.gm / "STOP").unlink()
        self.run["status"] = "complete"
        self.save()
        self.assertIsNone(self.call())
        self.assertFalse((self.gm / "RUN").exists())

    def test_wrong_run_session_and_subagent_do_not_consume(self):
        self.assertIsNone(self.call(env={}))
        self.assertIsNone(self.call(env={"ASTRA_RUN_ID": "other"}))
        other = dict(self.payload, hook_event_name="SubagentStop")
        self.assertIsNone(self.call(payload=other))
        self.run["session_id"] = "00000000-0000-0000-0000-000000000099"
        self.save()
        self.assertIsNone(self.call())
        self.assertEqual(hook.read_json(self.gm / "run.json")["continues"], 0)

    def test_invalid_budget_fails_closed(self):
        self.run["max_continues"] = "forever"
        self.save()
        self.assertIsNone(self.call())
        self.assertFalse((self.gm / "RUN").exists())

    def test_cap_cannot_extend_launch_limit(self):
        (self.gm / "MAX_CONTINUES").write_text("99")
        self.call()
        self.call()
        self.assertIsNone(self.call())

    def test_cap_can_reduce_limit(self):
        (self.gm / "MAX_CONTINUES").write_text("0")
        self.assertIsNone(self.call())

    def test_lock_contention_allows_stopping(self):
        (self.gm / "hook.lock").touch()
        self.assertIsNone(self.call())
        self.assertEqual(hook.read_json(self.gm / "run.json")["continues"], 0)


@unittest.skipUnless(os.name == "nt", "PowerShell launcher fixtures run on Windows")
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="astra-launch-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scripts = self.root / "scripts"
        self.scripts.mkdir()
        for name in ("run.ps1", "stop.ps1"):
            shutil.copy2(ROOT / "scripts" / name, self.scripts / name)
        self.mockbin = self.root / "mockbin"
        self.mockbin.mkdir()
        (self.mockbin / "codex.ps1").write_text(
            '$args | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $env:MOCK_ROOT "calls.jsonl")\n'
            'Write-Output \'{"type":"thread.started","thread_id":"' + SESSION + '"}\'\n'
            'if ($env:MOCK_EXIT) { exit ([int]$env:MOCK_EXIT) }\n'
            'exit 0\n', encoding="utf-8")
        self.env = dict(os.environ, PATH=str(self.mockbin) + os.pathsep + os.environ["PATH"],
                        MOCK_ROOT=str(self.root))
        self.gm = self.root / "gamemaster"

    def launch(self, *args):
        return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                               "-File", str(self.scripts / "run.ps1"), *args],
                              env=self.env, capture_output=True, text=True, timeout=20)

    def calls(self):
        path = self.root / "calls.jsonl"
        if not path.exists():
            return []
        # Windows PowerShell Add-Content uses system encoding; fixture flags are ASCII.
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def test_headless_once_persists_session_and_clears_counter(self):
        result = self.launch("-Headless", "-MaxContinues", "0", "-Objective", "fixture")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(json.loads((self.gm / "session.json").read_text())["session_id"], SESSION)
        self.assertFalse((self.gm / "RUN").exists())
        (self.gm / "logs/continues.count").write_text("999")
        result = self.launch("-Headless", "-Resume")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.calls()[-1]
        self.assertIn(SESSION, args)
        self.assertNotIn("--last", args)
        self.assertNotIn("--dangerously-bypass-hook-trust", args)
        self.assertEqual((self.gm / "logs/continues.count").read_text(), "0")

    def test_missing_resume_id_fails_without_codex(self):
        result = self.launch("-Headless", "-Resume")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.gm / "RUN").exists())

    def test_fresh_unidentified_session_cannot_resume_previous(self):
        self.assertEqual(self.launch("-Headless").returncode, 0)
        (self.mockbin / "codex.ps1").write_text('exit 0\n')
        self.assertEqual(self.launch("-Headless").returncode, 0)
        self.assertIsNone(json.loads((self.gm / "session.json").read_text())["session_id"])
        self.assertNotEqual(self.launch("-Headless", "-Resume").returncode, 0)

    def test_integrated_headless_hook_budget_has_no_outer_bypass(self):
        mock = self.mockbin / "codex.ps1"
        original = mock.read_text()
        simulation = (
            'for ($i=0; $i -lt 5; $i++) {\n'
            '  @{hook_event_name="Stop";cwd=$env:MOCK_ROOT;session_id="' + SESSION +
            '"} | ConvertTo-Json | & python $env:MOCK_HOOK_PATH\n'
            '}\n'
        )
        mock.write_text(original.replace('exit 0\n', simulation + 'exit 0\n'))
        self.env["MOCK_HOOK_PATH"] = str(HOOK)
        result = self.launch("-Headless", "-MaxContinues", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((self.gm / "run.json").read_text())
        self.assertEqual(state["continues"], 2)
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertEqual(len(self.calls()), 1)
        self.assertFalse((self.gm / "RUN").exists())

    def test_foreign_workspace_rejected(self):
        self.gm.mkdir()
        (self.gm / "session.json").write_text(json.dumps(
            dict(workspace=str(self.root / "foreign"), session_id=SESSION)))
        self.assertNotEqual(self.launch("-Headless", "-Resume").returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_second_launcher_cannot_take_workspace_lease(self):
        self.gm.mkdir()
        holder = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command",
             '$h=[IO.File]::Open((Join-Path $env:MOCK_ROOT "gamemaster/launcher.lock"),'
             '[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);'
             '[Console]::WriteLine("LOCKED");[Console]::ReadLine()|Out-Null;$h.Dispose()'],
            env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "LOCKED")
            self.assertNotEqual(self.launch("-Headless").returncode, 0)
            self.assertEqual(self.calls(), [])
            self.assertFalse((self.gm / "RUN").exists())
        finally:
            holder.communicate("release\n", timeout=10)

    def test_stop_requires_explicit_clear_and_stop_script_disarms(self):
        self.gm.mkdir()
        (self.gm / "STOP").touch()
        self.assertNotEqual(self.launch("-Headless").returncode, 0)
        self.assertTrue((self.gm / "STOP").exists())
        self.assertEqual(self.calls(), [])
        result = self.launch("-Headless", "-ClearStop", "-TrustRepositoryHooks")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dangerously-bypass-hook-trust", self.calls()[0])
        (self.gm / "RUN").write_text("fixture")
        result = subprocess.run(["powershell", "-NoProfile", "-File",
                                 str(self.scripts / "stop.ps1")], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertTrue((self.gm / "STOP").exists())
        self.assertFalse((self.gm / "RUN").exists())

    def test_nonzero_exit_never_restarts(self):
        self.env["MOCK_EXIT"] = "7"
        result = self.launch("-Headless")
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(json.loads((self.gm / "run.json").read_text())["status"], "failed")
        self.assertFalse((self.gm / "RUN").exists())

    def test_reset_archives_checkpoint_and_rejects_resume_combination(self):
        self.gm.mkdir()
        (self.gm / "state.json").write_text('{"fixture":true}')
        (self.gm / "concept.md").write_text("preserved")
        result = self.launch("-Headless", "-Reset")
        self.assertEqual(result.returncode, 0, result.stderr)
        archived = list((self.gm / "logs").glob("reset-*/state.json"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(json.loads(archived[0].read_text())["fixture"], True)
        self.assertEqual((self.gm / "concept.md").read_text(), "preserved")
        self.assertNotEqual(self.launch("-Resume", "-Reset").returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
