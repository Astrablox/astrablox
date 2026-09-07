---
name: roblox-materials
description: Craft and API reference for Roblox surfaces - SurfaceAppearance and its PBR maps, the three-level material system (unique / shared trim / MaterialVariant), tinting through Overlay alpha, emissive masks, texel density and tiling, texture resolution and streaming, generated materials, and what to check after applying one. Use when a surface looks flat, plastic, stretched or wrong-scaled, when choosing between a built-in material, a MaterialVariant and a SurfaceAppearance, when building glowing runes or lava, and when authoring or assigning textures. Not for lighting, atmosphere and post-processing, not for particle textures, not for geometry, composition or set dressing (see roblox-environment-art).
---

# Materials and surfaces on Roblox

A part with a built-in material on it reads as a toy. The same shape with a colour, normal and roughness map on it reads as stone. This is the single largest visual difference available in the engine, and the people who ship the best-looking Roblox games say so directly. Twin Atlas: *"When Roblox released Surface Appearance, we were able to get some really cool materials in the game"*, and on emission maps, *"we have leveled up the visuals of some of our projects tenfold."* Ecos on PBR: *"an absolute game changer ... Our textures were able to become so much more photorealistic."* Fluorlite names 4K textures, emissive maps for fire and lava, and custom terrain material variants as the three things that mattered most.

The most common half-measure is the one to avoid: *"many custom Roblox surfaces still look flat because developers skip the normal and roughness maps, only adding the ColorMap."* The normal map is what catches raking light; without it a surface is a photograph glued to a box.

Numbers below are starting points from documentation and practitioners unless marked as an engine limit.

## The three-level material system

From the *Duvall Drive* showcase team, and it is the right way to organise a project:

1. **SurfaceAppearance for unique, 1:1 surfaces on meshes** — a marble statue, a carved gate, a hero prop with its own UV layout and its own maps.
2. **SurfaceAppearance for shared trim maps on MeshParts** — one set of maps used by the whole modular kit, with every kit mesh UV-mapped onto it. This is where most of the architecture lives.
3. **MaterialVariant for shared materials on Parts and terrain** — a variant overrides a built-in material everywhere it is used, so plain parts and terrain join the same material language.

Decide which level a surface belongs to before you author anything. Most surfaces are level 2 or 3; level 1 is for the few things the player walks up to.

## SurfaceAppearance

A `SurfaceAppearance` is a child of a `MeshPart` and replaces its material appearance with PBR maps:

- `ColorMap` — albedo. No baked lighting or shadows in it.
- `NormalMap` — surface direction. This is what makes light rake across a wall.
- `RoughnessMap` — how sharp reflections are. Variation here (wet patches, polished edges, dull dirt) sells a surface faster than more colour detail.
- `MetalnessMap` — metal or not. Mostly binary in practice.
- `AlphaMode` — `Transparency` uses the ColorMap alpha as cutout; `Overlay` uses it as a mask so the part's `Color`/`BrickColor` shows through.
- Emissive properties (`EmissiveMaskContent`, `EmissiveStrength`, `EmissiveTint`) — see below.

Assign in code by creating the instance under the MeshPart and setting the map properties to `rbxassetid://` content. Confirm the exact property names and types against the live schema before a large batch; the emissive properties are recent.

**Tinting through Overlay.** With `AlphaMode = Overlay` and an alpha mask in the ColorMap, one SurfaceAppearance set can be recoloured per instance through the part's `Color`. The Duvall Drive team used exactly this to *"apply BrickColor or Color3 to tint objects for visual variation"* from a single texture set — the cheapest source of variety in a kit, and the reason a kit does not have to look monotonous.

## MaterialVariant

A `MaterialVariant` under `MaterialService` overrides a built-in material. It carries the same map set plus `BaseMaterial` and `StudsPerTile`. Apply it by setting the part's `Material` to the base material and its `MaterialVariant` property to the variant name.

- This is how plain Parts and Terrain get PBR without becoming meshes.
- `StudsPerTile` is your texel-density control for parts and terrain: it decides how large one tile of the texture is in world space.
- Wet and dry variants of the same material, swapped by area or by weather, is a documented showcase technique (Duvall Drive used it for a stormy Pacific Northwest direction).
- Terrain currently supports overriding 21 of the 23 built-in materials this way. The Early Access programme for 64 custom terrain materials exists, but enabling it in a published place breaks the place for players outside the programme.

## Emissive masks

Live since February 2026 on `SurfaceAppearance`, `MaterialVariant` and `TerrainDetail`: `EmissiveMaskContent` plus `EmissiveStrength` and `EmissiveTint`. The mask marks which parts of the surface glow, so runes, cracks in lava, forge coals, magical seams and lit windows glow while the rest of the material stays a normal material.

Two facts that decide how you use it:

- It behaves like Neon for bloom purposes but **does not cast light onto other geometry**. If the object should illuminate its surroundings, a light source has to be placed there — and lights belong to the lighting owner, so name that anchor in your handoff instead of adding one.
- `EmissiveStrength` and `EmissiveTint` are ordinary properties, so they can be animated by script: a pulsing rune, a forge that brightens, a portal that charges. The runtime writer owns that animation; you build the surface and mark the anchor.

Compared to the old approach of a Neon part: emissive masks keep the material readable as stone or metal while glowing only where they should, which is why they look expensive and Neon rectangles look like 2016.

## Texel density and tiling

Texel density is how many texture pixels cover a stud of surface. Keep it consistent across a zone, or the eye reads the inconsistency as cheapness even when it cannot name it. The showcase complaint *"some PBR textures are clearly very stretched out, so it seems low-resolution"* is a texel-density failure, not a resolution failure.

- Check density by putting two objects that share a material next to each other and looking at the pattern scale on both.
- For parts and terrain, adjust `StudsPerTile`. For meshes, the UV layout decides it — a mesh scaled non-uniformly in Studio stretches its texture, so scale the mesh in one direction only when the material can survive it.
- Tileable textures must have no seam. Tile a test surface twice and look at the joint.
- Trim maps stay *"fairly clean and free of details that would be easily recognizable as repeating"* — one memorable crack becomes a stamp visible across the entire zone.
- A practical authoring target for a tileable map is 1024×1024, square. Bigger is for surfaces the camera gets close to.

## Resolution, memory and streaming

- Textures upload at up to 8000 px and 20 MB per Open Cloud call (engine limits); 8K uploads are transcoded to 4K. Rendering at 4K requires texture streaming, which is on for published experiences; weak devices receive a smaller mip automatically.
- Downsizing is normal practice, not a compromise: colour, roughness and metalness maps *"can often be dropped down by 1 or 2 times without losing any visual fidelity."* Normal maps are the ones to keep sharp.
- Built-in materials use far less memory than custom textures. Spend custom PBR where the player looks, use built-ins plus a variant elsewhere.
- One texture set shared by a kit is the difference between a place that loads and a place that stutters.

## Generated materials

`generate_material` (Studio MCP) produces a PBR material from a description. Treat the result as a starting point:

- Read back what it created and where it landed, and confirm which maps actually exist on it — a generated set missing a normal map produces exactly the flat look you are trying to escape.
- Check tiling and seams on a real surface before using it across a zone.
- Check it against the palette and the material language of the direction; generated materials arrive with their own colour opinion.
- Name it so the kit can reuse it, and record it in the asset inventory like any other asset.

Tool arguments and failure modes are in `$roblox-studio-mcp`; how a material fits the kit and the composition is in `$roblox-environment-art`.

## Checking a surface after you apply it

- Look at it in raking light, not head-on: if the surface does not change as the angle changes, the normal map is missing or flat.
- Look at it at player eye height at the distance the player will actually be. A material tuned in a zoomed-in editor view is usually far too detailed at gameplay distance.
- Look at two adjacent objects that share the material: same texel density, same wear direction, no visible tiling rhythm.
- Look at the silhouette edge against a bright background: hard black edges usually mean an alpha mode or cutout problem.
- Confirm the object still reads under the direction's lighting rather than under a brightened editor scene.

## Failures worth recognising

- Colour map only, no normal or roughness — the surface stays flat under every light.
- Stretched or non-uniformly scaled textures reading as low resolution.
- Mixed texel density across one structure.
- A distinctive detail baked into a tiling map, repeating visibly across a wall.
- Neon used as a stand-in for glow, producing a flat bright rectangle instead of a glowing material.
- Emissive treated as a light source, leaving a glowing object in an unlit room.
- Every surface unique: memory spent, cohesion lost, nothing looks related.
- Built-in material plus a colour, used as the finished look of a large visible surface.

## Sources

- Roblox creator interviews, July 2026 (Twin Atlas, Fluorlite, Ecos on SurfaceAppearance, emissive, 4K, terrain variants): https://about.roblox.com/newsroom/2026/07/roblox-studio-fidelity-creator-interviews-twin-atlas-fluorlite-maximillian-ecos
- Duvall Drive, materialize the world (three-level system, trim maps, Overlay tinting, downsizing, wet/dry variants): https://create.roblox.com/docs/resources/the-mystery-of-duvall-drive/materialize-the-world
- SurfaceAppearance reference: https://create.roblox.com/docs/reference/engine/classes/SurfaceAppearance ; material variants: https://create.roblox.com/docs/parts/materials
- Emissive masks live: https://devforum.roblox.com/t/emissive-masks-are-now-live-for-published-experiences/4357705
- 4K texture rendering and streaming: https://devforum.roblox.com/t/4k-texture-rendering/4316229
- Terrain 64 custom materials Early Access: https://devforum.roblox.com/t/early-access-program-unlocking-massive-terrain-with-up-to-64-custom-materials/4703282
- Asset upload limits (Open Cloud Assets): https://create.roblox.com/docs/cloud/guides/usage-assets
- Flat-PBR and stretched-texture critique: https://craftpbr.com/guides/roblox-texture ; https://devforum.roblox.com/t/hyper-realistic-environmental-art-showcase/2737141
