# AstraBlox v1.0 — shared contract of the studio

This file is the single source of the names, formats and rules that every lane, tool and document of the studio must use identically. A lane file or a tool that disagrees with this contract is wrong, not the contract. Written for the people and agents who build the studio; the lanes read the parts that concern them from their own files, which quote this contract in the same words.

## 1. What the studio is

AstraBlox v1.0 is a fully autonomous game studio on Codex (GPT-6 Astra family). It builds a stylized-realistic open-world fantasy game for Roblox, scene by scene, 24/7, with no human in the loop: it designs the story and quests, generates its own concept frames, models the world, characters, creatures and effects in Blender, writes the gameplay in Luau, integrates everything in Roblox Studio, plays its own build, and improves its own lanes after every scene. The owner's voice exists once, in `game/VISION.md`; everything else the studio decides.

The bar for every artifact: it would pass in a game a strong studio ships. A concept frame that reads as generic concept art, a mesh that reads as a primitive or a scan, a UI that reads as a template, a sound that reads as random, a quest that reads as filler: each is a failure of the lane that produced it and is not accepted.

## 2. Processes and names

Long-lived Codex sessions, one per lane, each started with `codex --session-name <lane>` in the checkout root (worktree per lane where it writes code). Session names are exactly:

| Lane | Session name | Owns |
|---|---|---|
| Lead | `lead` | The scene: plan, concept frames, exemplar acceptance, assembly in Blender, builds, acceptance, dispatch to all lanes. Also builds world pieces itself when nobody else is faster. |
| World | `world` | Kit pieces, hero structures, terrain, vegetation, Blender lighting matched to the target frame; GLB export. |
| Creatures | `creatures` | Player character parts, NPC and monster models, rigs (R15 / Avatar Auto Setup), animations (retargeted or authored), accessories. |
| Effects | `vfx` | Mesh effects and flipbooks in Blender; particles, beams, camera shake, hitstop, impact frames and the client presentation code in Roblox. |
| Code | `code` | Character controller, abilities, combat, enemy AI, quest logic, save data, remotes; the luau-lsp gate and the independent code review. |
| Design | `design` | Core loop and pillars (`game/DESIGN.md`), system specs (controller, abilities, combat, enemies, progression, economy), per-scene gameplay contract (encounters, mechanics, difficulty, feel targets), tuning from playtest and completion reports. |
| Story | `story` | Lore, scene list, per-scene script, NPC roster with schedules and lines, quests, points of interest, environmental storytelling; the contract each scene imposes on the other lanes. |
| Studio | `studio` | Import into Roblox Studio, scene assembly, Roblox lighting matched to the Blender render, audio placement, playtest, computer-player completion, captures, build export. |
| UI | `ui` | HUD, menus, prompts, dialogue and quest interfaces: design, UI art, style sheet, states, motion, device layouts, and their client code. |
| Audio | `audio` | Sound effects, ambiences, music and adaptive layers from open sources and local generation; objective audio gates; the audio catalog. |
| Dev | `dev` | `studio-developer`: after each accepted scene, reads the scene's retro, digests and trajectories and fixes lane files, skills and tools; a fresh instance audits every change. |

Inside any session, subagents (depth 1) are used for exactly two things: fresh-context judges, and parallel workers on independent pieces. A subagent never owns a lane.

## 3. The bus

Sessions signal each other only with `codex queue --session <name> "<signal>"`. A signal is one line, carries no content, and always names a file:

- `TASK <id> DONE <path to report>`
- `TASK <id> BLOCKED <path to report>`
- `TASK <id> RETURNED <path to report>` (lead → lane, one round)
- `TASK <id> OPEN <path to task>` (lead → lane: a new task for you)
- `BUILD <n> READY builds/<n>/`
- `SCENE <id> ACCEPTED` / `SCENE <id> BLOCKED <path>`
- `RETRO <scene id> READY studio/scenes/<id>/retro.md` (dev)
- `WAKE` (supervisor → any idle session with open tasks)

Everything else is in files. A session that receives a signal reads the file it names before acting. The supervisor appends every signal to `board/queue.log`.

## 4. Task cards

`board/tasks/<id>.md`, id = zero-padded number. Front matter fields, exactly these names:

```
id: 042
lane: world
scene: harbour
status: open | claimed | done | blocked | returned
created: <ISO time>   claimed_by: <session>   claimed_at: <ISO>   deadline: <ISO>
depends_on: [ids]
```

Body sections, in this order: **Goal** (one paragraph, what and why for this scene); **Input** (paths: target frames, sheets, contract, existing assets); **Output** (paths and formats expected); **Acceptance** (the criteria the judge will use, same words as the lane file); **Must survive** (what the change may not break); **Notes** (assumptions the lane may make when the card is silent).

The lane that claims a card sets `status: claimed`, `claimed_by`, `claimed_at`. It finishes with `status: done` or `blocked` and a report at `board/reports/<id>.md`. The lead accepts by the artifact (render, GLB verification, test, capture), never by the report; a return is an addressed list appended to the card under **Return**, one round; what remains goes to `studio/inventory.md`.

## 5. Reports

`board/reports/<id>.md` leads with one paragraph: the state of the result and what a viewer will notice first. Then markers at the start of their lines, exactly:

- `DELIVERED:` paths of every artifact produced, one per line, with its readiness state (§6)
- `EVIDENCE:` renders, verify outputs, test results, captures that prove the state
- `ASSUMPTIONS:` decisions taken where the card was silent
- `WEAKEST:` the single weakest place of the result next to the bar, in the lane's own judgement
- `OPEN:` what could not be done and why; what another lane must provide
- `STATUS: DONE` or `STATUS: BLOCKED`

Lane-specific markers are listed in each lane file and in `AGENTS.md`'s lane table; a report missing a marker is incomplete and the lead returns it.

## 6. Readiness states of an asset

Every asset carries one state in `assets/<lane>/<name>/provenance.json` (`state` field) and in the scene card:

`source → rendered → accepted → baked → glb_verified → in_scene → in_studio → played`

A change to geometry or material resets the state to `rendered`. "Done" without a state is not a word the studio uses.

## 7. Scene card

`game/scenes/<id>/card.md`, owned by the lead, rewritten after every build:

```
# Scene <id> — <name>
Goal: <one sentence>
Target frames: <paths>
Current build: <n>  (builds/<n>/)
Top three defects: 1. … 2. … 3. …
Pieces: <name> — <state> — <owner lane>   (one line per piece)
Blocked: …
Next step: …
```

## 8. Files and their owners

```
game/VISION.md        owner's voice, once            written by owner; lead may annotate, never rewrite
game/DESIGN.md        core loop, pillars, system specs    design
game/LORE.md          lore bible                     story
game/PLAN.md          ordered scene list + status    story proposes, lead approves
game/scenes/<id>/     card.md (lead), script.md + contract.md (story), gameplay.md (design), target.png + sheets/ (lead/world)
board/STATE.md        one page: goal, latest owner instruction, current scene, top three defects, builds waiting, next step   lead
board/tasks/ reports/ queue.log
assets/<lane>/<name>/ files + provenance.json (source, licence, parameters, state, hashes, roblox asset id)
assets/library/       catalogued open assets (KayKit, Quaternius, Poly Haven, audio sources)
builds/<n>/           renders, side-by-side, Studio captures, .rbxl, CHANGES.md (what changed, where to look)
studio/journal.md     every change to the studio: date, what, why, how to verify   dev
studio/inventory.md   numbered problems and fates                                    dev
studio/scenes/<id>/retro.md   what worked and what did not in this scene             dev
tools/                blender/ (render_views, bake_pbr, export_glb, side_by_side), board/ (board.py, supervisor.py, build_publish.py), assets/, check/, studio/, audio/
.agents/skills/       concept-frames, blender-craft, narrative-witcher, ui-premium, audio-pipeline, roblox-*
.codex/agents/        one TOML per lane except lead (AGENTS.md)
```

Code lives in `game/src/{server,client,shared,tests}` with `.server.luau` / `.client.luau` / `.luau` suffixes (the analyzer needs them). Two modules are mandatory declarations: `game/src/shared/Presentation.luau` (every presentation event with its payload type; `vfx`, `ui` and `audio` require it, so a name cannot drift) and `game/src/shared/Tuning.luau` (every value the design spec names, under the design's names, so tuning never hides inside a system). The Blender assembly of a build is exported as `builds/<n>/layout.json` in the schema `tools/blender/README.md` documents (pieces with transforms in metres, Y-up, and the acceptance cameras); `studio` reproduces it. The audio lane delivers a scene's package as `assets/audio/<scene>/placement.json`.

Judge subagents that lanes spawn by name are registered in `.codex/config.toml` with a description that begins with `Judge subagent:`; they are not lanes and have no session: `luau-reviewer` (spawned by `code`), `computer-player` (spawned by `studio`).

`gamemaster/` from v0.2 is retired; `board/` and `game/` replace it. Runtime folders (`board/`, `builds/`, `assets/` except `library/`, `game/scenes/*/target*.png`) are ignored by git except their templates.

## 9. Style of the game (all lanes)

Stylized realism as Roblox's best studios ship it, anchored by the target frames the lead generates: clean large shapes with bevelled edges, readable silhouettes, few materials that respond to light, calm surfaces with wear where hands and weather put it, warm emissive light against cool dusk, mist separating planes, one visual centre per frame. Characters are Roblox R15 avatars (blocky proportions) with modelled accessories; monsters and NPCs follow the same proportion language unless the story contract says otherwise. Interface is quiet, premium and diegetic where it can be: thin strokes, restrained palette taken from the world, ornament as image assets, motion that answers actions. Text in the game is short; the world tells the story first.

## 10. Roblox and Blender constraints (engine facts)

Mesh ≤ 20,000 triangles, file ≤ 20 MB, textures above 1024 downsampled (hero at 2048 only when needed), one texture set per mesh, Principled BSDF with image textures only (bake before export), metres with origin at base centre, Y-up on export, modular pieces on a grid with matching end profiles; no custom LOD chains. Modelling in Blender happens through whatever the session has: a Blender MCP bridge, or bpy scripts run headlessly; the gates always run through `tools/blender/` (fixed-camera renders under reference light, baking, GLB export with re-import verification, `layout.json`, side-by-side), because a render that cannot be compared and a mesh that was not verified do not count. Roblox is driven through Studio MCP (`roblox-studio-mcp` skill) with leases: one exclusive Play/input/camera owner at a time.

## 11. Gates (objective before judgement)

World: `export_glb.py` verification; side-by-side with the target frame; fresh judge on renders. Creatures: rig imports, animations play in Studio, Auto Setup passed. Code: `tools/check/check_luau.py` strict, Lune unit tests, playtest scenarios, computer-player completes the route. VFX: clip from a fixed camera, judge on frames. UI: captures at phone, tablet and desktop viewports against the UI target mockup; style sheet is the only source of colour, type and spacing. Audio: `tools/audio/gate.py` (duration, loudness, clipping, silence, format) and a source with a licence in provenance. Design: `tools/design/design_check.py` (every system named in a scene's `gameplay.md` has a spec section in `game/DESIGN.md`, every encounter names its enemies, space, mechanics and feel target, every enemy has a spec); tuning changes cite a playtest or completion report. Story: `tools/story/contract_check.py` (every quest has trigger, goal, choice, consequence, reward, place; every NPC has a place, a schedule and lines; every place named exists in the scene). Build: import without errors, captures from the acceptance cameras, diff against the Blender render.

## 12. Autonomy rules (all lanes)

Never ask questions; decide, write the assumption in the report, continue. Stop only when the card's output exists or an external blocker stops you; then report BLOCKED with the exact cause. A step that fails twice the same way gets a different approach. Nothing that leaves the machine happens without `game/VISION.md` explicitly allowing it. Leaving the machine means: publishing a place, making anything public, uploading to a group or account the vision does not name, spending money. Uploading assets to the owner's own account or group named in the vision and inserting them into the open Studio place is ordinary work, not leaving the machine. No credentials in any file the studio writes. Report only what a render, a verify output, a test or a capture proves.

## 13. Models and effort

Default model for lanes: the Astra family; `model_reasoning_effort` per lane file: creative and diagnostic lanes `xhigh`, mechanical `medium`. Judges run at `high`. Effort is raised before a prompt is lengthened.
