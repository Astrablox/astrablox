# board/ — the studio's shared desk

Runtime state of the AstraBlox studio (docs/v0.3-contract.md §3–§8). Everything here except this
file and `STATE.md` is written by tools and ignored by git.

| Path | What | Written by |
|---|---|---|
| `STATE.md` | one page: goal, latest owner instruction, current scene, top three defects, builds waiting, next step | lead |
| `tasks/<id>.md` | task cards (§4) | `tools/board/board.py new / claim / done / blocked / return` |
| `reports/<id>.md` | reports (§5), one per task | the lane that did the task |
| `heartbeats/<session>.json` | `{session, time, task}`; refreshed by `board.py next / claim / done / heartbeat` | every session |
| `queue.log` | every signal sent on the bus | `board.py signal` |
| `supervisor.log` | wake-ups, reopened tasks, stops | `tools/board/supervisor.py` |

Rules that the tools enforce: a card is claimed only by its own lane and only from `open`/`returned`
with all `depends_on` done; `done`/`blocked` need a report that passes `board.py report-check`; a
card is returned once (the second round goes to `studio/inventory.md`); a signal must match one of
the §3 forms or it is refused.

Daily use from a lane session:

```
python tools/board/board.py next --lane world          # what to do
python tools/board/board.py claim 043 --lane world
python tools/board/board.py heartbeat --session world --task 043   # while working, every ~10 min
python tools/board/board.py done 043 --report board/reports/043.md
python tools/board/board.py signal --to lead "TASK 043 DONE board/reports/043.md"
```

Stopping the studio: create a file named `STOP` in the checkout root (`scripts/run_studio.ps1 -Stop`);
the supervisor sends `STOP` to every session and exits.
