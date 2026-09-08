# Architecture (v1.0)

A studio instance is one Codex session: the lead (`AGENTS.md`) with the lanes (`.codex/agents/*.toml`) as its subagents, spawned by name with `spawn_agent` and the path of a task card. Lanes spawn their own fresh judges and parallel workers (`agents.max_depth = 2`). Several instances run in parallel as separate terminals (`scripts/run_studio.ps1 -Instances 3`); each claims a different scene from `game/PLAN.md` on the board and shares nothing else with the others but the files. The shared contract of names and formats is `docs/contract.md`.

**Board.** Task cards in `board/tasks/` (goal, input, output, acceptance, must survive), reports in `board/reports/` with the contract's markers, scene claims in `board/scenes/`, `queue.log`, and `board/STATE.md`, one page rewritten after every build. `codex queue --session lead-1 "..."` lets the owner steer a running instance; it carries a file path, never content.

**Scene cycle.** Story and design work one scene ahead. For the current scene the lead generates target frames and sheets with the session's image tool (`concept-frames` skill), accepts exemplars, spawns tiling, hero, creatures, code, effects, interface and audio as lanes with cards, assembles in Blender, publishes a numbered build with a side-by-side, spawns `studio` for integration (import, lighting matched to the render, playtest, player completion, captures), accepts the scene by evidence, and spawns `dev` for the retro. Readiness states (`source → rendered → accepted → baked → glb_verified → in_scene → in_studio → played`) live in provenance files and the scene card and reset when a piece changes.

**Blender and Roblox.** Everything that is a mesh or an animation is made in Blender, through the session's Blender MCP or bpy scripts the lane writes and keeps; the evidence is the same either way: renders from fixed cameras under fixed light, baked materials, a GLB re-imported and measured against the engine limits, `layout.json` for the assembly. Everything that behaves lives in Roblox Studio through its MCP server: gameplay, AI, quests, lighting, audio, interface.

**Gates before judges.** GLB re-import measurements, luau-lsp, Lune tests, audio gates, the story contract check, the design check and Studio import errors are checked by tools; only then a fresh subagent judges renders, captures or clips against the target. Reports are never accepted on their own.

**Self-improvement.** After each accepted scene the `dev` lane reads the scene digest (`tools/studio/run_digest.py`), session trajectories (`session_digest.py`) and the retro, fixes lanes, skills and tools, and a fresh instance audits the change; `studio/journal.md` and `studio/inventory.md` keep the history. Changes apply from the next scene.

**Keeping an instance going.** The Stop hook (`scripts/hooks/stop_continue.py`) pushes a lead session back to the board while cards or scenes remain and no `STOP` file exists; `STOP` in the checkout root halts every instance after its current step.

**Retired from v0.2.** The producer-as-dispatcher, the fifteen specialist roles, `gamemaster/` and the bounded launcher modes.
