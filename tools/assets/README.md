# Asset tools

Shell tools that give the studio real assets instead of primitives. Every tool is a plain Python script
with `--help`; missing API keys turn a step into a dry run that says so. Run them from this directory
with `python3`. Outputs go to `$ASTRA_ASSET_ROOT` (default `./assets-work`), one folder per asset with a
`provenance.json` that records source, licence, parameters, hashes and Roblox asset ids.

| Tool | What it does | Needs |
|---|---|---|
| `store_search.py "query"` | Searches the Creator Store and prints, per asset: id, triangles, mesh parts, animations, whether it carries scripts, votes, free/paid, category. Use `--free --no-scripts --max-tris 20000` to keep only what can go straight into a kit. | nothing |
| `textures.py search / fetch / skybox` | CC0 PBR sets from Poly Haven and ambientCG as the exact maps Roblox wants (color, OpenGL normal, roughness, metalness, AO) plus a `recipe.json`; `skybox` turns a CC0 HDRI into the six cube faces for `Sky`. | nothing (skybox: `pip install py360convert imageio`) |
| `concept.py` | One concept image shaped for image-to-3D: single object, transparent background, 3/4 view, T-pose for characters. Style comes only from the style bible file. | `OPENAI_API_KEY` |
| `gen3d.py` | Concept image -> textured PBR GLB through Tripo. Default model P1 (native low-poly, honours `--face-limit`); `--hero` for H3 + quad; `--multiview` for characters; `--rig --rig-type quadruped` for creatures (Mixamo-spec skeleton, idle/walk/run). | `TRIPO_API_KEY`, `pip install tripo3d` |
| `optimize.py in.glb out.glb` | Weld, simplify to a triangle target, resize textures to 1024, then report triangles, size, maps, animations and whether Roblox will accept it (`--check-only` to inspect). | node (`npx @gltf-transform/cli`), `pip install trimesh pygltflib` |
| `blender_convert.py` | Headless Blender: any model (usd/usda/fbx/obj/gltf/glb) -> GLB, with `--target-tris`, `--split` (loose parts -> separate meshes) and `--apply-scale`. Keeps skins and animations. | a Blender binary; run as `blender -b --python blender_convert.py -- in out.glb [...]` |
| `upload.py` | Open Cloud upload of a GLB, image or audio; polls the operation and returns the asset id and moderation state. `--batch catalog.json --root kits/` bulk-uploads a CC0 catalog. | `ROBLOX_API_KEY` (assets write), `ROBLOX_CREATOR_USER_ID` or `_GROUP_ID` |
| `pipeline.py --subject ... --bible bible.md` | The four steps above in order for one asset, ending with the Luau snippet that inserts the uploaded model into `ServerStorage.StyleKit`. | all of the above for a full run; none for `--dry-run` |
| `insert.luau` | The snippet `pipeline.py` fills in: `InsertService:LoadAsset(id)` into the style kit, read back part/script counts and size. Run through Studio MCP `execute_luau` in Edit. | Studio MCP |
| `kit_manifest.py uploads.jsonl --out kit.json --luau insert_kit.luau --folder KayKitDungeon` | After a batch upload: the kit manifest (name, tags, triangles, animations, asset id) a role can pick from without opening Studio, and one Luau snippet that inserts the whole kit into `ServerStorage.StyleKit/<folder>` with any bundled scripts disabled. | nothing |
| `apply_material.luau` | Studio snippet: builds a `MaterialVariant` (Parts, Terrain) and a `SurfaceAppearance` template (MeshParts) from uploaded texture ids out of a `textures.py` recipe. | Studio MCP |
| `kit_catalog.py kits/ out/` | Builds `catalog.json` + `INDEX.md` + thumbnails for a folder of GLB/glTF kits (used for `assets-library/`). | `pip install trimesh pygltflib pillow numpy` |

## Facts the tools are built on

- Roblox refuses a mesh above 20 000 triangles and a file above 20 MB; the working target for kit pieces is
  under 10 000. Custom LOD chains are not accepted; RenderFidelity does the rest.
- Open Cloud uploads a GLB as a Model package of MeshParts with textures embedded. Whether PBR maps arrive as a
  `SurfaceAppearance` is expected from the Studio importer's behaviour but not yet confirmed on this account:
  verify on the first upload and, if needed, upload the maps as Image assets and build the SurfaceAppearance
  from `recipe.json`.
- Open Cloud cannot place anything into a place. Placement happens in Studio through MCP (`insert.luau`).
  Assets the account owns load with `InsertService:LoadAsset`; third-party assets need the place's
  "Allow Loading Third Party Assets" security setting.
- Audio uploads through Open Cloud are capped at 100 per month for ID-verified accounts; Studio's own uploader
  allows far more. Every asset passes moderation, so an id can exist before it renders for others.
- Generated meshes (Tripo P1/H3, Cube) are hero props and one-offs; the fabric of a world comes from a coherent
  kit. `assets-library/` holds CC0 kits already catalogued (KayKit, Quaternius) with triangle counts,
  animations and thumbnails.
- Style consistency comes from the style bible (a short text the art director writes: civilisation, materials,
  palette, signature detail, geometry style, texture style), not from the generator. `concept.py` adds only
  the framing image-to-3D needs.
- Scale: Tripo `auto_size` returns metres; one Roblox stud is roughly 0.28 m. KayKit and Quaternius are
  authored at 1 unit = 1 m. Set scale once per kit, not per piece.

## Typical runs

```
# find a rigged dragon that carries no scripts and fits the mesh limit
python3 store_search.py "dragon rigged" --free --no-scripts --max-tris 20000

# a hero prop from the style bible, end to end (dry run without keys)
python3 pipeline.py --subject "iron portcullis gate of a storm citadel" --bible bible.md --dry-run

# a storm dragon: concept in T-pose, multiview, rig as quadruped
python3 concept.py --slug storm_dragon --subject "enormous storm dragon, scales with glowing seams" --bible bible.md --pose tpose
python3 gen3d.py --slug storm_dragon --multiview --rig --rig-type quadruped --face-limit 18000

# castle stone as a Roblox material set, and a stormy sky
python3 textures.py fetch polyhaven castle_brick_02_red --res 1k
python3 textures.py skybox polyhaven kloppenheim_06 --res 2k

# a Quaternius pack piece to GLB at a Roblox-safe budget
blender -b --python blender_convert.py -- SK_Dragon.usda dragon.glb --target-tris 15000

# bulk-upload the dungeon kit (dry run first)
python3 upload.py --batch ../../assets-library/catalog.json --root kits/ --prefix "KayKit " --only-tag structure --dry-run
```
