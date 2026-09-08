# tools/blender — headless Blender toolkit

Every Blender step of the studio runs through these scripts; the GUI and MCP bridges are not used
(contract §10). One launcher, four bpy scripts, one plain-Python compositor.

| Tool | Does | Prints / writes |
|---|---|---|
| `blender.py` | finds the Blender binary (`BLENDER` env, PATH, standard installs) and runs a bpy script headless | the command, Blender's exit code |
| `bpy/render_views.py` | renders a .blend from fixed cameras (near / far / quarter) under reference lighting: Nishita sky, warm sun, finite fog box | `<out>/<stage>_<view>.png`, `MEAN_BRIGHTNESS <view> <0-255>` |
| `bpy/bake_pbr.py` | bakes color, roughness, metallic, normal, AO per mesh and rewires the material to those images | `<out>/<Object>_<map>.png`, `<blend>_baked.blend` |
| `bpy/export_glb.py` | exports visible meshes to one GLB (Y-up, modifiers applied) and re-imports it to verify Roblox limits | `<out>.glb`, `<out>.glb.verify.json`, `VERDICT: OK/REFUSED`, exit 2 when refused |
| `bpy/layout_export.py` | writes `layout.json` in the schema the `studio` lane reads: `scene`, `build`, `units: metres`, `up: Y`, `studs_per_metre`, `pieces[]` (name, asset, glb, parent `Workspace.Scene.<scene>.<group>`, position, rotation_euler_xyz_deg, scale, collision, anchored, plus the Blender Z-up values) and `cameras[]` (name, position, look_at, fov_deg_vertical, render) | `layout.json`, `LAYOUT <path> <n> pieces, <m> cameras` |
| `side_by_side.py` | render and target frame in one PNG with labels (plain Python + Pillow) | `SIDE_BY_SIDE <path>` |

## Order for a world piece

```
python tools/blender/blender.py tools/blender/bpy/render_views.py --blend work/pier.blend -- --out work/pier/renders --stage blockout
python tools/blender/blender.py tools/blender/bpy/bake_pbr.py    --blend work/pier.blend -- --out work/pier/textures --size 1024
python tools/blender/blender.py tools/blender/bpy/export_glb.py  --blend work/pier_baked.blend -- --out assets/world/pier/pier.glb
python tools/blender/side_by_side.py --left work/pier/renders/final_far.png --right game/scenes/harbour/target.png --out work/pier/sbs_far.png
```

For a scene assembly add `layout_export.py` on the assembly .blend; the studio lane reads `layout.json`
to place the imported pieces. `tools/board/build_publish.py` calls `side_by_side.py` for every render.

## Rules the scripts encode

- Objects with the custom property `is_ground` are rendered but never framed, baked or exported.
- Lighting in `render_views.py` is a finite fog cube with Volume Scatter, not a world volume: a world
  volume is infinite in Cycles, swallows the sun and produces black frames. `--keep-world` keeps the
  file's own lighting when the lane has matched it to the target frame deliberately.
- `MEAN_BRIGHTNESS` under 20 means a black frame: fix lighting or camera, do not submit it as evidence.
- Bake before export: GLB keeps only Principled BSDF with image textures. A change to geometry or
  material after the bake resets the asset to `rendered` (§6) and needs a new bake.
- `export_glb.py` verification output (`*.verify.json`) is the evidence for `glb_verified`.
- Pass script arguments after `--`; `-- --help` prints a script's own help.

## Test

`BLENDER=<binary> python -B tests/test_blender_tools.py` builds `tests/fixtures/make_lantern.py`, renders
(checks frames are not black), bakes, exports, verifies and writes the layout. Skipped when `BLENDER` is unset.
