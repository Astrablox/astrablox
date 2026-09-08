---
name: blender-craft
description: Craft reference for building stylized-realistic game assets in headless Blender for Roblox - shape language and silhouette, bevels and normals, modular kits on a grid, few named materials built from gradients and masks rather than noise, baking to images and checking the bakes, vegetation, real-world scale, light in the working scene, generated blockins as proportion guides, and the export mistakes that arrive silently in Studio. Use when modelling, texturing, baking, lighting a Blender scene or exporting a GLB for Roblox, and when a render reads as blocky, flat, noisy, plasticky or scanned. Characters, rigs, skinning, accessories and animation are in references/characters-and-rigs.md; bpy code patterns are in references/bpy-recipes.md. Not for placing, lighting or scripting inside Roblox (see roblox-environment-art, roblox-materials, roblox-assets).
---

# Stylized realism in Blender, for assets that ship in Roblox

Two results fail this look, and they fail it for opposite reasons. A primitive with a material on it - a cylinder called a post, a cube called a crate - reads as a placeholder at every distance, because it has no edges for light to live on and no construction to read. A generated or scanned mesh dropped in as it came reads as a smear: soft edges, wobbling silhouette, texture that carries lighting baked from somewhere else. The look this studio ships sits between them: large clean shapes with bevelled edges, silhouettes that read as black shapes, few materials that respond to light, calm surfaces with wear only where hands and weather put it.

Everything below is how that is actually made in Blender, and what breaks between Blender and Studio.

## Render discipline

Modelling goes through whatever your session has: a Blender MCP bridge into a running Blender, or bpy scripts run headlessly (`blender -b [scene.blend] --python script.py -- args`). Either way the render is the only thing that tells you what happened: a tool call that returned and a script that exited zero have proved nothing. These all "succeed": an empty camera, an object inside another object, a black frame, a bevel that shredded a corner, a bake that wrote a black image, a modifier that never got applied. Look at every render at full size before deciding the next step.

Every asset ends as a `.blend` that can be reopened and, when it was built by script, the script kept beside it. Scenes are `.blend` files; renders are images from cameras that do not move between stages, under light that does not change between stages. When the cameras or the light move, two stages cannot be compared and the work stops being measurable.

## Shape language

A piece is finished when it is recognisable as a black silhouette, with no material and no texture. Render the blockout flat and look: if the answer is "a rectangle", it is still a rectangle in the game, whatever gets applied to it later.

Silhouette is built from three things: the large proportion (how tall against how wide, and against a human body), the secondary break in the outline (an overhang, a taper, a bracket, a broken corner - the thing that stops the shape being a box), and the negative space the outline encloses. Detail that lives inside the outline does not help recognition and costs triangles.

Style is not invented per piece. It comes from the target frame and the scene's sheets: the proportions, the way things are jointed, what is heavy and what is slender, what is old and what is new. Two pieces of one kit must read as built by the same hands - same wall thickness language, same chamfer size, same joint logic.

## Edges and normals

Real objects have no zero-radius edges. Light lives on bevels, and bevels are the single largest difference between "modelled" and "boxed". Every hard edge that catches light gets a bevel modifier (a few segments, a width in metres that matches the object's scale) or a chamfer built into the mesh; edges nobody sees are skipped to keep the triangle budget for silhouette.

Two mechanics matter in Blender 4.x. Bevel width is in object space, so unapplied scale gives uneven bevels: apply scale first, always. Shading is smooth-by-angle: in 4.1 and later the old mesh auto-smooth angle is gone, and the equivalent is the Smooth by Angle modifier or `bpy.ops.object.shade_auto_smooth(angle=...)`; a weighted-normal modifier after the bevel keeps flat faces flat while the bevel carries the highlight. Without that, bevelled hard-surface pieces look inflated.

## Modular kits on a grid

A world is built from a small set of pieces reused with variation, not from unique models. Pieces snap when they share a grid step, matching end profiles at the seams, and pivots at the base centre of each piece. Variation comes from rotation, mirroring, combination and wear, not from new geometry.

A kit is proven by assembling the target frame from its pieces and rendering that assembly from the frame's camera. Every gap, every overlap and every seam that reads as a repeat is a defect of the kit, not of the placement. A kit that only fits in the scene you assembled by hand is not a kit.

## Where the triangles go

Roblox refuses a mesh above 20,000 triangles and a file above 20 MB, and it builds its own level of detail, so custom LOD chains are wasted work. Inside that budget the rule is: triangles buy silhouette and the surfaces the player passes close to. Interior faces of closed objects, faces pressed against the ground, and geometry smaller than a pixel at gameplay distance buy nothing.

## Materials: few, named, and built from gradients

Name materials once by what they are and reuse them across the kit; one texture set per mesh, because Roblox builds one SurfaceAppearance per mesh.

Colour comes from large soft gradients and from masks that follow the form - ambient occlusion in the creases, curvature (the Geometry node's Pointiness through a colour ramp) on the exposed edges, height or object coordinates for the transition from wet to dry, from clean to weathered. Wear goes where hands and weather put it: the top of a rail, the corner of a step, the waterline. High-frequency noise stretched over a box reads as noise at every distance and is the second most common reason a surface looks cheap.

Roughness carries most of the realism: worn timber is rougher on top than on its sides, wet stone at the waterline is darker and glossier, metal is rare and only where metal is. Emissive belongs to the things that are lights (lantern glass, windows, runes) and it is what makes a dusk scene light itself. Water is a flat plane with its own material and mild normal variation, never displaced geometry. `$roblox-materials` covers what these maps become on the Roblox side.

## Baking, and how bakes fail

Only a Principled BSDF reading image textures survives GLB export. Procedural node trees, shader math and layered shaders vanish silently and leave a flat grey material in Studio, so every material is baked to images (colour, roughness, metallic, normal in tangent space, ambient occlusion) and the material is rewired to read those images. your bake script (blender-craft: bake colour, roughness, metallic, normal and AO to images and rewire the material) does this, run through headless Blender (`blender -b`); its docstring carries the flags and the `layout.json` schema in docs/contract.md §8 the order.

Baking needs a UV layout that exists and does not overlap, with margin between islands - marked seams and unwrap for pieces the player inspects, Smart UV Project for the rest. After every bake, open the images: a black map, a magenta map or a map with no variation means the bake failed, and the failure is invisible until it reaches Studio. Then render again with the baked materials and compare to the pre-bake render; the two must match, or the bake lost something.

Two Roblox facts change what you bake: normal maps must be OpenGL tangent space, and roughness and metalness are read as separate greyscale images (a packed ORM texture is not read). Textures above 1024 are downsampled on import, so bake kit pieces at 1024 and reserve 2048 for a hero surface that needs it.

## Vegetation

Canopies are a few large intersecting leaf cards or simple lumpy volumes with one foliage material and alpha where sky must show through; never thousands of modelled leaves, never a sphere with a leaf texture on it. Trunks are simple, branches exist only where they carry canopy. Scattered small elements - leaves on the ground and on the water, grass tufts - are cards distributed by geometry nodes or by a scripted distribution with the same material, placed in clusters rather than at even intervals. Wind and grass on the Roblox side belong to `$roblox-environment-art`.

## Scale is a deliverable

Author in metres. One Roblox stud is 0.28 m, and the importer scales on import, so a door is about two metres, a rail sits at hand height, a step is a step. Keep a stand-in of the player's height in the working scene (the R15 avatar is roughly five and three quarter to six and a half studs tall) so every render answers "how big is this", and keep the stand-in out of the exported file. A piece whose size can only be guessed from the render is unfinished, because the builder who places it will guess wrong.

## Generated meshes and library assets are guides

An image-to-3D blockin (`tools/assets/gen3d.py`) or a catalogued library piece is useful for one thing: proportion and silhouette reference. Import it, match its dimensions and its outline, build clean geometry over it, delete it. Its soft edges, its dense triangulation and its baked-in lighting are exactly the look this studio rejects, so it is never a deliverable in that state. A library piece becomes a deliverable only after it has been rebuilt into the frame's language - proportions, bevels, materials, budget - and its source and licence are recorded in provenance. `$roblox-assets` covers sourcing and provenance.

## Light in the working scene

The working scene carries the light of the target frame: key direction and colour, sky, and the mist that separates the planes of depth. It is saved with the scene so every stage is judged under the same light, and it is the target the Roblox side matches later - which is why the values (sun elevation and rotation, sun colour and strength, sky and fog settings, exposure and view transform) are written down beside the renders rather than living only inside the `.blend`.

Light does not repair geometry. A piece that only reads because the render is dark reads as nothing in the game; fix the shape.

## Export, and the mistakes that arrive silently

Before export: apply scale and rotation, zero the location so the piece sits at its own origin with that origin at its base centre, apply modifiers, recalculate normals outside (flipped faces render black in Studio), merge by distance after boolean and array work, delete interior faces of closed objects, and remove loose vertices and degenerate faces (the importer drops them and the mesh changes shape). Do not triangulate by hand; the exporter does it. Export Y-up with materials and packed textures.

your export-and-verify script (blender-craft) writes the file and then re-imports it in a clean process and prints, per mesh, triangles, materials, images and their sizes, and dimensions in metres, refusing anything over the engine limits. Only a GLB that passed that script is a deliverable, and the printout is the evidence, not a sentence about it.

Two more traps: GLB compression extensions (Draco, meshopt quantization, WebP or KTX2 textures) make a file Roblox will not import, so they stay off; and Roblox merges vertices on import, which can soften split normals on hard-surface pieces - check the re-imported result rather than assuming the export is what arrives.

## Characters

Bodies, rigs, skinning, accessories, clothing textures and animation have their own rules and their own Roblox constraints: `references/characters-and-rigs.md`.

## Code patterns

Working bpy snippets for the operations above - bevel and weighted normals, applying transforms, UV and bake preparation, curvature and AO masks, leaf-card clusters and scatter, camera reconstruction from a reference image, cleanup before export, checking a baked image, measuring triangles and dimensions: `references/bpy-recipes.md`.

## Failures, in the words of people who see them

"Blocky" means no bevels and no secondary shapes in the outline. "Flat" means one value across a large surface: no gradient, no roughness variation, no ambient occlusion in the creases. "Noisy" means a tiling texture doing the work that surface design should do. "Plasticky" means uniform roughness and no wear. "Obviously generated" means smeared texture, soft edges and a silhouette that wobbles. "Toy-like" means everything is the same size and nothing gives scale. Each one names a mechanism, and each mechanism has a fix above.

## Sources

Roblox mesh and texture specifications (20,000 triangle limit, watertight geometry, four influences per vertex, OpenGL tangent-space normals, separate roughness and metalness, one animation per file): https://create.roblox.com/docs/art/modeling/specifications and https://create.roblox.com/docs/art/modeling/texture-specifications - 3D importer formats and settings: https://create.roblox.com/docs/studio/3d-importer - Blender 4.1 shading change (auto-smooth replaced by the Smooth by Angle modifier): https://developer.blender.org/docs/release_notes/4.1/ - glTF compression extensions (Draco, meshopt quantization, KTX2/WebP) are not among the features the Roblox importer lists, and files carrying them have failed to import for practitioners: https://create.roblox.com/docs/art/modeling/specifications; treat this as VERIFY ON FIRST RUN and record what this account's importer actually accepted.
