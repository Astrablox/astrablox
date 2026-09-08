#!/usr/bin/env python3
"""Make a GLB Roblox-ready and report what it is: triangle count, size, textures, animations.

Usage:
  optimize.py in.glb out.glb [--target-tris 10000] [--texture-max 1024] [--check-only]

Pipeline: weld -> simplify to the target (only if above it) -> resize textures -> validate.
Requires: npx @gltf-transform/cli (node), pip install trimesh pygltflib.
Exit status 2 when the result would still be refused by Roblox (over 20 000 triangles or 20 MB).
"""
from __future__ import annotations
import argparse, json, os, pathlib, shutil, subprocess, sys, tempfile
from common import log, ROBLOX_MAX_TRIS, ROBLOX_MAX_FILE_BYTES, TEXTURE_MAX


def inspect(path: pathlib.Path) -> dict:
    import trimesh, pygltflib
    sc = trimesh.load(str(path), force="scene")
    tris = int(sum(g.faces.shape[0] for g in sc.geometry.values()))
    g = pygltflib.GLTF2().load(str(path))
    mats = []
    for m in g.materials or []:
        pbr = m.pbrMetallicRoughness
        mats.append({"name": m.name, "baseColorTexture": bool(pbr and pbr.baseColorTexture),
                     "metallicRoughnessTexture": bool(pbr and pbr.metallicRoughnessTexture),
                     "normalTexture": bool(m.normalTexture), "emissiveTexture": bool(m.emissiveTexture)})
    return {
        "file": str(path), "bytes": path.stat().st_size, "triangles": tris,
        "meshes": len(g.meshes or []), "materials": mats, "images": len(g.images or []),
        "animations": [a.name or f"anim{i}" for i, a in enumerate(g.animations or [])],
        "skinned": bool(g.skins), "extents": [round(float(x), 3) for x in sc.extents] if len(sc.geometry) else None,
        "roblox_ok": tris <= ROBLOX_MAX_TRIS and path.stat().st_size <= ROBLOX_MAX_FILE_BYTES,
    }


def gltf_transform(*args) -> None:
    cli = shutil.which("gltf-transform")
    cmd = [cli, *args] if cli else ["npx", "-y", "@gltf-transform/cli", *args]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def optimize(src: pathlib.Path, dst: pathlib.Path, target_tris: int, texture_max: int) -> dict:
    before = inspect(src)
    with tempfile.TemporaryDirectory() as td:
        a = pathlib.Path(td) / "a.glb"; b = pathlib.Path(td) / "b.glb"
        gltf_transform("weld", str(src), str(a))
        cur = a
        if before["triangles"] > target_tris:
            ratio = max(0.05, min(0.95, target_tris / before["triangles"]))
            gltf_transform("simplify", str(cur), str(b), "--ratio", f"{ratio:.3f}", "--error", "0.001")
            cur = b
        c = pathlib.Path(td) / "c.glb"
        gltf_transform("resize", str(cur), str(c), "--width", str(texture_max), "--height", str(texture_max))
        shutil.copy(c, dst)
    after = inspect(dst)
    return {"before": before, "after": after}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst", nargs="?")
    ap.add_argument("--target-tris", type=int, default=10000)
    ap.add_argument("--texture-max", type=int, default=TEXTURE_MAX)
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    src = pathlib.Path(a.src)
    if a.check_only or not a.dst:
        info = inspect(src); print(json.dumps(info, indent=1)); sys.exit(0 if info["roblox_ok"] else 2)
    res = optimize(src, pathlib.Path(a.dst), a.target_tris, a.texture_max)
    print(json.dumps(res, indent=1))
    sys.exit(0 if res["after"]["roblox_ok"] else 2)


if __name__ == "__main__":
    main()
