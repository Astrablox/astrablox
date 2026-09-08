# Developing the framework

Everything the agents do is plain text in this checkout. Change a lane in `.codex/agents/`, the lead's contract in `AGENTS.md`, the shared contract in `docs/contract.md`, the tools in `tools/`, then run the checks below and commit.

## Tests

```powershell
python -B tools/studio/check_studio.py
python -B tests/test_foundation_runtime.py
python -B tests/test_studio_tools.py
python -B tests/test_board_tools.py
python -B tests/test_audio_tools.py
python -B tests/test_story_tools.py
python -B tests/test_blender_tools.py        # needs BLENDER=<binary>, skipped otherwise
python -B -m unittest scripts.player.test_player scripts.player.test_regressions
```

`check_studio.py` is the static gate for lanes, registrations, markers, skills and references; it must pass before a commit that touches `AGENTS.md`, `.codex/` or `.agents/`. A change to the studio also gets an entry in `studio/journal.md` (and, when it closes or opens a problem, `studio/inventory.md`). Prefer letting the `dev` lane make the change (`codex queue --session dev "..."` while the studio runs, or a `dev` card on the board): it reads the run evidence first and a fresh instance audits the result.

The launcher suite runs against a fake Codex in isolated temporary workspaces. The player suite mocks host input and capture and needs Pillow and pywin32. Neither opens Studio or sends real input. Set `PYTHONDONTWRITEBYTECODE=1` (or use `-B`) to keep bytecode caches out of the tree.

## Player harness dependencies

The player harness (`scripts/player/`, manual in [scripts/player/README.md](../scripts/player/README.md)) captures the Studio window and sends bounded input. Windows capture needs Pillow and pywin32; recording needs `ffmpeg` and `ffprobe` on PATH.

The optional faster Windows Graphics Capture recorder lives in an isolated environment that is never committed:

```powershell
python -m venv .venv-wgc
.venv-wgc/Scripts/python -m pip install --only-binary=:all: windows-capture==2.0.1 numpy==2.2.3 av==18.0.0 pillow pywin32
.venv-wgc/Scripts/python -m unittest scripts.player.test_fast_record -v
```

## What is tracked

Source: `AGENTS.md`, `docs/`, `.codex/agents/`, `.codex/config.toml`, `.codex/hooks.json`, `.agents/skills/`, `scripts/`, `tools/`, `tests/`, `game/` templates and `VISION.md`, `board/README.md` and `STATE.md` template, `assets/library/`, `artifacts/`. Runtime data (`board/tasks`, `reports`, `heartbeats`, logs, `builds/`, generated assets, target frames, `STOP`) is ignored, as are tool binaries and `.env` files.

## Hooks

`.codex/hooks.json` wires one Stop hook, `scripts/hooks/stop_continue.py`. It acts only in a session started with `ASTRA_SESSION=<lane>` (which `scripts/run_studio.*` sets): while the board has work for that lane and no `STOP` file exists, it pushes the session back to the board, at most a few times without a new heartbeat; the supervisor's `WAKE` covers the rest. An interactive `codex` chat without the variable never triggers it. Codex treats hooks from a fresh clone as untrusted until you accept them.
