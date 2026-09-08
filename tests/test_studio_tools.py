"""Studio tools fixtures (v0.3): the static gate on this checkout, run_digest and session_digest on fakes.
Run: python -B tests/test_studio_tools.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools/studio"
LANE_TABLE = "| Lane | Session | Owns | Extra markers |\n|---|---|---|---|\n| Lead | `lead` | scene | `SCENE:` |\n| World | `world` | pieces | `PIECES:`, `RENDERS:` |\n"


def run(*args):
    return subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, timeout=60)


class StudioToolsTests(unittest.TestCase):
    def test_check_studio_passes_on_this_checkout(self):
        r = run(TOOLS / "check_studio.py", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        data = json.loads(r.stdout)
        self.assertGreaterEqual(data["roles"], 10)
        self.assertIn('[agents."dev"]', (ROOT / ".codex/config.toml").read_text(encoding="utf-8"))

    def test_check_studio_fails_on_missing_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp)
            (fake / ".codex/agents").mkdir(parents=True)
            (fake / ".agents/skills").mkdir(parents=True)
            (fake / ".codex/config.toml").write_text('[agents."world"]\ndescription = "d"\nconfig_file = "agents/world.toml"\n')
            (fake / ".codex/agents/world.toml").write_text('name = "world"\ndescription = "d"\nmodel_reasoning_effort = "low"\ndeveloper_instructions = "DELIVERED: EVIDENCE: ASSUMPTIONS: WEAKEST: OPEN: STATUS: PIECES:"\n')
            (fake / "AGENTS.md").write_text(LANE_TABLE)
            r = run(TOOLS / "check_studio.py", "--root", str(fake))
            self.assertEqual(r.returncode, 1)
            self.assertIn("RENDERS:", r.stdout)
            self.assertNotIn("PIECES:", r.stdout.split("ERROR")[1] if "ERROR" in r.stdout else "")

    def test_run_digest_reports_missing_markers_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp)
            (fake / "AGENTS.md").write_text(LANE_TABLE)
            (fake / "board/tasks").mkdir(parents=True); (fake / "board/reports").mkdir()
            (fake / "board/STATE.md").write_text("# State\nGoal: pier\n")
            (fake / "board/tasks/001.md").write_text("---\nid: 001\nlane: world\nscene: pier\nstatus: done\nclaimed_by: world\n---\n## Goal\nlantern\n")
            (fake / "board/reports/001.md").write_text("Lantern built.\nDELIVERED: assets/world/lantern/lantern.glb glb_verified\nEVIDENCE: builds/1/renders/near.png\nASSUMPTIONS: none\nWEAKEST: the glass\nOPEN: none\nSTATUS: DONE\nPIECES: lantern\n")
            r = run(TOOLS / "run_digest.py", "--root", str(fake), "--scene", "pier")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("MISSING markers: RENDERS:", r.stdout)
            self.assertIn("2 missing", r.stdout)
            self.assertIn("STATUS: DONE", r.stdout)
            self.assertTrue((fake / "studio/scenes/pier/digest.md").exists())

    def test_session_digest_reads_rollout(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp)
            sessions = fake / "sessions/2026/09/08"
            sessions.mkdir(parents=True)
            ws = fake / "ws"; ws.mkdir()
            lines = [
                {"timestamp": "t0", "type": "session_meta", "payload": {"id": "s1", "cwd": str(ws), "timestamp": "t0", "cli_version": "0.153"}},
                {"timestamp": "t1", "type": "turn_context", "payload": {"model": "gpt-6-astra"}},
                {"timestamp": "t2", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "build the bridge"}]}},
                {"timestamp": "t3", "type": "response_item", "payload": {"type": "function_call", "name": "execute_luau", "arguments": json.dumps({"code": "print(1)"}), "call_id": "c1"}},
                {"timestamp": "t4", "type": "response_item", "payload": {"type": "function_call_output", "call_id": "c1", "output": "Error: nope"}},
                {"timestamp": "t5", "type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent", "arguments": json.dumps({"agent": "world", "message": "brief"}), "call_id": "c2"}},
                {"timestamp": "t6", "type": "event_msg", "payload": {"type": "token_count", "info": {"last_token_usage": {"total_tokens": 42}}}},
                {"timestamp": "t7", "type": "weird_new_type", "payload": {}},
            ]
            (sessions / "rollout-2026-09-08T10-00-00-s1.jsonl").write_text("\n".join(json.dumps(l) for l in lines))
            r = run(TOOLS / "session_digest.py", "--sessions", str(fake / "sessions"), "--workspace", str(ws))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("execute_luau", r.stdout)
            self.assertIn("looks like an error: 1", r.stdout)
            self.assertIn("weird_new_type", r.stdout)
            self.assertIn("1 of 1 session files", r.stdout)


if __name__ == "__main__":
    unittest.main()
