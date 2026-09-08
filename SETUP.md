# Setup

One machine runs the whole studio: Windows with a GPU, Roblox Studio, Blender and Codex. Linux/macOS can run every lane except `studio` (Roblox Studio is Windows/macOS only; the MCP server ships with Studio).

## 1. Codex CLI

```powershell
npm install -g @openai/codex
codex login
codex --version      # 0.153 or newer; codex queue (the bus between lanes) needs 0.149+
```

## 2. Blender 4.x

Install from blender.org. Lanes model through the Blender MCP your Codex session has, or through bpy scripts they write; Blender must be on PATH or reachable by the MCP.

## 3. Roblox Studio

1. Install or update Roblox Studio.
2. Open a place and publish it (File → Publish to Roblox As…). MCP only works on a published place.
3. Assistant panel → `…` → Manage MCP Servers → Enable Studio as MCP server. `%LOCALAPPDATA%\Roblox\mcp.bat` now exists; `.codex/config.toml` already points at it.

## 4. Python 3.11+

`python --version`. Optional: `pip install pillow numpy trimesh pygltflib` for thumbnails and mesh inspection; `npm i -g @gltf-transform/cli` for mesh optimisation. The luau gate installs itself: `tools/check/install.ps1`.

## 5. Keys (optional)

Target frames, sheets and mockups are generated with the image tool of the Codex session itself; `OPENAI_API_KEY` is needed only if your session has none. `TRIPO_API_KEY` enables image-to-3D form guides; `ROBLOX_API_KEY` + `ROBLOX_CREATOR_USER_ID` or `ROBLOX_CREATOR_GROUP_ID` enable Open Cloud uploads when the import path needs them. Set keys in the environment of the terminal that starts the studio; never write them into files in the checkout.

## 6. The vision

Edit `game/VISION.md`. It is the only place the owner speaks: the game, the audience, the bar, what it must never do, and what may leave the machine (publishing, uploads, spending). Everything else the studio decides.

## 7. Start

```powershell
git clone https://github.com/Astrablox/astrablox.git
cd astrablox
.\scripts\run_studio.ps1
```

One window opens per instance (`codex --session-name lead-<n>`): the lead with the lanes as its subagents. `-Instances 3` opens three, each claiming a different scene from `game/PLAN.md`. Say yes to trusting the folder in each: trust loads `.codex/config.toml`. The lead starts the first scene. Watch `board/STATE.md`, `game/scenes/<id>/card.md` and `builds/<n>/`.

Talk to an instance while it runs: `codex queue --session lead-1 "Latest owner instruction: ..."`. Stop everything: `.\scripts\run_studio.ps1 -Stop` (writes `STOP`; every instance halts after its current step).

## If Studio does not connect

- Start Codex before you open Studio: Studio attaches to the MCP proxy only if it is already running.
- The place must be published.
- One Studio window with MCP enabled at a time.
- `list the Roblox Studios you can see` in the instance answers with the open place and its id.
