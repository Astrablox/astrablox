# Problem inventory

Numbered problems of the studio and their fates. Numbering: a letter for the campaign that found the problem (P prompts of v0.2.0, H harness, I the studio's own reporting; a new campaign takes the next unused letter and says what it stands for here), a dash, and a running number within that letter. Numbers are never reused; a returning problem gets a new number that cites the old one. Classes: fundamental (set of nodes, order of phases, a role's focus), medium (a section of a prompt, a step, a constraint, an input or output, a tool), small (names, wording, format). Fates: closed by <journal entry> / deferred: <reason> / not a problem: <why>. Status: hypothesis until a live run shows the difference.

| # | Problem | Evidence | Class | Fate |
|---|---|---|---|---|
| P-1 … P-20 | The v0.2.0 diagnosis: builds came out as box rooms with one light because the prompts named primitives as the norm, carried no craft, set negative bars, gave assets no owner and decorated the blockout instead of rebuilding it (full list in the owner's research folder, `00-ДИАГНОЗ-И-ПЛАН.md`) | v0.1 artifacts (`artifacts/images/*.jpg`) | fundamental | closed by v0.2.0 rewrite (2026-09-08); hypothesis |
<<<<<<< HEAD
| H-1 | Roles could not place a real mesh: no path from a concept to a Roblox asset id | v0.1 builds, `generate_mesh` quality | fundamental (harness) | open: asset pipeline in progress, not in this version |
| H-2 | No library of coherent assets; every world assembled from parts | same | fundamental (harness) | open: CC0 kit library in progress, not in this version |
| H-3 | Code went to Studio unchecked; API errors surfaced at run time | v0.1 reviewer findings | medium (tool) | open: luau-lsp gate in progress, not in this version |
| H-4 | Builders worked from words; nothing to compare a capture against | v0.1 captures vs direction text | fundamental (order of work) | open: concept frames per acceptance view in progress, not in this version |
| H-5 | Effects and audio built from nothing; no libraries named | v0.1 vfx reports | medium (context) | open: library sections for the VFX and audio skills in progress, not in this version |
| H-6 | Store search returned nothing usable about triangles or scripts | `roblox-assets` skill "blocked" note in v0.1 | medium (tool) | open: Store search tool in progress, not in this version |
=======
| H-1 | Roles could not place a real mesh: no path from a concept to a Roblox asset id | v0.1 builds, `generate_mesh` quality | fundamental (harness) | closed by `tools/assets/pipeline.py`, `upload.py`, `insert.luau` (2026-09-08); live API not yet run |
| H-2 | No library of coherent assets; every world assembled from parts | same | fundamental (harness) | closed by `assets-library/` catalog and `upload.py --batch` (2026-09-08); kit not yet uploaded |
| H-3 | Code went to Studio unchecked; API errors surfaced at run time | v0.1 reviewer findings | medium (tool) | closed by `tools/check/check_luau.py` and the `roblox-luau` skill (2026-09-08) |
| H-4 | Builders worked from words; nothing to compare a capture against | v0.1 captures vs direction text | fundamental (order of work) | closed by concept frames in `art-director` DIRECTION and the capture-matches-frame rule for builders and lighting (2026-09-08) |
| H-5 | Effects and audio built from nothing; no libraries named | v0.1 vfx reports | medium (context) | closed by library sections in `roblox-vfx` and `audio.md` (2026-09-08); libraries not yet placed in `ServerStorage.StyleKit` |
| H-6 | Store search returned nothing usable about triangles or scripts | `roblox-assets` skill "blocked" note in v0.1 | medium (tool) | closed by `tools/assets/store_search.py` (2026-09-08); verified on real queries |
>>>>>>> harness-local
| I-1 | Nobody owned the studio itself: a weak role report had no node that diagnoses and fixes the role; the owner did it by hand | this folder before 2026-09-08 | fundamental (missing node) | closed by `studio-developer` (2026-09-08); hypothesis |
| I-2 | A run left no readable record of what roles did: reports were prose, trajectories were raw JSONL, markers were checked by nobody | `gamemaster/logs` layout, no tools | medium (tool) | closed by `tools/studio/run_digest.py`, `session_digest.py`, `check_studio.py` (2026-09-08); verified on fixtures |
| I-3 | Changes to the studio had no journal or inventory; a returning problem could not be recognised | no such files before 2026-09-08 | small | closed by `docs/journal.md`, `docs/inventory.md` (2026-09-08) |
