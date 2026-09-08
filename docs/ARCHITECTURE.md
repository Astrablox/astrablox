# Architecture (v1.0)

The studio is a set of long-lived Codex sessions, one per lane, in one checkout. The lead (`AGENTS.md`) owns the scene being built; the lanes (`.codex/agents/*.toml`) own their craft. The shared contract of names and formats is `docs/contract.md`.

**Bus.** Sessions signal each other with `codex queue --session <lane> "<signal>"` through `tools/board/board.py signal`. A signal is one line that names a file; the content is in the file. `tools/board/supervisor.py` wakes idle lanes with open tasks, reopens claimed tasks whose owner stopped heartbeating, and stops everyone on `STOP`.

**Board.** Task cards in `board/tasks/` (goal, input, output, acceptance, must survive), reports in `board/reports/` with the contract's markers, heartbeats, `queue.log`, and `board/STATE.md`, one page rewritten after every build.

**Scene cycle.** Story and design work one scene ahead. For the current scene the lead generates target frames and sheets (`concept-frames` skill), accepts exemplars, dispatches tiling, hero, creatures, code, effects, interface and audio as cards, assembles in Blender, publishes a numbered build with a side-by-side, dispatches integration to `studio` (import, lighting matched to the render, playtest, player completion, captures), accepts the scene by evidence, and signals `dev` for the retro. Readiness states (`source → rendered → accepted → baked → glb_verified → in_scene → in_studio → played`) live in provenance files and the scene card and reset when a piece changes.

**Blender and Roblox.** Everything that is a mesh or an animation is made in headless Blender through `tools/blender/` (fixed-camera renders, baking, GLB export with re-import verification, layout export). Everything that behaves lives in Roblox Studio through its MCP server: gameplay, AI, quests, lighting, audio, interface. `layout.json` from Blender is the placement `studio` reproduces.

**Gates before judges.** GLB verification, luau-lsp, Lune tests, audio gates, the story contract check and Studio import errors are checked by tools; only then a fresh subagent judges renders, captures or clips against the target. Reports are never accepted on their own.

**Self-improvement.** After each accepted scene the `dev` lane reads the scene digest (`tools/studio/run_digest.py`), session trajectories (`session_digest.py`) and the retro, fixes lanes, skills and tools, and a fresh instance audits the change; `studio/journal.md` and `studio/inventory.md` keep the history. Changes apply from the next scene.

**Retired from v0.2.** The producer-as-dispatcher, the fifteen specialist roles as subagents, `gamemaster/` and the bounded launcher modes. Roles became lanes; `board/` and `game/` replaced `gamemaster/`; the Stop hook remains as the continuation mechanism inside a session.
