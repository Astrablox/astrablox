#!/usr/bin/env python3
"""Image -> textured PBR mesh through Tripo, downloaded as GLB.

Usage:
  gen3d.py --slug iron_portcullis [--image path.png] [--multiview] [--face-limit 8000] [--quad] [--rig] [--dry-run]

Default model is Tripo P1 (native low-poly: honours --face-limit at generation, so the Roblox 20k limit is met
without decimation), PBR on, auto size on (metres), orientation aligned to the image. --hero switches to H3 v3.1
with quad topology and smart low-poly for assets that get retopologised. --rig runs rig-check, auto-rig
(biped/quadruped/avian/...) with a Mixamo-spec skeleton and idle/walk/run retargets. Every parameter is recorded in
provenance.
Requires: pip install tripo3d ; TRIPO_API_KEY in the environment.
"""
from __future__ import annotations
import argparse, asyncio, json, pathlib, sys
from common import log, key, asset_dir, read_provenance, record, ROBLOX_TARGET_TRIS

# P1 is Tripo's native low-poly model: it honours face_limit at generation time (48..20000), so the
# Roblox 20k limit is met without decimation. H3 (v3.1) is for hero assets that will be retopologised.
MODEL_P1 = "P1-20260311"
MODEL_H3 = "v3.1-20260211"
MODEL_VERSION = MODEL_P1


async def run(slug: str, image: pathlib.Path, multiview: bool, face_limit: int, quad: bool, rig: bool,
              texture_quality: str, geometry_quality: str, model_version: str = MODEL_VERSION, rig_type: str = "biped") -> dict:
    from tripo3d import TripoClient, TaskStatus
    out_dir = asset_dir(slug) / "tripo"
    out_dir.mkdir(exist_ok=True)
    result: dict = {"model_version": model_version}
    async with TripoClient(api_key=key("TRIPO_API_KEY")) as client:
        hero = model_version == MODEL_H3
        common = dict(model_version=model_version, face_limit=face_limit, texture=True, pbr=True,
                      texture_quality=texture_quality, geometry_quality=geometry_quality,
                      auto_size=True, orientation="align_image")
        if hero:  # P1 rejects quad / smart_low_poly / generate_parts
            common.update(quad=quad, smart_low_poly=True)
        if multiview:
            # one clean 3/4 concept -> four consistent views -> model; more faithful for characters
            mv_task = await client.generate_multiview_image(image=str(image))
            await client.wait_for_task(mv_task, verbose=False)
            result["multiview_task_id"] = mv_task
            task_id = await client.multiview_to_model(images=[str(image)], original_task_id=mv_task,
                                                      **{k: v for k, v in common.items() if k != "orientation"})
        else:
            task_id = await client.image_to_model(image=str(image), **common)
        result["tripo_task_id"] = task_id
        log("tripo task", task_id)
        task = await client.wait_for_task(task_id, verbose=True)
        if task.status != TaskStatus.SUCCESS:
            raise SystemExit(f"tripo task {task_id} ended {task.status}")
        files = await client.download_task_models(task, str(out_dir))
        result["files"] = files
        glb = files.get("pbr_model") or files.get("model")
        result["glb"] = glb
        if rig:
            from tripo3d.models import RigType, RigSpec
            chk = await client.check_riggable(task_id)
            chk_done = await client.wait_for_task(chk)
            result["rig_check"] = str(getattr(chk_done, "output", ""))[:300]
            rig_task = await client.rig_model(task_id, out_format="glb", rig_type=RigType(rig_type), spec=RigSpec.MIXAMO)
            rig_done = await client.wait_for_task(rig_task, verbose=True)
            result["rig_task_id"] = rig_task
            result["rig_files"] = await client.download_task_models(rig_done, str(out_dir / "rig"))
            try:
                from tripo3d.models import Animation
                anim_task = await client.retarget_animation(rig_task, [Animation("preset:idle"), Animation("preset:walk"), Animation("preset:run")], out_format="glb", export_with_geometry=True)
                anim_done = await client.wait_for_task(anim_task, verbose=True)
                result["anim_files"] = await client.download_task_models(anim_done, str(out_dir / "anim"))
            except Exception as e:  # animation presets vary by account; rig alone is still useful
                result["anim_error"] = str(e)[:200]
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--image", help="defaults to the asset's concept.png")
    ap.add_argument("--multiview", action="store_true")
    ap.add_argument("--face-limit", type=int, default=ROBLOX_TARGET_TRIS)
    ap.add_argument("--quad", action="store_true", default=True)
    ap.add_argument("--no-quad", dest="quad", action="store_false")
    ap.add_argument("--rig", action="store_true", help="characters: auto-rig after generation")
    ap.add_argument("--rig-type", default="biped", choices=["biped", "quadruped", "hexapod", "octopod", "avian", "serpentine", "aquatic", "others"])
    ap.add_argument("--hero", action="store_true", help="use H3 (v3.1) + quad instead of P1; for retopologised hero assets")
    ap.add_argument("--texture-quality", default="detailed", choices=["standard", "detailed"])
    ap.add_argument("--geometry-quality", default="detailed", choices=["standard", "detailed"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    image = pathlib.Path(a.image) if a.image else pathlib.Path(read_provenance(a.slug).get("concept_png") or asset_dir(a.slug) / "concept.png")
    model_version = MODEL_H3 if a.hero else MODEL_P1
    params = dict(image=str(image), multiview=a.multiview, face_limit=a.face_limit, quad=a.quad, rig=a.rig, rig_type=a.rig_type,
                  texture_quality=a.texture_quality, geometry_quality=a.geometry_quality, model_version=model_version)
    if a.dry_run or not key("TRIPO_API_KEY"):
        log("gen3d: dry run (no TRIPO_API_KEY)" if not key("TRIPO_API_KEY") else "gen3d: dry run")
        record(a.slug, "gen3d", dry_run=True, **params)
        print(json.dumps({"slug": a.slug, "dry_run": True, **params}))
        return
    if not image.exists():
        raise SystemExit(f"no input image: {image}")
    res = asyncio.run(run(a.slug, image, a.multiview, a.face_limit, a.quad, a.rig, a.texture_quality, a.geometry_quality, model_version, a.rig_type))
    record(a.slug, "gen3d", source="tripo", **params, **{k: v for k, v in res.items() if k != "files"}, files=res.get("files"))
    print(json.dumps({"slug": a.slug, **res}, default=str))


if __name__ == "__main__":
    main()
