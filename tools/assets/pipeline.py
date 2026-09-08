#!/usr/bin/env python3
"""One asset end to end: concept -> 3D -> optimize -> upload -> Luau insert snippet.

Usage:
  pipeline.py --subject "iron portcullis gate of a storm citadel" --bible bible.md [--slug x] [--pose tpose] [--rig] [--dry-run]

Each step is its own script (concept.py, gen3d.py, optimize.py, upload.py) and can be rerun alone;
this runner only sequences them and writes the final summary. Missing API keys turn the affected
steps into dry runs and the summary says so, so a producer never mistakes a dry run for an asset.
"""
from __future__ import annotations
import argparse, json, pathlib, subprocess, sys
from common import log, key, asset_dir, read_provenance, slugify

HERE = pathlib.Path(__file__).parent


def sh(*args) -> dict:
    p = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    if p.returncode not in (0, 2):
        raise SystemExit(f"{args[0]} failed:\n{p.stderr}")
    last = [l for l in p.stdout.strip().splitlines() if l.startswith("{")]
    return json.loads(last[-1]) if last else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True); ap.add_argument("--bible", required=True)
    ap.add_argument("--slug"); ap.add_argument("--pose", default="none"); ap.add_argument("--rig", action="store_true")
    ap.add_argument("--face-limit", type=int, default=10000); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    slug = a.slug or slugify(a.subject)
    dry = ["--dry-run"] if a.dry_run else []
    c = sh(str(HERE / "concept.py"), "--slug", slug, "--subject", a.subject, "--bible", a.bible, "--pose", a.pose, *dry)
    g = sh(str(HERE / "gen3d.py"), "--slug", slug, "--face-limit", str(a.face_limit), *(["--rig"] if a.rig else []), *dry)
    glb = g.get("glb")
    summary = {"slug": slug, "concept": c, "gen3d": g}
    if glb and pathlib.Path(glb).exists():
        opt = asset_dir(slug) / "model.roblox.glb"
        o = sh(str(HERE / "optimize.py"), glb, str(opt), "--target-tris", str(a.face_limit))
        summary["optimize"] = o
        u = sh(str(HERE / "upload.py"), "--file", str(opt), "--name", a.subject, "--slug", slug, *dry)
        summary["upload"] = u
        if u.get("roblox_asset_id"):
            summary["insert_luau"] = (HERE / "insert.luau").read_text().replace("ASSET_ID", str(u["roblox_asset_id"])).replace("ASSET_NAME", slug)
    else:
        summary["note"] = "no GLB produced (dry run or generation failed); optimize/upload skipped"
    summary["provenance"] = str(asset_dir(slug) / "provenance.json")
    summary["dry_run"] = a.dry_run or not (key("OPENAI_API_KEY") and key("TRIPO_API_KEY") and key("ROBLOX_API_KEY"))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
