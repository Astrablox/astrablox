# v0.2.1 — The studio works on itself

Date: 2026-09-08.

v0.2.0 gave every role its craft. v0.2.1 adds the role that keeps the roles honest, and the tools that let anyone see what a run actually did.

- `studio-developer`: the architect of the agents. When a role, skill, tool, brief or the producer contract produces a weak result, or the owner brings feedback about how an agent worked, the producer hands the task to this role instead of patching prompts itself. It reads the run from its digests and session trajectories, builds the full inventory of problems, fixes on the level where each lives (tool, input, order of work, prompt) and rewrites files whole. A second, fresh instance audits every change with the same criteria and returns ACCEPT or RETURN before the change is accepted. The role carries the studio's whole practice of agent design: how a model reads a prompt, what turns into something else in it, how criteria and checks are written, when a new agent is justified.
- Mode `IMPROVE` in the launcher and the producer contract; studio feedback as an inbox class; the route producer → FIX → fresh AUDIT → one return.
- `tools/studio/`: `check_studio.py` (static gate: roles, registrations, markers, skills, references, the AGENTS.md cap), `run_digest.py` (a cycle's reports against the markers the producer expects, verdicts, missing evidence), `session_digest.py` (Codex session JSONL as readable trajectories: tool sequences, errors, spawned roles).
- `docs/journal.md` and `docs/inventory.md`: every change to the studio with its reason and how to verify it; every known problem with its fate.
<<<<<<< HEAD

Static gate, launcher fixtures and studio-tool fixtures pass. The first IMPROVE run is still to be made; nothing here claims a visual result yet.
=======
- Asset harness from the same week: `tools/assets/` (Creator Store search with triangle counts and script flags, CC0 PBR textures and skyboxes, concept image → mesh through Tripo → optimise → Open Cloud upload → Studio insert, batch kit upload and manifest, headless Blender conversion), `assets-library/` (1290 catalogued CC0 assets from KayKit and Quaternius with thumbnails), `tools/check/` (luau-lsp gate with Roblox types), a vendored API reference; skills and four roles point to them; builders and the lighting director now work toward concept frames of each acceptance view.

Static gate, launcher fixtures and studio-tool fixtures pass. Live API calls of the asset tools and the first IMPROVE run are still to be made; nothing here claims a visual result yet.
>>>>>>> harness-local

# v0.2.0 — Craft, direction and set pieces

Date: 2026-09-08.

The biggest step the studio has taken since the framework baseline. v0.1 proved the pipeline: leases, parallel builders, independent review, a player agent that earns its completion. v0.2.0 gives that pipeline a studio's craft and points it at AAA-scale fantasy work.

- Every specialist profile rewritten around its craft: what an environment artist, a lighting director, an effects artist, a sound designer, a level designer and a code reviewer actually do, in their own terms, with criteria that describe the finished result.
- Seven repository skills in `.agents/skills/` that roles load on demand: environment art, materials and PBR, lighting and atmosphere (with an audio reference), VFX and game feel, Luau and the current engine API, the Studio MCP playbook, and asset sourcing. Knowledge lives once, next to the role that acts on it.
- Art direction as a step: before finish work, the art director chooses a direction, builds a verified style kit of real assets in the place, and names the acceptance views. A fresh art director instance later reviews from captures only.
- One hand per zone: `world-builder` now carries a zone from blockout through rebuild, architectural detail and set dressing. `interior-designer`, `detail-architect` and `set-dresser` fold into it; the roster is 15 roles.
- Effects owned end to end: `vfx-designer` builds a cue from anticipation to dissipate, including camera work and the client presentation code, and can direct a full sequence with camera choreography.
- Set pieces as a task type: one directed moment, delivered as a recorded clip from the player's camera and judged as a clip.
- Producer contract updated for the current generation of models: a definition of done for a build, explicit delegation and parallelism rules, an order of work that rebuilds the blockout to the direction instead of decorating it, and the vertical slice as the fallback when the budget is short.
- Studio audit reports what the world is made of (mesh parts, surface appearances, material variants, emissive masks, procedural models, leftover blockout) and the current lighting properties; counts are inventory, quality is judged from captures.
- Role registrations describe when to call each specialist; the historical two-room example is marked as the smoke test it was.

Profile, registration and marker checks passed; launcher fixtures run as before. The first build on this version is still to be run, so its visual results are not yet claimed here.

# v0.1.1 — Visual direction and review

Date: 2026-09-08.

- For substantial visual work, the architect compares feasible directions and defines silhouette, setting, depth, materials and player-eye acceptance views.
- Small visual fixes use a focused brief without requiring a full art contract.
- Art reviews report each visual target as achieved, missed or unobserved. Animation and effects require motion evidence.
- Presentation planning coordinates lighting, VFX, animation and scripting with explicit ownership, triggers and cleanup responsibilities.
- Narrative briefs connect the purpose of a place or event to its visual direction.

This release updates the producer instructions and seven of the existing 18 specialist profiles. Setup, launcher and player tools remain compatible.

Profile and registration checks passed. Planning trials covered local fixes, environment direction and event coordination; one architectural deliverable remained incomplete at its deadline. Runtime checks recorded 17/18 launcher tests and 26/27 player tests passing on the first run, with a launcher timeout and an encoder cadence failure; these tools are unchanged from v0.1.0. Visual results still need an in-game pilot.

# v0.1.0 — framework baseline

Date: 2026-09-07.

- Standalone editable AstraBlox source with a general owner-concept contract and 18 specialist profiles.
- Bounded PowerShell launcher, synchronous Stop continuation hook, relative Studio MCP wrapper and read-only Studio audit.
- Optional local player input/capture helpers and isolated regression fixtures.
- Dated foundation escape example: verified local RBXL, images, provenance and honest acceptance limits. Large recordings are separate optional release assets.
- README and setup now identify the exact files to improve and normal Git source-release steps.

This is a framework baseline, not proof of arbitrary genres or a new showcase result. Historical known-route playback does not establish blind discovery, reset/death, multiplayer/mobile, adversarial remotes or cross-account asset portability. No Roblox publication or ordinary-player join is claimed.

Validation commands are documented in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). The release tag identifies the reviewed source commit; [artifacts/README.md](artifacts/README.md) identifies the separate game build.

Baseline checks on 2026-09-07: 18 isolated launcher/Stop tests, 27 mocked player regressions and 10 recorder fixtures passed. All 19 TOML and two JSON files parsed; profile, hook and local Markdown paths resolved. The retained RBXL hash matched its verification record. These file-side checks did not launch Studio or repeat the historical game acceptance.
