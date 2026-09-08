"""Blender toolkit on the lantern fixture, headless. Runs only when BLENDER points at a Blender 4.x binary
(skipped otherwise): render_views frames are not black (mean brightness > 20), bake_pbr writes five maps
per object, export_glb verifies OK, layout_export writes layout.json with the pieces, side_by_side composes.
Run: BLENDER=/path/to/blender python -B tests/test_blender_tools.py
"""
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
LAUNCH = ROOT / "tools/blender/blender.py"
BPY = ROOT / "tools/blender/bpy"
BLENDER = os.environ.get("BLENDER")


def blender(script, blend=None, *args):
    cmd = [sys.executable, "-B", str(LAUNCH), str(script)] + (["--blend", str(blend)] if blend else []) + ["--", *map(str, args)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    return r


def mean_brightness(png):
    from PIL import Image
    im = Image.open(png).convert("L").resize((64, 36))
    data = list(im.getdata())
    return sum(data) / len(data)


@unittest.skipUnless(BLENDER and os.path.exists(BLENDER), "BLENDER not set")
class BlenderToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="astra-blender-"))
        cls.blend = cls.tmp / "test.blend"
        r = blender(ROOT / "tests/fixtures/make_lantern.py", None, "--out", cls.blend)
        assert cls.blend.exists(), r.stdout + r.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_1_render_views_not_black(self):
        r = blender(BPY / "render_views.py", self.blend, "--out", self.tmp / "renders", "--stage", "t", "--samples", "16", "--size", "640x360")
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        for view in ("near", "far", "quarter"):
            png = self.tmp / "renders" / f"t_{view}.png"
            self.assertTrue(png.exists(), r.stdout[-2000:])
            self.assertGreater(mean_brightness(png), 20, f"{view} render is black")
            self.assertIn(f"MEAN_BRIGHTNESS {view}", r.stdout)

    def test_2_bake_export_layout(self):
        tex = self.tmp / "textures"
        baked = self.tmp / "test_baked.blend"
        r = blender(BPY / "bake_pbr.py", self.blend, "--out", tex, "--size", "256", "--save", baked)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        for obj in ("LanternPost", "LanternHead"):
            maps = sorted(p.name for p in tex.glob(f"{obj}_*.png"))
            self.assertEqual(maps, [f"{obj}_{k}.png" for k in ("ao", "color", "metallic", "normal", "roughness")], r.stdout[-1500:])
        self.assertTrue(baked.exists())
        glb = self.tmp / "out/lantern.glb"
        r = blender(BPY / "export_glb.py", baked, "--out", glb)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertIn("VERDICT: OK", r.stdout)
        verify = json.loads((self.tmp / "out/lantern.glb.verify.json").read_text(encoding="utf-8"))
        self.assertEqual(verify["verdict"], "OK"); self.assertEqual(len(verify["meshes"]), 2); self.assertTrue(verify["images"])
        layout = self.tmp / "out/layout.json"
        r = blender(BPY / "layout_export.py", self.blend, "--out", layout)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        data = json.loads(layout.read_text(encoding="utf-8"))
        names = {o["name"]: o for o in data["pieces"]}
        self.assertEqual(set(names), {"LanternPost", "LanternHead"})  # Ground is skipped
        head = names["LanternHead"]
        self.assertEqual(head["glb"], "assets/world/lantern/LanternHead.glb")
        self.assertEqual(head["asset"], "assets/world/lantern/")
        self.assertEqual(head["collision"], "gameplay"); self.assertTrue(head["anchored"])
        self.assertAlmostEqual(head["blender"]["location_m"][2], 3.2, places=3)
        self.assertAlmostEqual(head["position"][1], 3.2, places=3)  # Y-up: Blender z becomes y
        self.assertEqual(data["up"], "Y"); self.assertIn("cameras", data)

    def test_3_side_by_side(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")
        renders = self.tmp / "renders"
        if not (renders / "t_far.png").exists():
            blender(BPY / "render_views.py", self.blend, "--out", renders, "--stage", "t", "--samples", "8", "--size", "320x180", "--views", "far,near")
        out = self.tmp / "sbs.png"
        r = subprocess.run([sys.executable, "-B", str(ROOT / "tools/blender/side_by_side.py"), "--left", renders / "t_far.png", "--right", renders / "t_near.png", "--out", out], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
