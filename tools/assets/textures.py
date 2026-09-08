#!/usr/bin/env python3
"""CC0 PBR texture sets and skyboxes for Roblox, from Poly Haven and ambientCG.

Usage:
  textures.py search "castle brick"                      # list candidates from both sources
  textures.py fetch polyhaven castle_brick_02_red --res 1k  # download the Roblox map set into assets-work/textures/<id>/
  textures.py fetch ambientcg Bricks097 --res 1K
  textures.py skybox polyhaven kloppenheim_06 --res 2k     # HDRI -> six cube faces (needs: pip install py360convert imageio)

A fetched set contains: color.jpg, normal_gl.png (Roblox wants OpenGL normals), roughness.jpg, metalness.jpg (if any),
and a recipe.json that says which file goes into which SurfaceAppearance/MaterialVariant slot after upload with upload.py.
"""
from __future__ import annotations
import argparse, io, json, pathlib, sys, urllib.request, urllib.parse, zipfile
from common import log, ROOT

PH = "https://api.polyhaven.com"
ACG = "https://ambientcg.com/api/v2/full_json"
OUT = ROOT / "textures"


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "astrablox/1.0"}), timeout=60) as r:
        return json.load(r)


def download(url, dst: pathlib.Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "astrablox/1.0"}), timeout=300) as r:
        dst.write_bytes(r.read())
    return dst


def search(q: str):
    ph = get_json(f"{PH}/assets?t=textures")
    words = q.lower().split()
    hits = [(k, v) for k, v in ph.items() if all(w in (k + " " + " ".join(v.get("tags", []) + v.get("categories", []))).lower() for w in words)]
    for k, v in sorted(hits, key=lambda kv: -kv[1].get("download_count", 0))[:15]:
        print(f"polyhaven  {k:40} cats={','.join(v.get('categories', []))[:40]:40} dl={v.get('download_count')}")
    acg = get_json(f"{ACG}?{urllib.parse.urlencode({'q': q, 'type': 'Material', 'limit': 15})}")
    for a in acg.get("foundAssets", []):
        print(f"ambientcg  {a.get('assetId'):40} {a.get('displayName', '')[:40]:40} tags={','.join(a.get('tags', [])[:6])}")


def fetch_polyhaven(asset: str, res: str):
    files = get_json(f"{PH}/files/{asset}")
    out = OUT / f"polyhaven_{asset}"; out.mkdir(parents=True, exist_ok=True)
    recipe = {"source": "polyhaven", "id": asset, "license": "CC0", "url": f"https://polyhaven.com/a/{asset}", "maps": {}}
    plan = {"Diffuse": ("color", "jpg"), "nor_gl": ("normal_gl", "png"), "Rough": ("roughness", "jpg"), "Metal": ("metalness", "jpg"), "AO": ("ao", "jpg")}
    for key, (name, ext) in plan.items():
        node = files.get(key, {}).get(res, {})
        f = node.get(ext) or node.get("jpg") or node.get("png")
        if not f: continue
        dst = download(f["url"], out / f"{name}.{f['url'].rsplit('.', 1)[-1]}")
        recipe["maps"][name] = dst.name
        log("fetched", dst.name, f["size"])
    (out / "recipe.json").write_text(json.dumps(recipe, indent=1))
    print(json.dumps(recipe, indent=1))


def fetch_ambientcg(asset: str, res: str):
    data = get_json(f"{ACG}?{urllib.parse.urlencode({'id': asset, 'include': 'downloadData'})}")
    found = data.get("foundAssets") or []
    if not found: raise SystemExit("not found")
    dls = found[0]["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
    pick = next((d for d in dls if d["attribute"] == f"{res}-JPG"), dls[0])
    out = OUT / f"ambientcg_{asset}"; out.mkdir(parents=True, exist_ok=True)
    zpath = download(pick["downloadLink"], out / pick["fileName"])
    recipe = {"source": "ambientcg", "id": asset, "license": "CC0", "url": f"https://ambientcg.com/view?id={asset}", "maps": {}}
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            low = n.lower()
            slot = ("color" if "color" in low else "normal_gl" if "normalgl" in low else "roughness" if "roughness" in low
                    else "metalness" if "metalness" in low else "ao" if "ambientocclusion" in low else None)
            if slot and (low.endswith(".jpg") or low.endswith(".png")):
                target = out / f"{slot}.{low.rsplit('.', 1)[-1]}"
                target.write_bytes(z.read(n)); recipe["maps"][slot] = target.name
    zpath.unlink()
    (out / "recipe.json").write_text(json.dumps(recipe, indent=1))
    print(json.dumps(recipe, indent=1))


def skybox_polyhaven(asset: str, res: str):
    """HDRI -> six LDR cube faces. Uses Poly Haven's tonemapped JPG of the panorama (no HDR decoding needed);
    the raw .hdr is also downloaded for anyone who wants their own tonemap."""
    files = get_json(f"{PH}/files/{asset}")
    out = OUT / f"skybox_{asset}"; out.mkdir(parents=True, exist_ok=True)
    tm = files.get("tonemapped", {})
    src = None
    if tm.get("jpg") or tm.get("url"):
        f = tm.get("jpg") or tm
        src = download(f["url"], out / "pano_tonemapped.jpg")
    hdr = files.get("hdri", {}).get(res, {})
    if hdr.get("hdr"):
        download(hdr["hdr"]["url"], out / "pano.hdr")
    if src is None:
        raise SystemExit("no tonemapped panorama available; convert pano.hdr yourself (imageio[opencv])")
    import numpy as np, py360convert
    from PIL import Image
    img = np.asarray(Image.open(src).convert("RGB"))
    faces = py360convert.e2c(img, face_w=1024, cube_format="dict")
    names = {"F": "Ft", "R": "Rt", "B": "Bk", "L": "Lf", "U": "Up", "D": "Dn"}
    for k, v in faces.items():
        Image.fromarray(v).save(out / f"Skybox{names[k]}.png")
    (out / "recipe.json").write_text(json.dumps({"source": "polyhaven", "id": asset, "license": "CC0", "faces": [f"Skybox{n}.png" for n in names.values()],
                                                 "note": "upload each face with upload.py --type Image, then set Sky.Skybox{Bk,Dn,Ft,Lf,Rt,Up}; Roblox faces are square, Up/Dn orientation may need a 180-degree rotation, check in Studio"}, indent=1))
    print(out)


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("q")
    f = sub.add_parser("fetch"); f.add_argument("source", choices=["polyhaven", "ambientcg"]); f.add_argument("id"); f.add_argument("--res", default="1k")
    k = sub.add_parser("skybox"); k.add_argument("source", choices=["polyhaven"]); k.add_argument("id"); k.add_argument("--res", default="2k")
    a = ap.parse_args()
    if a.cmd == "search": search(a.q)
    elif a.cmd == "fetch": (fetch_polyhaven if a.source == "polyhaven" else fetch_ambientcg)(a.id, a.res if a.source == "polyhaven" else a.res.upper())
    elif a.cmd == "skybox": skybox_polyhaven(a.id, a.res)


if __name__ == "__main__":
    main()
