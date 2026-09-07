# Architecture

The Game Master owns scope, sequencing, Studio leases, integration, and acceptance. Specialists receive bounded briefs and own disjoint folders or scripts. Parallel writers use Edit mode only. Play, player input, and camera control have one exclusive owner after the Edit barrier.

Each interactable has one physical author and one runtime-state writer. Review gates use observed behavior: secure server state, collision and traversal, reset/replay behavior, composition, and player completion. Reports do not substitute for inspecting the DataModel and running the scenario.

Runtime state lives under `gamemaster/` and is separate from the portable framework. `scripts/run.ps1` creates a finite run record. The Stop hook may continue the same authorized session only while its count and deadline allow. It does not start unrelated roadmap work.

The reusable framework lives in AGENTS.md, .codex/agents/, scripts/, gamemaster/tools/, tests/ and docs/. The owner's concept and task-specific acceptance contract determine genre and scope; example docs apply only when selected. Local input/capture helpers are optional game test tooling with explicit Studio leases.
