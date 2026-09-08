# Studio journal

One entry per change to the studio itself (producer contract, roles, skills, tools, launcher): date · what (files and substance) · why (problem numbers from `docs/inventory.md`) · how to verify (which run or artifact shows the difference). Rollbacks get their own entry: "tried X, it did not work because Y". The `studio-developer` role reads a role's history here before touching it and appends after every change. Newest first.

## 2026-09-08 · studio-developer role and the reporting tools (v0.2.1)

- What: `.codex/agents/studio-developer.toml` (new role, two modes FIX and AUDIT, registered in `.codex/config.toml`); `tools/studio/` (`check_studio.py` static gate, `run_digest.py` cycle digest, `session_digest.py` trajectory digest); AGENTS.md: mode IMPROVE, the Studio improvement route, studio feedback as an inbox class, the role's table row; `scripts/run.ps1` and the Stop hook accept `IMPROVE`; `tests/test_studio_tools.py`; this journal and `docs/inventory.md`.
- Why: I-1, I-2, I-3.
- Audit: a fresh instance returned 13 findings (session digest truncated the brief a role received; the role told to ask questions it has no channel for; the auditor could not see FATES/STATUS or deletions; a self-questioning criterion; a dead skill check in the gate; merged markers for two-mode roles; the route accepted after one return without recording the residue; live network tools inside the role's boundary; the fix ladder outside the algorithm; no ceiling per audit finding; three dangling objects; an unconditional digest step on a checkout with no run; an unfixed numbering scheme). All closed in the same pass: `--thread --raw` in `session_digest.py`, `OPEN:` instead of questions, AUDIT receives diff + FATES/STATUS, criterion removed, `$skill` check, label-keyed table rows, residue to inventory, dry-run boundary, ladder in step 5, ceiling, objects removed, no-run clause, numbering in the inventory header.
- How to verify: `python -B tests/test_studio_tools.py` and `python -B tests/test_foundation_runtime.py` pass; on the next run with any weak role report, `.\scripts\run.ps1 -Mode IMPROVE -Objective "<owner's words>"` produces a FIX report with every marker, an AUDIT verdict from a second instance, and a new entry here. Status: hypothesis until that run.

## 2026-09-08 · asset harness, code gate, CC0 library (uncommitted work of the night of 2026-09-07)

- What: `tools/assets/` (Creator Store search, CC0 PBR textures and skyboxes, concept image → Tripo mesh → optimise → Open Cloud upload → Studio insert; batch kit upload and manifest; headless Blender conversion; catalog builder), `assets-library/` (1290 CC0 assets, 22 packs, thumbnails, triangle counts), `tools/check/` (luau-lsp gate with Roblox types), `tools/reference/roblox-dev-skill/` (vendored API reference); skills `roblox-assets`, `roblox-luau`, `roblox-vfx`, `audio.md`; roles `art-director`, `world-builder`, `lighting-director`, `ui-designer` (concept frames as the target of a capture; library pointers); AGENTS.md Assets paragraph.
- Why: H-1 … H-6 (see inventory).
- How to verify: with `ROBLOX_API_KEY`, `TRIPO_API_KEY`, `OPENAI_API_KEY` set, `tools/assets/pipeline.py` on one prop ends with a Roblox asset id and `insert.luau` loads it; `upload.py --batch` on the dungeon kit; the storm dragon set piece from the owner's concept. Status: tools verified locally on real files; live API calls not yet run; hypothesis.

## 2026-09-08 · v0.2.0: every role rewritten around its craft

- What: AGENTS.md rewritten as the producer's contract (bar, definition of done, order of work that rebuilds the blockout to the direction, set-piece route, leases, briefs, role registry with markers); 15 roles rewritten (`interior-designer`, `detail-architect`, `set-dresser` folded into `world-builder`); seven skills under `.agents/skills/`; `RELEASE_NOTES.md`.
- Why: P-1 … P-20 (the diagnosis of the box-room builds: primitives as the norm, no craft in the prompts, negative bars, no owner for assets, decorate-the-blockout order).
- How to verify: the first build on v0.2.0 against the concept `CONCEPT-storm-dragon.md` (owner's copy): captures that match the concept frames, a clip that passes REVIEW. Status: hypothesis; no build has run on this version.
