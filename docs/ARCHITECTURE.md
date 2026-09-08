# Architecture

The Game Master (AGENTS.md) owns scope, sequencing, Studio leases, integration and acceptance.
Specialists receive bounded briefs and own disjoint zones, folders or scripts. Parallel writers
use Edit mode only; Play, player input and camera control have one exclusive owner after the
Edit barrier.

Order of work for a new game: architecture (loop, zones, route, ownership, acceptance) → art
direction with a style kit and named acceptance views → systems and per-zone blockout in
parallel → integration barrier and first playable → per-zone rebuild to the direction →
lighting → effects → sound → UI → narrative → independent art review from captures, code
review, QA, earned player completion → capture and authorized release. The definition of done
and the routing of small fixes are in AGENTS.md.

Each interactable has one physical author and one runtime-state writer. Review gates use
observed behaviour and captures: server-authoritative state, collision and traversal, reset and
replay, composition against the acceptance views, player completion. Reports do not substitute
for inspecting the DataModel, the captures and the scenario.

Craft reference lives in `.agents/skills/` and is loaded by roles on demand; role files in
`.codex/agents/` hold responsibility, algorithm, criteria and report format.

Runtime state lives under `gamemaster/` and is separate from the portable framework.
`scripts/run.ps1` creates a finite run record; the Stop hook may continue the same authorized
session only while its count and deadline allow. The reusable framework is AGENTS.md,
.codex/agents/, .agents/skills/, scripts/, gamemaster/tools/, tests/ and docs/. The owner's
concept determines genre and scope; docs/examples/ is historical.

The studio itself has an owner: `studio-developer` (`.codex/agents/studio-developer.toml`). In mode
IMPROVE, or on any request about how an agent worked, the producer spawns it in FIX mode with the
owner's words, the cycle folder and the paths; then a fresh instance in AUDIT mode judges only the
changed files. `tools/studio/` gives both the evidence: `run_digest.py` (a cycle's reports against
the markers the producer expects), `session_digest.py` (Codex session JSONL as trajectories) and
`check_studio.py` (the static gate every change must pass). `docs/journal.md` records every change
to the studio with its reason and how to verify it; `docs/inventory.md` numbers the problems and
<<<<<<< HEAD
their fates.
=======
their fates. `tools/assets/`, `assets-library/` and `tools/check/` are the roles' own tools for real
assets and checked code; `tools/assets/README.md` describes them.
>>>>>>> harness-local
