# Studio tools

Tools for the `studio-developer` role and for anyone reading what a run did. Plain Python 3.11+, no
dependencies, `--help` on each. They read; they never touch Studio or the place.

| Tool | What it does |
|---|---|
| `check_studio.py` | Static gate for the studio: every registered role parses and has its fields, every role in the AGENTS.md table is registered and returns the markers the table lists, skills have frontmatter, referenced skill and tool paths exist, AGENTS.md is under the Codex 32 KiB cap, hooks parse. Exit 1 on errors. Run after any change to roles, skills, AGENTS.md or config. |
| `run_digest.py` | Digest of a run cycle from `gamemaster/`: run status, state, buglist, and per report the role, the expected markers present and missing, verdicts, BLOCKED/UNOBSERVED counts, referenced evidence paths and whether they exist, media under the cycle. Writes `<cycle>/digest.md`. |
| `session_digest.py` | Trajectories from Codex session JSONL (`~/.codex/sessions/`): per thread the user messages, the tool-call sequence, calls whose output looks like an error, spawned agents, compactions, tokens. `--thread <id> --raw` prints one thread with every user message (a role's brief) and every spawn argument untruncated: the full feed of a role. `--types` first if Codex changed its format. |

Records the role keeps: `docs/journal.md` (every change to the studio: date, what, why, how to verify) and
`docs/inventory.md` (numbered problems and their fates).
