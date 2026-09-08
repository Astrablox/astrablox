"""Story tools: the scene gate on a good fixture and on each fault it exists to catch.
Run: python -B tests/test_story_tools.py
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "tools/story/contract_check.py"
GOOD = ROOT / "tests/fixtures/story/good"


def run(*args):
    return subprocess.run([sys.executable, "-B", str(GATE), *map(str, args)], capture_output=True, text=True, timeout=60)


def check(*args):
    r = run(*args)
    return r, json.loads(r.stdout)


class ContractCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.scene = pathlib.Path(self.tmp.name) / "scene"
        shutil.copytree(GOOD, self.scene)
        self.script = self.scene / "script.md"
        self.contract = self.scene / "contract.md"

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture no longer contains {old!r}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def rules(self, data):
        return {e["rule"] for e in data["errors"]}

    def test_good_fixture_passes_clean(self):
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["warnings"], [])
        self.assertEqual(data["counts"]["quests"], 1)
        self.assertEqual(data["counts"]["npcs"], 2)
        self.assertEqual(data["counts"]["schedule_entries"], 4)

    def test_explicit_pair_of_paths_and_text_output(self):
        r, data = check(self.script, self.contract)
        self.assertEqual(data["status"], "PASS")
        r = run(self.scene, "--text")
        self.assertEqual(r.returncode, 0)
        self.assertIn("PASS", r.stdout)

    def test_quest_missing_a_required_field(self):
        self.edit(self.script, "Reward: The crossing opens and the far bank becomes walkable.\n", "")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("field-missing", self.rules(data))
        self.assertTrue(any("Quest: The Sunken Ferry" == e["where"] for e in data["errors"]))

    def test_quest_field_left_empty(self):
        self.edit(self.script, "Trigger: The player finds the ferry rope cut and the boat under water at the landing.", "Trigger:")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("field-empty", self.rules(data))

    def test_choice_with_one_option(self):
        self.edit(self.script, "- Buy the barge — costs the grain money the village kept for winter\n", "")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("choice-single", self.rules(data))
        self.assertIn("consequence-unknown-option", self.rules(data))

    def test_option_without_a_consequence(self):
        self.edit(self.script, "- Buy the barge — BargeBought: the grain store stands empty and the winter queue forms at the Mill Yard\n", "")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("consequence-missing", self.rules(data))

    def test_option_with_no_cost(self):
        self.edit(self.script, "- Raise the boat — costs the player two days of Neska's labour and her trust in the miller", "- Raise the boat")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("choice-cost-missing", self.rules(data))

    def test_place_not_declared_in_the_contract(self):
        self.edit(self.script, "Place: Ferry Landing\nTrigger:", "Place: The Old Weir\nTrigger:")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("place-undeclared", self.rules(data))

    def test_schedule_place_not_declared(self):
        self.edit(self.script, "- night — Burnt Barn — sleeping where the roof holds", "- night — The Old Weir — sleeping where the roof holds")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("place-undeclared", self.rules(data))

    def test_schedule_entry_without_place_or_action(self):
        self.edit(self.script, "- morning — Mill Yard — splitting the axle blocks he cannot use", "- morning — Mill Yard")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("schedule-incomplete", self.rules(data))

    def test_npc_without_lines_or_schedule(self):
        self.edit(self.script, 'Lines:\n- first meeting — "Coin first, then the far bank."\n', "")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("field-missing", self.rules(data))
        self.assertTrue(any(e["where"] == "NPC: Neska" for e in data["errors"]))

    def test_line_entry_without_a_quoted_line(self):
        self.edit(self.script, '- rain — "Water everywhere and none of it under the wheel."', "- rain — he complains about the rain")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("line-unquoted", self.rules(data))

    def test_npc_missing_from_the_contract(self):
        self.edit(self.contract, "- Neska — the ferrywoman; works the boat, sleeps in the barn\n", "")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("npc-undeclared", self.rules(data))

    def test_duplicate_name_in_the_contract(self):
        self.edit(self.contract, "- Cut Rope — the ferry rope, cut short, under the straw in the Burnt Barn", "- Mill Yard — a second thing called by the name of a place")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("name-duplicate", self.rules(data))

    def test_two_quests_with_the_same_name(self):
        text = self.script.read_text(encoding="utf-8")
        block = text[text.index("### Quest: The Sunken Ferry"):text.index("## Points of interest")]
        self.script.write_text(text.replace(block, block + block, 1), encoding="utf-8")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("name-duplicate", self.rules(data))

    def test_contract_entry_without_a_description(self):
        self.edit(self.contract, "- Mill Yard — the yard above the stopped wheel; the dry race is visible from it", "- Mill Yard")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("description-missing", self.rules(data))

    def test_missing_section_in_each_file(self):
        self.edit(self.script, "## Journal", "## Notes")
        self.edit(self.contract, "## Events", "## Signals")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len([e for e in data["errors"] if e["rule"] == "section-missing"]), 2)

    def test_empty_sections_are_allowed_only_as_none(self):
        self.edit(self.contract, "- Cut Rope — the ferry rope, cut short, under the straw in the Burnt Barn\n- Grain Sacks — sacks stacked in the Mill Yard, some already sour", "none")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(data["counts"]["props"], 0)
        self.edit(self.contract, "none", "")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("section-empty", self.rules(data))

    def test_unknown_field_is_a_warning_not_an_error(self):
        self.edit(self.script, "Place: Mill Yard\nSchedule:", "Place: Mill Yard\nWants: the wheel turning again\nSchedule:")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("field-unknown", {w["rule"] for w in data["warnings"]})

    def test_contract_name_never_used_in_the_script_is_a_warning(self):
        self.edit(self.script, "(MillWheelDry) ", "")
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("name-unused", {w["rule"] for w in data["warnings"]})

    def test_missing_file_reports_and_fails(self):
        self.contract.unlink()
        r, data = check(self.scene)
        self.assertEqual(r.returncode, 1)
        self.assertIn("file-missing", self.rules(data))


if __name__ == "__main__":
    unittest.main(verbosity=2)
