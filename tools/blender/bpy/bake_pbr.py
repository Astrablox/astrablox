"""bake_pbr.py: bake every mesh's material to image textures Roblox can use, and rewire the material to those images.

Run:  python tools/blender/blender.py tools/blender/bpy/bake_pbr.py --blend work/asset.blend -- --out work/textures [--size 2048] [--only Name1,Name2] [--save work/asset_baked.blend]

Per mesh object (all visible meshes unless --only): ensures UVs (Smart UV Project when none), bakes
color, roughness, metallic, normal (tangent space, OpenGL) and ambient occlusion to PNG, then replaces
the material with a Principled BSDF that reads those images, which is the only kind of material that
survives GLB export. Procedural node trees are baked as they render, so keep them until this step.
Multi-material objects are baked as one atlas (one texture set per mesh, as Roblox wants).
Saves the rewired scene to --save (default: <blend>_baked.blend). Prints BAKED <object> <maps> -> <folder>
and SAVED <path>. Objects marked is_ground are skipped. Run this before export_glb.py; a change to
geometry or material after baking needs a new bake (readiness resets to rendered, contract §6).
"""
import argparse
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(prog="bake_pbr.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--out", default="work/textures", help="folder for <Object>_<map>.png")
ap.add_argument("--size", type=int, default=2048, help="texture size in pixels (Roblox downsamples above 1024)")
ap.add_argument("--only", help="comma-separated object names")
ap.add_argument("--save", help="where to save the rewired scene (default <blend>_baked.blend)")
a = ap.parse_args(argv)
OUT = os.path.abspath(a.out); SIZE = a.size; ONLY = a.only
SAVE = a.save or bpy.data.filepath.replace(".blend", "_baked.blend")
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.bake_type = "DIFFUSE"
sc.render.bake.use_pass_direct = False; sc.render.bake.use_pass_indirect = False; sc.render.bake.margin = 8

targets = [o for o in sc.objects if o.type == "MESH" and o.visible_get() and not o.get("is_ground")
           and any(s.material for s in o.material_slots) and (not ONLY or o.name in ONLY.split(","))]
skipped = [o.name for o in sc.objects if o.type == "MESH" and o.visible_get() and o not in targets]
if skipped:
    print("SKIPPED (no material or is_ground):", ", ".join(skipped))

def ensure_uv(o):
    if not o.data.uv_layers:
        bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02); bpy.ops.object.mode_set(mode="OBJECT")

def bake_map(o, kind, img):
    """kind: color | roughness | metallic | normal | ao. Uses an emission detour for scalar channels."""
    nodes_added = []
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.use_nodes:
            continue
        nt = m.node_tree
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; nt.nodes.active = tex; nodes_added.append((nt, tex))
        if kind in ("roughness", "metallic", "color"):
            bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
            if bsdf and out:
                emit = nt.nodes.new("ShaderNodeEmission"); nodes_added.append((nt, emit))
                src = {"roughness": "Roughness", "metallic": "Metallic", "color": "Base Color"}[kind]
                inp = bsdf.inputs[src]
                if inp.is_linked:
                    nt.links.new(inp.links[0].from_socket, emit.inputs["Color"])
                else:
                    v = inp.default_value; emit.inputs["Color"].default_value = (v, v, v, 1) if isinstance(v, float) else v
                m["_restore"] = out.inputs["Surface"].links[0].from_node.name if out.inputs["Surface"].is_linked else ""
                nt.links.new(emit.outputs[0], out.inputs["Surface"])
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
    if kind in ("roughness", "metallic", "color"):
        bpy.ops.object.bake(type="EMIT")
    elif kind == "normal":
        sc.render.bake.normal_space = "TANGENT"; bpy.ops.object.bake(type="NORMAL")
    elif kind == "ao":
        bpy.ops.object.bake(type="AO")
    img.filepath_raw = os.path.join(OUT, f"{o.name}_{kind}.png"); img.file_format = "PNG"; img.save()
    for nt, n in nodes_added:
        nt.nodes.remove(n)
    for slot in o.material_slots:
        m = slot.material
        if m and m.use_nodes and m.get("_restore") is not None:
            nt = m.node_tree; out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
            src = nt.nodes.get(m["_restore"])
            if out and src:
                nt.links.new(src.outputs[0], out.inputs["Surface"])
            del m["_restore"]

for o in targets:
    ensure_uv(o)
    maps = {}
    for kind in ("color", "roughness", "metallic", "normal", "ao"):
        img = bpy.data.images.new(f"{o.name}_{kind}", SIZE, SIZE, alpha=False)
        if kind == "normal":
            img.colorspace_settings.name = "Non-Color"
        elif kind != "color":
            img.colorspace_settings.name = "Non-Color"
        bake_map(o, kind, img); maps[kind] = img
    # rewire: one exportable material
    m = bpy.data.materials.new(o.name + "_baked"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(bsdf.outputs[0], out.inputs[0])
    def tex(img, x, y):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = img; n.location = (x, y); return n
    c = tex(maps["color"], -600, 300); nt.links.new(c.outputs[0], bsdf.inputs["Base Color"])
    r = tex(maps["roughness"], -600, 0); nt.links.new(r.outputs[0], bsdf.inputs["Roughness"])
    mt = tex(maps["metallic"], -600, -300); nt.links.new(mt.outputs[0], bsdf.inputs["Metallic"])
    n = tex(maps["normal"], -600, -600); nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(n.outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    o.data.materials.clear(); o.data.materials.append(m)
    print("BAKED", o.name, ",".join(maps), "->", OUT)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(SAVE)); print("SAVED", SAVE)
