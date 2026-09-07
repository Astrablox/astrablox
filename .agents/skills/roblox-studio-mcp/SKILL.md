---
name: roblox-studio-mcp
description: Playbook for the Roblox Studio MCP tools - list_roblox_studios and studio_id, execute_luau and its sandbox, get_console_output truncation, script_read/multi_edit/grep, search_game_tree and inspect_instance, screen_capture with camera placement, start_stop_play and input, generate_mesh, generate_material, generate_procedural_model, search_asset and insert_asset, upload_image, subagent - with the limits and traps that produce false results. Use whenever you are about to drive the owner's live Studio through these tools, and before diagnosing a tool that seems to have failed. Not a source of Luau or art craft.
---

# Driving the owner's Studio through MCP

These tools reach into a live Roblox Studio the owner has open. There is no undo queue you can rely on and no second copy of the place. Everything here is about getting real evidence out of that Studio and not corrupting somebody else's work in the process.

**Tool schemas win over this file.** Names and parameter spellings below are what the tooling exposed as of September 2026; the server ships with Studio and changes with it. Read the live schema of a tool before its first use in a session, and follow it where it differs. Lines marked `VERIFY ON FIRST RUN` were not confirmed inside this project.

**Which of these you may call is set by your lease, not by this file.** The lease is in your brief.

## Connect first

`list_roblox_studios` returns the connected Studio instances. Keep the `studio_id` and pass it to every subsequent call: since August 2026 every tool takes it, and with more than one Studio open a call without it can land in the wrong place. A Studio process being alive is not proof that the MCP bridge is connected; the tool result is.

If a call times out, the Studio side dropped it. Do not repeat the same call in a loop: inspect the state once, wait briefly, retry once, and if it still fails, report a blocker with what you observed. Retry storms lock up the owner's editor.

## Reading the place

- `search_game_tree` finds instances by name, class or path across the DataModel. This is how you learn what exists before you write anything.
- `inspect_instance` returns an instance's properties, attributes and children. Use it to confirm what you or another agent actually created, including collision, anchoring, tags and the source of an inserted asset.
- `script_read` returns the source of a script. Read whole files, not the first screen; a review or a change based on an excerpt misses what is below it.
- `script_search` / `script_grep` find code by text across the place. Use them to find every caller before changing an interface, and to find scripts nobody mentioned - including scripts that arrived inside inserted models.

Independent reads can be issued together; a read that depends on the result of another comes after it.

## Changing the place with `execute_luau`

`execute_luau` runs a Luau snippet inside Studio. It is the main way to create and modify instances in bulk.

Three execution contexts exist: the Edit-mode DataModel, and the server and client DataModels of a running Play session. The audit script in this repository is invoked with `datamodel_type = "Edit"`; confirm the parameter name and the accepted values from the live schema before your first call. Edit context is where building happens. Server and client contexts only exist while Play is running, and reaching them requires the Play lease.

What this tool is and is not:

- **It is a sandbox, not the game.** It runs with its own identity and its own module cache. Requiring a module here does not give you the instance the running game has, and state you create in it is not the state a running server sees. Build and inspect with it; test behaviour in a real Play session.
- **Batch creation.** Creating instances one call per instance is slow and produces a fragile transcript. Create a batch in one snippet - the whole set of parts for a structure, the whole tree of a GUI - with properties set before parenting, and return a short summary string.
- **Write idempotent snippets.** Assume a snippet may run twice: find or create, do not create blindly, and never destroy something you did not create. A snippet that deletes by class or by name pattern will eventually delete another owner's work.
- **Keep the returned output small.** Return a summary line or a small table, not a dump of the DataModel. The MCP result size is capped (the screenshot tool was moved to JPEG because of a 1 MB cap on tool results), and a large return can lose the part you needed.
- **Read back after writing.** The snippet returning without error means the snippet ran, not that the object is as you intended. Inspect what you made.

`script_multi_edit` applies edits to script sources; use it for code rather than rewriting scripts through `execute_luau` string assignment, and read the source back afterwards.

## Console output

`get_console_output` returns Studio's recent output. The buffer is small - about 10 KB - and when it overflows, new lines can be lost rather than old ones. Consequences for how you work:

- Read the console immediately after the action you care about, not at the end of a long sequence.
- Look for errors explicitly rather than skimming: a filtered probe that only matches your own prints hides everybody else's errors.
- Silence is not proof of a clean run when other systems are logging; note when the buffer looked truncated.

## Running the game

`start_stop_play` starts and stops a Play session. Only the agent holding the Play lease calls it. Starting Play while another agent is writing in Edit destroys their work in progress; stopping Play discards the session state, so capture the evidence you need first.

A running game caches each module the first time it is required. After editing code, stop and start Play again before testing, or you will be testing the previous version.

`user_keyboard_input` and `user_mouse_input` drive the real input pipeline; `character_navigation` moves the character to a point. Evidence from real input is the point of these tools: a state change forced through `execute_luau` proves nothing about whether a player could have caused it. Release held inputs before ending your turn, then stop Play and confirm the editor is back in Edit mode.

## Seeing what you built

`screen_capture` returns an image of the viewport, optionally with a camera position and a look-at target, encoded as JPEG because of the result-size cap. This is the only way anyone in this studio can judge how the place looks; a description of a scene is not evidence about the scene.

How to use it well:

- Place the camera deliberately: eye height where a player stands, aimed at what the frame is about. A capture from an arbitrary editor camera says nothing about what the player sees.
- Capture the same named views before and after a change, from the same positions, so two frames can be compared.
- One capture per view is enough; a second angle of the same thing adds no information for a critic.
- The tool has been documented in the context of Play mode. `VERIFY ON FIRST RUN` whether Edit-mode capture works in this Studio, and whether camera arguments behave the same in both.
- JPEG compression softens fine detail; do not conclude anything about texture sharpness from a capture alone.

## Making content

`generate_mesh` produces a textured MeshPart from a text prompt, optionally with a hint image. It takes its bounding box from a Part you select first, so the way to control scale is to create a correctly sized Part and generate into it. The triangle budget is capped by a max-triangle argument, defaulting to around ten thousand. Generation is roughly deterministic: the same prompt returns essentially the same mesh, so variety comes from different prompts, not from retrying.

Quality expectation, from the people using it: props and background objects, not hero assets. Topology is decimated, textures are the weak part. Use it where a shape that reads correctly at gameplay distance is enough, and do not stake the look of a landmark on it. Whatever it returns, look at the result in a capture before keeping it, and record in your report where the asset came from.

`generate_material` produces a material for surfaces. Same rule: inspect the result on real geometry under the scene's lighting before adopting it.

`generate_procedural_model` produces a parametric model whose attributes regenerate it - stairs, walls, railings, structures that repeat with variation. Daily generation limits apply. This is the closest thing available to a reusable component library: a generated procedural model can be tuned by attribute instead of rebuilt, and the same model can be placed many times with different parameters.

## Bringing in existing content

`search_asset` searches the Creator Store and inventory; `insert_asset` inserts by id. Rules that matter:

- **Scripts inside inserted models are untrusted.** Do not enable or run them before they have been read. A free model with a script that touches players, data stores or HTTP is a real and common attack.
- Inspect what actually arrived: scale relative to the character, orientation, pivot, materials, collision, and whether textures loaded. An asset that failed to load is not a reference and not a delivery.
- Record the asset id, its source and its permitted use in your report. Provenance that is not written down is provenance that is lost.
- Style coherence beats variety: many instances of one consistent set look built, one instance each of many different sets looks like a store catalogue.
- Loading third-party assets by id from code additionally requires the place's security setting for third-party assets; `VERIFY ON FIRST RUN` whether that is enabled in this place.

`upload_image` uploads an image and returns an asset reference usable in properties. Moderation applies and takes time, so an image that is not yet approved may not render for anyone else.

## `subagent`

The Studio MCP server exposes a `subagent` tool with explore and playtest types. The playtest agent drives a character through a scenario autonomously; it has a per-test move limit, a daily cap, and limited observability, and Roblox says a test can pass while the game is actually broken. Treat its result as a lead, not as acceptance: this studio's own playtester and computer-player roles produce the real evidence. `VERIFY ON FIRST RUN` the available subagent types and what they return.

## Failure modes worth recognising

- **Tool success is not the object.** Every write is followed by a read of what was written.
- **Timeout means Studio dropped the call**, not that the work failed halfway - inspect before assuming either.
- **A parameter you remember may not exist.** When a call is rejected, re-read the schema instead of guessing variants.
- **The place changed under you.** Another agent may have created or moved something between your read and your write; re-check before overwriting anything you did not create.
- **Partial writes.** A batch snippet that errors halfway leaves the first half in the place. Report what exists, and clean up only what you created.

## To verify on the first real run

The exact parameter names of `execute_luau` and its context values; whether `screen_capture` works in Edit mode and how camera arguments behave there; the `SetParameter` and Character Controller details flagged in `roblox-luau`; the available `subagent` types; whether third-party asset loading is enabled in this place; the current default and maximum triangle counts for `generate_mesh`; the daily limits on procedural model generation. Record the answers in the run's report so the next agent does not re-derive them.

## Sources

Studio MCP documentation: https://create.roblox.com/docs/studio/mcp · Mesh generation, screenshot tool and MCP tool additions: https://devforum.roblox.com/t/assistant-updates-mesh-generation-new-mcp-server-tools-screenshot-tool-and-more/4527258 · Built-in MCP server and playtest automation: https://devforum.roblox.com/t/assistant-updates-studio-built-in-mcp-server-and-playtest-automation/4474643 · Multi-Studio `studio_id` update: https://devforum.roblox.com/t/4820583 · Playtest agent beta: https://devforum.roblox.com/t/studio-beta-studio-assistant-mcp-playtest-agent/4566767 · Sandbox identity, module cache and console truncation observed by the community bridge maintainers: https://github.com/Chrrxs/robloxstudio-mcp and https://github.com/Chrrxs/roblox-mcp-primitives · Procedural Models: https://devforum.roblox.com/t/full-release-procedural-models-build-parametrized-3d-models-with-code-or-ai/4642542 · Generation quality reports: https://devforum.roblox.com/t/beta-cube-3d-generation-tools-and-apis-for-creators/3558947 · Third-party asset loading: https://devforum.roblox.com/t/loading-third-party-model-assets-in-experience/3939065
