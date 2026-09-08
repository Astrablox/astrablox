#!/usr/bin/env python3
"""Concept image for one asset, shaped for image-to-3D: one object, neutral background, 3/4 view.

Usage:
  concept.py --slug iron_portcullis --subject "iron portcullis gate of a storm citadel" --bible bible.md [--pose tpose] [--dry-run]

The style bible is the only place style lives. It is a short text file the art director wrote:
civilisation, materials, palette, signature detail, geometry style, texture style. This tool never
adds style words of its own; it only adds the framing that 3D generators need.
"""
from __future__ import annotations
import argparse, base64, json, pathlib, sys
from common import log, key, asset_dir, record

FRAMING = (
    "Single object only, centered, entire object visible with margin, three-quarter view from slightly above, "
    "isolated on a plain flat neutral background, no ground shadow, no scene, no text, no watermark, "
    "even studio lighting, colours and materials readable, game asset concept art."
)
POSE = {
    "none": "",
    "tpose": " Character standing in a T-pose, arms straight out to the sides, facing the camera, feet apart, neutral expression.",
    "apose": " Character standing in an A-pose, arms slightly away from the body, facing the camera.",
}


def build_prompt(subject: str, bible: str, pose: str) -> str:
    return f"{subject}. Style bible: {bible.strip()} {FRAMING}{POSE.get(pose, '')}"


def generate(prompt: str, out_png: pathlib.Path, size: str, quality: str) -> dict:
    from openai import OpenAI  # imported lazily so dry runs work without the SDK
    client = OpenAI()
    r = client.images.generate(model="gpt-image-2", prompt=prompt, size=size, quality=quality,
                               background="transparent", output_format="png", n=1)
    data = r.data[0]
    out_png.write_bytes(base64.b64decode(data.b64_json))
    return {"model": "gpt-image-2", "size": size, "quality": quality, "revised_prompt": getattr(data, "revised_prompt", None)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--bible", required=True, help="path to the style bible text")
    ap.add_argument("--pose", default="none", choices=list(POSE))
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--quality", default="high")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    bible = pathlib.Path(a.bible).read_text()
    prompt = build_prompt(a.subject, bible, a.pose)
    out = asset_dir(a.slug) / "concept.png"
    (asset_dir(a.slug) / "concept.prompt.txt").write_text(prompt)
    if a.dry_run or not key("OPENAI_API_KEY"):
        log("concept: dry run (no OPENAI_API_KEY)" if not key("OPENAI_API_KEY") else "concept: dry run")
        record(a.slug, "concept", dry_run=True, prompt=prompt, concept_png=str(out))
        print(json.dumps({"slug": a.slug, "dry_run": True, "prompt": prompt, "concept_png": str(out)}))
        return
    meta = generate(prompt, out, a.size, a.quality)
    record(a.slug, "concept", prompt=prompt, concept_png=str(out), **meta)
    log("concept:", out)
    print(json.dumps({"slug": a.slug, "concept_png": str(out), **meta}))


if __name__ == "__main__":
    main()
