# Setup

Three steps, then you talk to it. Windows only for now: Roblox Studio's MCP server and the launcher are Windows tools.

## 1. Codex CLI

```powershell
npm install -g @openai/codex
codex login          # browser login with your ChatGPT account
codex --version      # 0.153 or newer
```

Any ChatGPT subscription works. Pro has the headroom for a long build; inside `codex`, `/status` shows your plan and remaining quota.

## 2. Roblox Studio

1. Install or update Roblox Studio (the MCP server ships with Studio since spring 2026).
2. Open a place and **publish it** (File → Publish to Roblox As…). The MCP server only works on a published place.
3. Assistant panel → `…` → **Manage MCP Servers** → turn on **Enable Studio as MCP server**.
4. `%LOCALAPPDATA%\Roblox\mcp.bat` now exists. The project config already points at it; nothing to edit.

## 3. Open the studio

```powershell
git clone https://github.com/Astrablox/astrablox.git
cd astrablox
codex
```

Codex asks whether to trust the folder. Say yes: trust is what loads `.codex/config.toml` (the Studio connection and the 15 roles). Then type your game:

```
Horror escape. 3 floors underground, keycards, flickering lights, a monster that hunts you.
```

To check the connection first, ask `list the Roblox Studios you can see`. The answer is your open place with its id. Studio's Manage MCP Servers panel shows a green indicator.

## Let it run without you

```powershell
.\scripts\run.ps1 -Concept "Medieval dungeon crawler. 5 rooms, torches, a boss at the end."
```

The launcher starts the same studio with a budget (defaults: 60 minutes, 12 continuations) and a Stop hook keeps the session going until the budget runs out. Useful flags:

| Flag | Meaning |
|---|---|
| `-MaxMinutes 90 -MaxContinues 20` | bigger budget |
| `-Resume` | continue the last run |
| `-ClearStop` | start a new run after `stop.ps1` was used |
| `-Headless` | no interactive terminal, JSON events on stdout |
| `-TrustRepositoryHooks` | accept the repository's Stop hook without the trust prompt (read `.codex/hooks.json` first) |

`.\scripts\stop.ps1` ends it: no further continuations. Python 3.11+ is required for the hook.

## If Studio does not connect

- **Start Codex before you open Studio.** Studio attaches to the MCP proxy only if the proxy is already running. Close Studio, start `codex`, reopen the place.
- **The place must be published.** Local unsaved baseplates do not expose MCP.
- **One Studio window with MCP enabled at a time.** Several open places make the target ambiguous.
- **`mcp.bat` missing** means the toggle in step 2 is off or Studio is outdated.
- **Login fails with "Authorization code may not be used from this device"**: your network changes public IP between requests. Switch to another network and log in again.

## Developing the framework

Tests, optional capture dependencies and what is tracked: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
