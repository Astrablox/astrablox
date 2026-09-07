# Developing the framework

Everything the agents do is plain text in this checkout. Change a role in `.codex/agents/`, the producer contract in `AGENTS.md`, the launcher in `scripts/`, then run the checks below and commit.

## Tests

```powershell
python -B tests/test_foundation_runtime.py
python -B -m unittest scripts.player.test_player scripts.player.test_regressions
```

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

Source: `AGENTS.md`, `.codex/agents/`, `.codex/config.toml`, `.codex/hooks.json`, `scripts/`, `gamemaster/tools/`, `tests/`, `docs/`, `artifacts/`. Everything else under `gamemaster/` (concept, state, bug list, inbox, logs, reports) is runtime data and stays ignored, as do `.env` files and any personal Codex profile. Large videos are release assets, not tracked files.

## Hooks

`.codex/hooks.json` wires one Stop hook, `scripts/hooks/stop_continue.py`. It only acts inside a run started by `scripts/run.ps1`; an interactive `codex` chat never triggers it. Codex treats hooks from a fresh clone as untrusted until you accept them; the launcher passes the bypass flag only when you give it `-TrustRepositoryHooks`.
