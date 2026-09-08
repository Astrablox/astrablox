"""design_check fixtures. Run: python -B tests/test_design_tools.py"""
import pathlib, subprocess, sys, unittest, tempfile, shutil, json
sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests/fixtures/design"
TOOL = ROOT / "tools/design/design_check.py"


def run(gp, design):
    return subprocess.run([sys.executable, "-B", str(TOOL), str(gp), "--design", str(design)], capture_output=True, text=True)


class DesignCheckTests(unittest.TestCase):
    def test_good_fixture_passes_with_warning(self):
        r = run(FIX / "game/scenes/pier/gameplay.md", FIX / "game/DESIGN.md")
        self.assertEqual(r.returncode, 0, r.stdout)
        data = json.loads(r.stdout); self.assertEqual(data["verdict"], "PASS"); self.assertTrue(any("Riftblade".lower() in w.lower() for w in data["warnings"]))

    def test_unknown_system_and_enemy_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            gp = pathlib.Path(tmp) / "gameplay.md"
            gp.write_text((FIX / "game/scenes/pier/gameplay.md").read_text().replace("§5.2", "§9.9").replace("hoarfrost hound", "ice troll"))
            r = run(gp, FIX / "game/DESIGN.md")
            self.assertEqual(r.returncode, 1)
            problems = " ".join(f["problem"] for f in json.loads(r.stdout)["findings"])
            self.assertIn("does not name a DESIGN.md section", problems); self.assertIn("ice troll", problems)

    def test_template_placeholders_fail(self):
        r = run(ROOT / "game/scenes/_template/gameplay.md", ROOT / "game/DESIGN.md")
        self.assertEqual(r.returncode, 1)

    def test_seed_design_has_enemy_specs(self):
        text = (ROOT / "game/DESIGN.md").read_text(encoding="utf-8")
        self.assertIn("## 7. Enemies", text)


if __name__ == "__main__":
    unittest.main()
