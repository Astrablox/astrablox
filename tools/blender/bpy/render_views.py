"""render_views.py: render a .blend from fixed cameras with reference-matched lighting, so every stage
of a piece is compared on equal terms and against the target frame.

Run:
  python tools/blender/blender.py tools/blender/bpy/render_views.py --blend work/asset.blend -- \\
      --out out/renders --stage blockout [--samples 64] [--views near,far,quarter] [--scene-cameras RefCam] [--size 1600x900] [--keep-world]

Cameras are placed from the bounding box of all visible meshes (objects with the custom property
`is_ground` are excluded from framing but rendered):
  near     player eye height (1.6 m), close in front of the asset     -> what a player standing next to it sees
  far      player eye height, far away                                -> does the silhouette read
  quarter  elevated three-quarter view                                -> overall form
Lighting: unless --keep-world, the world is replaced by a golden-hour Nishita sky, a warm low sun and
a finite fog box (Volume Scatter in a cube around the scene). A world volume is not used: in Cycles a
world volume is infinite, it swallows the sun and the frames come out black.
Output: <out>/<stage>_<view>.png, one line `RENDERED <path>` per view and `MEAN_BRIGHTNESS <view> <0-255>`
computed from the saved pixels (a value under 20 means the frame is black: lighting or camera is wrong).
Cycles, GPU if available, else CPU.
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(prog="render_views.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--out", default="out/renders")
ap.add_argument("--stage", default="stage")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--views", default="near,far,quarter")
ap.add_argument("--size", default="1600x900", help="WxH pixels")
ap.add_argument("--keep-world", action="store_true", help="keep the file's own world and lights")
ap.add_argument("--fog-density", type=float, default=0.004)
ap.add_argument("--scene-cameras", default="", help="comma-separated names of camera objects already in the .blend (e.g. the reconstructed reference camera) to render in addition to the fixed views; rendered as <stage>_<camera name>.png")
a = ap.parse_args(argv)

OUT = os.path.abspath(a.out)
os.makedirs(OUT, exist_ok=True)
W, H = (int(v) for v in a.size.lower().split("x"))
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = a.samples
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.view_settings.view_transform = "AgX"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            if any(d.use for d in prefs.devices if d.type != "CPU"):
                sc.cycles.device = "GPU"
                break
        except Exception:
            continue
except Exception:
    pass

meshes = [o for o in sc.objects if o.type == "MESH" and o.visible_get() and not o.get("is_ground")]
if not meshes:
    raise SystemExit("no visible mesh objects to frame")
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
centre = (lo + hi) / 2
size = max(max(hi - lo), 0.5)
print("BBOX", tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi))

if not a.keep_world:
    w = bpy.data.worlds.new("ReferenceSky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(8)
    sky.sun_rotation = math.radians(160)
    sky.sun_intensity = 0.4
    sky.altitude = 300
    sky.air_density = 1.4
    sky.dust_density = 2.0
    bg = nt.nodes["Background"]
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.15
    for o in [o for o in sc.objects if o.type == "LIGHT"]:
        o.hide_render = True
    sun_data = bpy.data.lights.new("RV_Sun", "SUN")
    sun_data.energy = 5.0
    sun_data.angle = math.radians(2)
    sun_data.color = (1.0, 0.78, 0.55)
    sun = bpy.data.objects.new("RV_Sun", sun_data)
    sc.collection.objects.link(sun)
    sun.location = (0, 0, 50)
    sun.rotation_euler = (math.radians(80), 0, math.radians(160))
    # finite fog box: a cube with Volume Scatter around the scene (a world volume is infinite and swallows the sun)
    fog_size = max(60.0, size * 12)
    fog_mesh = bpy.data.meshes.new("RV_FogBox")
    s = fog_size / 2
    verts = [(x, y, z) for x in (-s, s) for y in (-s, s) for z in (-s, s)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    fog_mesh.from_pydata(verts, [], faces)
    fog = bpy.data.objects.new("RV_FogBox", fog_mesh)
    sc.collection.objects.link(fog)
    fog.location = (centre.x, centre.y, lo.z + s * 0.8)
    fog.display_type = "WIRE"
    fog.visible_shadow = False
    fog["is_ground"] = True  # keep it out of framing and export
    fm = bpy.data.materials.new("RV_Fog")
    fm.use_nodes = True
    fnt = fm.node_tree
    fnt.nodes.clear()
    fo = fnt.nodes.new("ShaderNodeOutputMaterial")
    fv = fnt.nodes.new("ShaderNodeVolumeScatter")
    fv.inputs["Density"].default_value = a.fog_density
    fv.inputs["Anisotropy"].default_value = 0.5
    fnt.links.new(fv.outputs[0], fo.inputs["Volume"])
    fog_mesh.materials.append(fm)


def camera(name, pos, target, lens=32):
    cam = bpy.data.objects.get("RV_" + name)
    if cam is None:
        data = bpy.data.cameras.new("RV_" + name)
        cam = bpy.data.objects.new("RV_" + name, data)
        sc.collection.objects.link(cam)
    cam.location = pos
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.data.clip_end = 5000
    direction = Vector(target) - Vector(pos)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return cam


eye = 1.6
front = Vector((0, -1, 0))
cams = {
    "near": camera("near", centre + front * max(6, size * 0.9) + Vector((0, 0, eye - centre.z)),
                   Vector((centre.x, centre.y, min(centre.z, lo.z + size * 0.45))), 28),
    "far": camera("far", centre + front * max(20, size * 2.5) + Vector((0, 0, eye - centre.z)),
                  Vector((centre.x, centre.y, lo.z + size * 0.4)), 40),
    "quarter": camera("quarter", centre + Vector((-1, -1, 0.55)).normalized() * size * 1.8, centre, 35),
}


def mean_brightness(path):
    img = bpy.data.images.load(path)
    try:
        px = img.pixels[:]
        n = len(px) // 4
        if not n:
            return 0.0
        step = max(1, n // 20000)
        vals = [(px[i * 4] + px[i * 4 + 1] + px[i * 4 + 2]) / 3 for i in range(0, n, step)]
        lin = sum(vals) / len(vals)
        return 255.0 * (lin ** (1 / 2.2))  # pixels are linear; report roughly as the PNG stores them
    finally:
        bpy.data.images.remove(img)


for name in [n.strip() for n in a.scene_cameras.split(",") if n.strip()]:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "CAMERA":
        print("SKIP missing scene camera", name)
        continue
    cams[name] = obj

for v in list(a.views.split(",")) + [n.strip() for n in a.scene_cameras.split(",") if n.strip()]:
    if v not in cams:
        print("SKIP unknown view", v)
        continue
    sc.camera = cams[v]
    sc.render.filepath = os.path.join(OUT, f"{a.stage}_{v}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath)
    print("MEAN_BRIGHTNESS", v, round(mean_brightness(sc.render.filepath), 1))
