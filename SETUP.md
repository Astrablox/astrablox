# Setup

One machine runs the whole studio: Windows with a GPU, Roblox Studio, Blender and Codex. Linux/macOS can run every lane except `studio` (Roblox Studio is Windows/macOS only; the MCP server ships with Studio).

## 1. Codex CLI

```powershell
npm install -g @openai/codex
codex login
codex --version      # 0.153 or newer; codex queue (the bus between lanes) needs 0.149+
```

## 2. Blender 4.x

Install from blender.org. `python tools/blender/blender.py` finds it on PATH or in the standard install folder; otherwise set `BLENDER=<path to blender.exe>`. Check: `python tools/blender/blender.py --help`.

## 3. Roblox Studio

1. Install or update Roblox Studio.
2. Open a place and publish it (File → Publish to Roblox As…). MCP only works on a published place.
3. Assistant panel → `…` → Manage MCP Servers → Enable Studio as MCP server. `%LOCALAPPDATA%\Roblox\mcp.bat` now exists; `.codex/config.toml` already points at it.

## 4. Python 3.11+

`python --version`. Optional: `pip install pillow numpy trimesh pygltflib` for thumbnails and mesh inspection; `npm i -g @gltf-transform/cli` for mesh optimisation. The luau gate installs itself: `tools/check/install.ps1`.

## 5. Keys (optional, but the studio cannot generate target frames without the first one)

Set in the environment of the terminal that starts the studio: `OPENAI_API_KEY` (concept frames), `TRIPO_API_KEY` (image-to-3D form guides), `ROBLOX_API_KEY` + `ROBLOX_CREATOR_USER_ID` or `ROBLOX_CREATOR_GROUP_ID` (Open Cloud uploads). Never write keys into files in the checkout.

## 6. The vision

Edit `game/VISION.md`. It is the only place the owner speaks: the game, the audience, the bar, what it must never do, and what may leave the machine (publishing, uploads, spending). Everything else the studio decides.

## 7. Start

```powershell
git clone https://github.com/Astrablox/astrablox.git
cd astrablox
.\scripts\run_studio.ps1
```

One terminal per lane opens (`codex --session-name <lane>`), plus the supervisor. Say yes to trusting the folder in each: trust loads `.codex/config.toml`. The lead starts the first scene. Watch `board/STATE.md`, `game/scenes/<id>/card.md` and `builds/<n>/`.

Talk to the lead while it runs: `codex queue --session lead "Latest owner instruction: ..."`. Stop everything: `.\scripts\run_studio.ps1 -Stop` (writes `STOP`; every lane finishes its card and halts). A subset: `.\scripts\run_studio.ps1 -Lanes lead,world,story`.

## If Studio does not connect

- Start Codex before you open Studio: Studio attaches to the MCP proxy only if it is already running.
- The place must be published.
- One Studio window with MCP enabled at a time.
- `list the Roblox Studios you can see` in the `studio` session answers with the open place and its id.
