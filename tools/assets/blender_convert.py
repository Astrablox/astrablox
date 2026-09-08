"""Headless Blender: convert any model (usd/usda/fbx/obj/gltf/glb) to a Roblox-ready GLB, decimate, split.

Run:  blender -b --python blender_convert.py -- <in> <out.glb> [--target-tris N] [--split] [--apply-scale S]
  --target-tris N   decimate (collapse) each mesh so the total stays under N triangles (Roblox refuses > 20000 per mesh)
  --split           separate loose parts into their own meshes (big buildings -> several MeshParts)
  --apply-scale S   uniform scale before export (Quaternius/KayKit are authored at 1 unit = 1 m; Roblox 1 stud ~ 0.28 m)
Prints one JSON line with the result. Textures embedded in the GLB.
"""
import bpy, sys, json, os, math

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
src, dst = argv[0], argv[1]
opts = {"target_tris": None, "split": False, "scale": 1.0}
i = 2
while i < len(argv):
    if argv[i] == "--target-tris": opts["target_tris"] = int(argv[i + 1]); i += 2
    elif argv[i] == "--split": opts["split"] = True; i += 1
    elif argv[i] == "--apply-scale": opts["scale"] = float(argv[i + 1]); i += 2
    else: i += 1

bpy.ops.wm.read_factory_settings(use_empty=True)
ext = os.path.splitext(src)[1].lower()
if ext in (".usd", ".usda", ".usdc", ".usdz"):
    bpy.ops.wm.usd_import(filepath=src)
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=src)
elif ext == ".obj":
    bpy.ops.wm.obj_import(filepath=src)
elif ext in (".gltf", ".glb"):
    bpy.ops.import_scene.gltf(filepath=src)
else:
    raise SystemExit(f"unsupported input {ext}")

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
if opts["scale"] != 1.0:
    for o in meshes:
        o.scale = tuple(s * opts["scale"] for s in o.scale)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(scale=True)

if opts["split"]:
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.separate(type="LOOSE"); bpy.ops.object.mode_set(mode="OBJECT")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]

def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

total = sum(tri_count(o) for o in meshes)
decimated = []
if opts["target_tris"] and total > opts["target_tris"]:
    ratio = opts["target_tris"] / total
    for o in meshes:
        if tri_count(o) < 64: continue
        m = o.modifiers.new("dec", "DECIMATE"); m.ratio = ratio; m.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="dec")
        decimated.append(o.name)

bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_yup=True, export_apply=True,
                          export_animations=True, export_skins=True, export_materials="EXPORT", export_image_format="AUTO")
result = {"src": src, "dst": dst, "meshes": len(meshes), "triangles_before": total,
          "triangles_after": sum(tri_count(o) for o in meshes), "decimated": decimated,
          "animations": [a.name for a in bpy.data.actions], "roblox_ok": all(tri_count(o) <= 20000 for o in meshes)}
print("RESULT " + json.dumps(result))
