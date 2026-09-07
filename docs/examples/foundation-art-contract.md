> Historical example (September 6, 2026): the environment acceptance contract of the two-room
> smoke test, written before the art-director DIRECTION step existed. Today the equivalent
> document is the ART DIRECTION with a style kit and acceptance views; see AGENTS.md.

# Foundation demonstration: environment acceptance contract

Status: planned polish, not visual acceptance. Applies after the first earned traversal.
Build scope: The Key Remembers; exactly the existing Cell and Shrine, each 24 x 14 x 24 studs. No enemies, extra rooms, puzzles, persistence or artificial waiting. The objective is a small convincing demonstration of the studio pipeline, not evidence that it can already make every Roblox genre.

## Direction

Stylized gothic stonework, restrained wear and clear silhouettes. Cell is a warm, intimate holding chamber; Shrine reveals a larger-looking cool ceremonial space. Repeated iron/keyhole shapes connect the pickup, lifting door and portal. Depth comes from substantial structural layers, framing and lighting, not hundreds of tiny scattered blocks.

Cell: stone piers and springing arch/rib shapes frame the existing door; a recessed or capped plinth makes the actual key readable at player height. The key must visibly have a bow, shaft and teeth. Torch fixtures should look attached to the architecture. Reserve a clear route from spawn to key to door. Use a few coherent worn details at the edges, with no competing bright focal prop.

Shrine: a truly open keyhole/arched portal, layered frame and restrained cyan recesses form the hero. Flanking architecture frames the portal; a small number of offerings and floor inlays establish scale. Keep the central ten-stud lane empty. The portal may glow, but it must retain shape and an obvious point of entry instead of becoming an opaque neon rectangle.

## Interfaces that cannot change silently

- Cell center (0,7,0), Shrine center (0,7,24), both floor tops Y=0. Door opening X=-4..4 at Z=12, height10; retain at least7.5 clear studs and no threshold lip.
- IronKey is the single DungeonKey target at (-6,3.5,-3), ItemId IronKey. Pickup remains visible and reachable without jumping. Decorative geometry is nonqueryable so server line-of-sight remains unobstructed.
- IronDoor is the single DungeonDoor BasePart at (0,5,12), DoorId CellDoor; saved scene is closed and colliding. The controller moves this target up12studs. Any visual assembly must follow that exact movement. Anchored child parts do not follow a parent Part's CFrame: do not create a static duplicate blocking or visually hiding the open passage. Declare any assembly exception to the anchored-decoration convention.
- PortalTrigger remains DungeonExit at (0,4.5,31.5), Size(7,9,3), ExitId ShrineExit; invisible, touch-enabled, noncolliding. No opaque or solid decoration closes the intended entry volume.
- One SpawnLocation, existing scripts and functional UI preserved. Existing light tags and client pulse behavior retained. No inserted scripts enabled without inspection and independent review.

## Asset and performance contract

Suitable generated meshes, generated materials, modular geometry and verified Creator Store assets are allowed; the original smoke-only primitive restriction and two-hero quota do not apply to this polish pass. Choose based on silhouette and consistency. For every generated/imported resource record its source/job/asset identity, load status, scale, collisions and any unknown geometry/texture cost. Generation gets a bounded attempt; a deliberate modular fallback is acceptable only if the actual result meets the visual criteria.

Whole Workspace remains under300 BaseParts including Terrain, with Map descendants under600. Environment owner should finish below260 parts, leaving room for atmosphere/fixes. Do not spend the budget merely to reach a count. Walkable structural collision stays simple; decorative collision/query/touch is disabled except a documented moving-door assembly.

## Acceptance images and regressions

Inspect Cell from spawn at player-eye height, key at interaction distance, doorway before/after unlock, Shrine from the doorway and portal at approach distance. Images must make the target, direction and passage readable. Record actual Client images again on final traversal; Edit beauty captures cannot substitute for player evidence.

Independent art review checks shape, proportions, coherent materials, focal hierarchy, readability and atmosphere, not just part counts. Final runtime review checks locked door, reachable key, visible opening animation, physical passage, portal win, fresh-session reset, stable client and console. Any added script is independently reviewed.

Audio/VFX/lighting are a later exclusive pass over the finished geometry. Verify actual sound asset loading and runtime evidence; never claim audibility from Sound properties alone. Keep effects subordinate to interaction readability. The final scene is not accepted until both the art and gameplay checks pass.
