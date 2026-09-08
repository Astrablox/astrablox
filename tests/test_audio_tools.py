"""Audio tools on synthesised fixtures: gate.py verdicts and metrics, store_audio_search.py parsing.
Run: python -B tests/test_audio_tools.py

Every fixture is generated here with the standard library, so the tests carry no audio files and
never touch the network: the Store search is exercised against a stubbed endpoint.
"""
import json
import math
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools/audio"
sys.path.insert(0, str(TOOLS))

import gate  # noqa: E402
import store_audio_search as store  # noqa: E402


def write_wav(path, samples, rate=44100, channels=1, width=2):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", max(-32768, min(32767, int(v * 32767)))) for v in samples))
    return path


def sine(freq, seconds, amp=0.5, rate=44100, phase=0.0):
    return [amp * math.sin(2 * math.pi * freq * i / rate + phase) for i in range(int(rate * seconds))]


def run_gate(*args):
    return subprocess.run([sys.executable, "-B", str(TOOLS / "gate.py"), *[str(a) for a in args]],
                          capture_output=True, text=True, timeout=120)


def status_of(result, name):
    for c in result["checks"]:
        if c["name"] == name:
            return c["status"]
    return None


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_loop_passes_and_reports_a_loudness_metric_by_name(self):
        f = write_wav(self.dir / "clean.wav", sine(441, 1.0))
        r = gate.measure(str(f), "ambience", True, -60.0)
        self.assertEqual(gate.verdict(r, False, False), "pass", r["checks"])
        self.assertIn(r["loudness"]["metric"], ("lufs_i", "lufs_i_bs1770_own", "rms_dbfs"))
        self.assertEqual(status_of(r, "loop_seam"), "pass")
        self.assertAlmostEqual(r["duration_s"], 1.0, places=2)

    def test_clipped_file_fails(self):
        f = write_wav(self.dir / "clipped.wav", [max(-1.0, min(1.0, v)) for v in sine(441, 1.0, amp=2.5)])
        r = gate.measure(str(f), "impact", False, -60.0)
        self.assertEqual(status_of(r, "clipping"), "fail")
        self.assertEqual(gate.verdict(r, False, False), "fail")

    def test_silence_fails(self):
        f = write_wav(self.dir / "silent.wav", [0.0] * 44100)
        r = gate.measure(str(f), "ambience", False, -60.0)
        self.assertEqual(status_of(r, "not_silence"), "fail")

    def test_loop_click_is_caught_and_a_seamless_loop_is_not(self):
        cut = write_wav(self.dir / "cut.wav", [0.8 * math.sin(2 * math.pi * 110 * i / 44100) for i in range(int(44100 * 1.31))])
        r = gate.measure(str(cut), "loop", True, -60.0)
        self.assertEqual(status_of(r, "loop_seam"), "fail")
        clean = write_wav(self.dir / "clean_loop.wav", sine(220, 2.0))
        r2 = gate.measure(str(clean), "loop", True, -60.0)
        self.assertEqual(status_of(r2, "loop_seam"), "pass")

    def test_sample_rate_above_the_roblox_limit_fails(self):
        f = write_wav(self.dir / "hires.wav", sine(441, 0.5, rate=96000), rate=96000)
        r = gate.measure(str(f), None, False, -60.0)
        self.assertEqual(status_of(r, "roblox_sample_rate"), "fail")

    def test_dc_offset_fails(self):
        f = write_wav(self.dir / "dc.wav", [0.4 + v for v in sine(441, 1.0, amp=0.2)])
        r = gate.measure(str(f), None, False, -60.0)
        self.assertEqual(status_of(r, "dc_offset"), "fail")

    def test_oneshot_with_late_start_and_cut_tail_warns(self):
        late = [0.0] * 8820 + sine(600, 0.3, amp=0.8)
        f = write_wav(self.dir / "late.wav", late)
        r = gate.measure(str(f), "oneshot", False, -60.0)
        self.assertEqual(status_of(r, "trigger_latency"), "warn")
        self.assertEqual(status_of(r, "tail_cut"), "warn")
        self.assertEqual(gate.verdict(r, False, False), "pass")
        self.assertEqual(gate.verdict(r, True, False), "fail")

    def test_undecodable_file_fails_as_unmeasured_unless_allowed(self):
        f = self.dir / "broken.ogg"
        f.write_bytes(b"OggS" + os.urandom(2048))
        r = gate.measure(str(f), None, False, -60.0)
        self.assertEqual(status_of(r, "levels"), "unmeasured")
        self.assertEqual(gate.verdict(r, False, False), "fail")
        self.assertEqual(gate.verdict(r, False, True), "pass")

    def test_set_report_gives_the_gain_that_levels_the_scene(self):
        loud = write_wav(self.dir / "loud.wav", sine(441, 1.0, amp=0.5))
        quiet = write_wav(self.dir / "quiet.wav", sine(441, 1.0, amp=0.05))
        rs = [gate.measure(str(p), "ambience", False, -60.0) for p in (loud, quiet)]
        s = gate.set_report(rs, None)
        self.assertGreater(s["spread_db"], 15)
        gains = {os.path.basename(f["file"]): f["gain_db"] for f in s["files"]}
        self.assertGreater(gains["quiet.wav"], gains["loud.wav"])
        with_target = gate.set_report(rs, -20.0)
        self.assertEqual(with_target["reference"], -20.0)
        self.assertEqual(with_target["reference_source"], "target")

    def test_plain_python_path_still_measures_and_names_its_metric(self):
        f = write_wav(self.dir / "clean.wav", sine(441, 1.0))
        env = dict(os.environ, AUDIO_GATE_NO_NUMPY="1")
        r = subprocess.run([sys.executable, "-B", str(TOOLS / "gate.py"), str(f), "--json"],
                           capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        data = json.loads(r.stdout)
        self.assertFalse(data["tools"]["numpy"])
        self.assertEqual(data["results"][0]["loudness"]["metric"], "rms_dbfs")
        self.assertEqual(data["results"][0]["decoder"], "stdlib-wave")

    def test_cli_exit_codes_and_json_shape(self):
        good = write_wav(self.dir / "good.wav", sine(441, 1.0))
        bad = write_wav(self.dir / "bad.wav", [max(-1.0, min(1.0, v)) for v in sine(441, 1.0, amp=3.0)])
        self.assertEqual(run_gate(good).returncode, 0)
        r = run_gate(good, bad, "--json")
        self.assertEqual(r.returncode, 1)
        data = json.loads(r.stdout)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual({x["verdict"] for x in data["results"]}, {"pass", "fail"})
        self.assertIn("set", data)
        self.assertEqual(run_gate(self.dir / "nothing-here.wav").returncode, 2)


class StoreSearchTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.payloads = {}
        self._real = store._get
        store._get = self.fake_get

    def tearDown(self):
        store._get = self._real

    def fake_get(self, url):
        self.calls.append(url)
        if "/marketplace/" in url:
            return {"totalResults": 2, "nextPageCursor": None,
                    "data": [{"id": 9112781510}, {"id": 9116653976}]}
        return {"data": [
            {"asset": {"id": 9112781510, "name": "Forest Ambience 1 (SFX)", "duration": 36,
                       "description": "Forest Ambience, Wind through Trees, Loop\nCategory: Ambience - Forest",
                       "audioDetails": {"artist": "Pro Sound Effects", "audioType": "Unknown", "tags": []},
                       "createdUtc": "2022-03-16T01:30:44.803Z"},
             "creator": {"id": 7462895450, "name": "ProSoundEffects", "isVerifiedCreator": True},
             "voting": {"upVotes": 3, "downVotes": 0}, "fiatProduct": {"isFree": True, "purchasable": True}},
            {"asset": {"id": 9116653976, "name": "Metal Hits 5 (SFX)", "duration": 1, "description": "Metal Hits",
                       "audioDetails": {"artist": "Pro Sound Effects", "audioType": "SoundEffect", "tags": []}},
             "creator": {"id": 7462895450, "name": "ProSoundEffects", "isVerifiedCreator": True},
             "voting": {"upVotes": 0, "downVotes": 0}, "fiatProduct": {"isFree": False, "purchasable": True}},
        ]}

    def test_search_builds_the_verified_audio_query(self):
        rows = store.search("forest ambience", audio_type="SoundEffect", min_duration=20,
                            max_duration=90, creator_id=store.PUBLISHERS["pse"][0], limit=25)
        q = self.calls[0]
        self.assertIn("/marketplace/3?", q)
        self.assertIn("minDuration=20", q)
        self.assertIn("maxDuration=90", q)
        self.assertIn("audioTypes=SoundEffect", q)
        self.assertIn("creatorTargetId=7462895450", q)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["uri"], "rbxassetid://9112781510")
        self.assertEqual(rows[0]["duration"], 36)
        self.assertTrue(rows[0]["creator_verified"])
        self.assertIn("Loop", rows[0]["description"])

    def test_free_filter_keeps_only_free_assets(self):
        rows = store.search("x")
        free = [r for r in rows if r["free"]]
        self.assertEqual([r["id"] for r in free], [9112781510])

    def test_publisher_ids_are_present_for_the_libraries_we_rely_on(self):
        for key in ("pse", "apm", "distrokid", "clippsly"):
            self.assertIsInstance(store.PUBLISHERS[key][0], int)


if __name__ == "__main__":
    unittest.main()
