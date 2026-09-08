"""export_glb.py: export the visible meshes as one GLB for Roblox, then verify it by re-importing in a clean scene.

Run:  python tools/blender/blender.py tools/blender/bpy/export_glb.py --blend work/asset_baked.blend -- --out out/asset.glb [--only Name1,Name2]

Applies modifiers, Y-up, includes materials and packed textures. Then opens a fresh scene, imports the
GLB and prints per mesh: triangles, materials, images and their sizes, bounding box in metres, and
VERDICT: OK or REFUSED (Roblox rejects a mesh above 20,000 triangles or a file above 20 MB; textures
above 1024 are downsampled by Roblox, so anything larger only costs upload size). Exit 2 when refused.
The report is also written to <out>.verify.json: this file is the EVIDENCE for the glb_verified state.
Roblox studs: 1 stud = 0.28 m; the importer lets you scale on import, so author in metres.
"""
import argparse
import json
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(prog="export_glb.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--out", default="out/asset.glb")
ap.add_argument("--only", help="comma-separated object names")
a = ap.parse_args(argv)
OUT = os.path.abspath(a.out); ONLY = a.only
os.makedirs(os.path.dirname(OUT), exist_ok=True)
sc = bpy.context.scene
bpy.ops.object.select_all(action="DESELECT")
sel = 0
for o in sc.objects:
    if o.type == "MESH" and o.visible_get() and not o.get("is_ground") and (not ONLY or o.name in ONLY.split(",")):
        o.select_set(True); sel += 1
if not sel:
    raise SystemExit("nothing to export")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
                          export_materials="EXPORT", export_image_format="AUTO", export_texcoords=True, export_normals=True)
size = os.path.getsize(OUT); print("EXPORTED", OUT, size // 1024, "KB")

# verify in a clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT)
report = {"file": OUT, "bytes": size, "meshes": [], "images": [], "refused": []}
for o in bpy.context.scene.objects:
    if o.type != "MESH":
        continue
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    dims = [round(max(v[i] for v in bb) - min(v[i] for v in bb), 2) for i in range(3)]
    mats = [m.name for m in o.data.materials if m]
    report["meshes"].append({"name": o.name, "triangles": tris, "materials": mats, "dimensions_m": dims, "uv": bool(o.data.uv_layers)})
    if tris > 20000:
        report["refused"].append(f"{o.name}: {tris} triangles > 20000")
for img in bpy.data.images:
    if img.size[0]:
        report["images"].append({"name": img.name, "size": list(img.size)})
if size > 20 * 1024 * 1024:
    report["refused"].append(f"file {size} bytes > 20 MB")
if not report["images"]:
    report["refused"].append("no textures in GLB: materials will import flat; run bake_pbr.py first")
report["verdict"] = "REFUSED" if report["refused"] else "OK"
print(json.dumps(report, indent=1)); print("VERDICT:", report["verdict"])
with open(OUT + ".verify.json", "w") as f:
    json.dump(report, f, indent=1)
sys.exit(2 if report["refused"] else 0)
