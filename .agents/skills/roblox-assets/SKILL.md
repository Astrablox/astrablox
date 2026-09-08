---
name: roblox-assets
description: Use when bringing assets into a Roblox place: building a style kit before construction, Creator Store search and insert, generate_mesh, generate_material, procedural models, licences and script safety, provenance and verification. Not for composing or lighting a scene, and not for gameplay code.
---

# Getting assets into a Roblox place

Everything below is about acquisition and verification. How to compose, place and light what you acquired is in `$roblox-environment-art`, `$roblox-materials` and `$roblox-lighting-atmosphere`.

## The strategy: kit first, then build

A world looks assembled when every piece comes from a different author and looks made when a small family of pieces is used many times. So the order is: choose and verify the style kit, then build with it. Building first and sourcing assets while you build produces zones that do not belong to the same world, and the fix costs a rebuild.

Beyond the Dark, the Roblox showcase, built about ninety percent of its architecture from a handful of swappable trim sheet sets on one grid, and updated a thousand instances by editing a package. That is what a kit does.

Four rules decide whether the kit works:

**One source of style.** Pick the family the world is made of and reject anything that fights it, however good the individual asset is. The failures people name on other people's builds are always source failures: rocks that do not match the terrain, models that look like plastic beside natural ground, a skybox from another world.

**Reuse beats variety.** Many instances of one good tree read better than as many different trees. Variation comes from rotation, scale, grouping and light, not from sourcing a different model each time.

**Verified or out.** An asset is in the kit only after you looked at it in the place. A tool that returns success has not produced an asset that loaded, and an asset that loaded is not one that looks right. Rejected candidates get recorded with the reason so nobody retries them.

**Provenance always.** Every asset carries where it came from, what may be done with it, and whether it loaded. Without it the studio cannot answer a licence question and cannot reproduce the build.

Models do not use a library they were merely given access to; using the kit has to be a step that somebody owns, which is why the art-director builds it and hands it over rather than telling builders to source their own.

## The paths, and what each is actually for

| Path | Good for | Bad for |
|---|---|---|
| Creator Store search and insert | props, furniture, foliage, audio, one-off set pieces | a whole coherent world; styles collide, quality varies |
| Cube generation (`generate_mesh`) | a hero prop whose exact shape you need and nobody sells | environment fabric, anything needing clean topology or crisp texture |
| `generate_material` | surface language: tiling PBR sets with normal and roughness | precise art-directed detail on a specific object |
| Procedural models (`generate_procedural_model`, `ProceduralModel`) | repeated parametric structure: stairs, walls, fences, towers, bridges | organic shapes, hero silhouettes |
| EditableMesh + `CreateDataModelContentAsync` | procedural geometry and textures written from code | anything achievable by placing existing pieces; it is expensive to author |
| External CC0 packs through Open Cloud upload (`tools/assets/upload.py --batch`) | a stylistically complete fantasy kit in one style | needs `ROBLOX_API_KEY`; placement still happens in Studio |

### Creator Store

Search with `search_asset`, bring the chosen asset in with `insert_asset` (both Studio MCP). Search covers free assets, paid assets and the group inventory.

Security is the real risk, not quality. Free models are a known vector for malicious scripts. After inserting: inspect the whole descendant tree for `Script`, `LocalScript` and `ModuleScript` instances anywhere in the model, including inside nested containers. Do not enable, run or keep executable code that arrived with an asset; remove it, or leave it disabled and hand it to the code owner for review before anything is enabled. An asset whose function depends on its scripts is usually the wrong asset for a kit.

Licences: free Creator Store assets may be used in experiences under the Creator Store terms; paid assets have to be bought by the account that will use them. Record the asset id and the permitted use for every entry.

Loading a third-party asset from code inside an experience is a different path: `AssetService:LoadAssetAsync(id)` loads free models that are not in the inventory, returns a sandboxed root whose scripts do not execute, and requires "Allow Loading Third Party Assets" to be enabled in Game Settings, Security. It is off by default. The older `InsertService:LoadAsset` returns 403 for third-party free models.

Audio: the Too Lost catalogue is in the Creator Store and licensed for use in experiences, alongside the Roblox audio library. Never invent an audio id; verify that the sound actually plays at runtime, because the properties of a `Sound` prove nothing about whether the asset resolved.

### Cube generation, `generate_mesh`

What it gives you: a textured `MeshPart` in twenty to forty seconds from a text prompt, optionally guided by an image.

The controls that matter:
- **Bounding box.** The generator takes the size and proportions of a `Part` you select. This is how you control scale and shape; a prompt alone will not give you the proportions you need.
- **Triangle budget.** The tool defaults to about ten thousand triangles. The engine refuses meshes above twenty thousand triangles per `MeshPart` at upload, so a large object is several meshes. These are engine and tool limits, not a quality target.
- **Hint image.** An image reference moves the result more than more adjectives do.
- **Segmentation.** A generated mesh can be split into up to eight parts when you need separately movable pieces.
- **Determinism.** The same prompt gives the same result. Variation needs different prompts, or transforms applied afterwards.

What it is honestly good for. Developers who have used it in production call the output placeholder quality: decimated sculpt topology and weak textures, and a style that does not land on the Roblox low-poly look by itself. Use it for a hero prop whose exact shape the world needs, then check that prop at the distance the player sees it. Do not build the fabric of an environment out of generated meshes.

In-experience generation through `GenerationService:GenerateModelAsync` exists with the same model, needs the `DynamicGeneration` capability and owner ID verification, and is rate limited per experience. There is no headless REST endpoint for mesh generation.

### `generate_material`

Produces a PBR material set you can apply as a `MaterialVariant`. This is usually a better spend than generating geometry: material depth is what separates an expensive surface from a cheap one, and a generated tiling material with normal and roughness maps lifts geometry you already have. Check that the result actually carries normal and roughness rather than colour alone, and check it on a large surface at a raking angle, because that is where a flat or stretched material shows.

### Procedural models

`generate_procedural_model` in the MCP, and the `ProceduralModel` instance in the engine (full release, May 2026). A procedural model is a container plus a generator module with attributes and an `OnGenerate(params, targetContainer)` function; changing an attribute or resizing rebuilds the geometry. Removing the generator bakes the result into ordinary instances.

For this studio the value is a reusable parametric library: a wall section, a stair run, a railing, a tower, a bridge span, a fence built once as parameters and instantiated with different values wherever the world needs it, instead of writing new geometry code per zone. AI generation of procedural models is rate limited per day; a hand-written generator has no such limit and is usually more controllable.

Keep generators out of the shipped world when they are not needed at runtime: bake, and keep the generator in the kit container.

### EditableMesh and EditableImage

`AssetService:CreateDataModelContentAsync` turns editable meshes and images into static content usable in a published experience. This is the only path to geometry and textures authored entirely from code: eroded rock, custom terrain shells, decal atlases, noise textures.

Limits to plan around: eight `EditableMesh` objects per client, server-side content up to two hundred megabytes, and the batching APIs that make large edits fast are still a Studio beta. Skinning is not supported through batching. Treat this as a specialist tool for a specific need, not a default.

### External CC0 packs and generated hero assets — through the shell tools

The reliable route to a stylistically complete fantasy world is an external CC0 kit uploaded as the studio's own
assets, and the reliable route to a hero prop or a creature nobody sells is a concept image turned into a mesh.
Both exist as shell tools in `tools/assets/` (read `tools/assets/README.md`):

- `assets-library/INDEX.md` and `catalog.json`: CC0 kits already catalogued with triangle counts, animations and
  thumbnails (KayKit dungeon, characters, skeletons, medieval hexagon; Quaternius fantasy packs). Pick a family
  from here first; it is a kit by construction.
- `store_search.py`: Creator Store search with triangles, scripts, votes and price per result.
- `textures.py`: CC0 PBR sets (Poly Haven, ambientCG) as the maps Roblox wants, and HDRI skyboxes.
- `concept.py` + `gen3d.py` (Tripo P1, `--rig` for creatures) + `optimize.py`: concept -> mesh -> Roblox-ready GLB.
- `upload.py`: Open Cloud upload, single file or a whole catalog; returns asset ids with provenance.
- `insert.luau`: the Studio MCP snippet that brings an uploaded asset into `ServerStorage.StyleKit`.

The tools need API keys in the environment (`ROBLOX_API_KEY`, `TRIPO_API_KEY`, `OPENAI_API_KEY`); without them
they run dry and say so. A dry run is not an asset: report the missing key as the blocker, name what the
fallback loses, and do not substitute a cheaper look silently. Check each pack's licence at its source (KayKit
and Kenney are CC0; Quaternius has its own free licence that forbids reselling the assets themselves).

## Verifying an asset

An asset is verified when all of this is true and recorded:

- It exists in the place under the container it belongs in, found by reading it back rather than by trusting the response of the tool that created it.
- You looked at it in the place at player eye height, at the distance the player will see it from. For a hero piece, look at it in the frame of the acceptance view it is meant to appear in.
- Its real size and pivot are known. A pivot in the wrong place turns into a placement bug for whoever uses the kit; `Model:PivotTo` moves the pivot, and an imported model's true orientation has to be checked rather than assumed.
- Its textures resolved. A mesh that loaded with a missing texture reads as flat grey and is easy to miss in a small viewport.
- Its collision behaviour is decided: what the player can walk on, what is decoration with collision off, and where a simple invisible collider does the physical work instead of the visible mesh.
- Nothing executable came with it, or what came with it is quarantined and named for review.

## What to record for every asset

Name and job in the kit. Source and identifier: the Creator Store asset id, the generation prompt and job, or the pack and file. Permitted use. Load status, and if it failed, how it failed. Real dimensions and pivot. Materials and textures it depends on. Collision setup. Where it lives in the place. If it was rejected, the reason.

Unknown cost stays unknown. Do not write down a performance number you did not measure.

## Failures worth knowing before they happen

- Trusting a success message instead of looking. The most common way a kit ends up with an asset nobody can see.
- Sourcing per need. One asset from each of ten authors gives ten styles.
- Generating environment fabric. Generated meshes look like placeholders in bulk, which is exactly how the cheap look happens.
- Colour without normal or roughness. The most cited reason custom surfaces still look flat.
- Stretched tiling. A texture scaled to fit a large face reads as low resolution.
- Enabling a script that arrived inside a free model.
- Substituting quietly when acquisition fails, instead of reporting the blocker and stating what the fallback loses.

## Sources

Studio MCP tools: https://create.roblox.com/docs/studio/mcp
Cube generation and `GenerationService`: https://create.roblox.com/docs/reference/engine/classes/GenerationService · https://devforum.roblox.com/t/beta-cube-3d-generation-tools-and-apis-for-creators/3558947
Procedural models: https://devforum.roblox.com/t/full-release-procedural-models-build-parametrized-3d-models-with-code-or-ai/4642542 · https://create.roblox.com/docs/parts/procedural-models
Editable mesh content: https://devforum.roblox.com/t/full-release-introducing-createdatamodelcontent-convert-editable-mesh-and-image-data-into-static-content/4541898
Loading third-party assets in experience: https://devforum.roblox.com/t/loading-third-party-model-assets-in-experience/3939065
Open Cloud assets upload: https://create.roblox.com/docs/cloud/guides/usage-assets
Mesh and texture specifications: https://create.roblox.com/docs/art/modeling/specifications
Kit and trim sheet practice: https://create.roblox.com/docs/resources/beyond-the-dark/building-architecture
CC0 packs: https://kaylousberg.itch.io · https://quaternius.com · https://kenney.nl/assets · https://polyhaven.com
