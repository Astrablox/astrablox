"""layout_export.py: write layout.json, the placement of every piece and camera of a Blender scene, for import into Roblox.

Run:  python tools/blender/blender.py tools/blender/bpy/layout_export.py --blend work/scene.blend -- --out builds/12/layout.json --scene harbour --build 12 [--all]

Schema (the one the studio lane reads; docs/contract.md §8):
  { "scene": "<id>", "build": <n>, "source": "<blend>", "units": "metres", "up": "Y", "studs_per_metre": 3.5714,
    "pieces": [ { "name", "asset": "assets/<lane>/<name>/" | null, "glb": "<path>" | null,
                  "parent": "Workspace.Scene.<scene>.<group>", "position": [x,y,z], "rotation_euler_xyz_deg": [rx,ry,rz],
                  "scale": [sx,sy,sz], "collision": "gameplay" | "decoration", "anchored": true,
                  "blender": { "location_m", "rotation_deg", "scale", "dimensions_m" } } ],
    "cameras": [ { "name", "position": [x,y,z], "look_at": [x,y,z], "fov_deg_vertical": <n>, "render": "<png or null>" } ] }
Transforms are metres, Y-up (the GLB export convention); `blender` keeps the original Z-up values for
debugging. A piece is an object with custom property `piece` = its GLB path (set by the lane when it
exports); `asset` is derived as the GLB's folder; custom properties `collision` ("gameplay" or
"decoration"; default decoration for objects without `piece`, gameplay for pieces), `anchored`
(default true), `group` (default the object's Blender collection name), `render` on a camera (path of
its render) refine the entry. Cameras, lights and objects marked `is_ground` are skipped unless --all.
Prints LAYOUT <path> <count> pieces, <count> cameras.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(prog="layout_export.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--out", default="out/layout.json")
ap.add_argument("--scene", default="")
ap.add_argument("--build", type=int, default=0)
ap.add_argument("--all", action="store_true", help="include objects marked is_ground")
ap.add_argument("--stud", type=float, default=0.28, help="metres per stud")
a = ap.parse_args(argv)

OUT = os.path.abspath(a.out)
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
# Blender Z-up -> Roblox/GLB Y-up: (x, y, z) -> (x, z, -y), the same axis change the glTF exporter applies.
TO_YUP = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))


def r3(v):
    return [round(float(x), 4) for x in v]


def yup(mw):
    return TO_YUP @ mw @ TO_YUP.inverted()


scene_id = a.scene or bpy.context.scene.name
pieces, cameras = [], []
for o in bpy.context.scene.objects:
    if o.type == "CAMERA":
        m = yup(o.matrix_world)
        loc, rot, _ = m.decompose()
        forward = rot @ Vector((0, 0, -1))
        look_at = loc + forward * 10
        sensor = o.data.sensor_height if o.data.sensor_fit == "VERTICAL" else o.data.sensor_width
        fov_v = 2 * math.degrees(math.atan((o.data.sensor_width * (bpy.context.scene.render.resolution_y / bpy.context.scene.render.resolution_x)) / (2 * o.data.lens))) if o.data.sensor_fit != "VERTICAL" else 2 * math.degrees(math.atan(sensor / (2 * o.data.lens)))
        cameras.append({"name": o.name, "position": r3(loc), "look_at": r3(look_at), "fov_deg_vertical": round(fov_v, 2), "render": o.get("render")})
        continue
    if o.type not in ("MESH", "EMPTY"):
        continue
    if o.get("is_ground") and not a.all:
        continue
    mw = o.matrix_world
    loc, rot, scl = mw.decompose()
    yloc, yrot, yscl = yup(mw).decompose()
    glb = o.get("piece")
    group = o.get("group") or (o.users_collection[0].name if o.users_collection else "Pieces")
    pieces.append({
        "name": o.name,
        "asset": (os.path.dirname(glb).replace("\\", "/") + "/") if glb else None,
        "glb": glb,
        "parent": f"Workspace.Scene.{scene_id}.{group}",
        "position": r3(yloc),
        "rotation_euler_xyz_deg": r3(math.degrees(e) for e in yrot.to_euler("XYZ")),
        "scale": r3(yscl),
        "collision": o.get("collision") or ("gameplay" if glb else "decoration"),
        "anchored": bool(o.get("anchored", True)),
        "blender": {
            "location_m": r3(loc),
            "rotation_deg": r3(math.degrees(e) for e in rot.to_euler("XYZ")),
            "scale": r3(scl),
            "dimensions_m": r3(list(o.dimensions)),
        },
    })

payload = {
    "scene": scene_id,
    "build": a.build,
    "source": bpy.data.filepath,
    "units": "metres",
    "up": "Y",
    "studs_per_metre": round(1.0 / a.stud, 4),
    "pieces": pieces,
    "cameras": cameras,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=1)
print("LAYOUT", OUT, sum(1 for p in pieces if p["glb"]), "pieces,", len(cameras), "cameras")
