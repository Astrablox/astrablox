# Studio tools

Tools for the `dev` lane and for anyone reading what a scene run did. Plain Python 3.11+, no
dependencies, `--help` on each. They read; they never touch Studio or the place.

| Tool | What it does |
|---|---|
| `check_studio.py` | Static gate for the studio: every registered lane or judge parses and has its fields, every lane in the AGENTS.md lane table has a file and returns the contract's base markers plus its extra markers, skills have frontmatter, referenced skill and tool paths exist, AGENTS.md is under the Codex 32 KiB cap, hooks parse. Exit 1 on errors. Run after any change to lanes, skills, AGENTS.md or config. |
| `run_digest.py` | Digest of a scene from `board/`: STATE, the scene card, task cards by status, per report the expected markers present and missing, STATUS and WEAKEST lines, BLOCKED/RETURNED counts, referenced evidence paths and whether they exist, heartbeats, builds, the tail of the bus. Writes `studio/scenes/<id>/digest.md`. |
| `session_digest.py` | Trajectories from Codex session JSONL (`~/.codex/sessions/`): per thread the user messages, the tool-call sequence, calls whose output looks like an error, spawned agents, compactions, tokens. `--thread <id> --raw` prints one thread with every user message (a role's brief) and every spawn argument untruncated: the full feed of a role. `--types` first if Codex changed its format. |

Records the lane keeps: `studio/journal.md` (every change to the studio: date, what, why, how to verify),
`studio/inventory.md` (numbered problems and their fates) and `studio/scenes/<id>/retro.md` per scene.
