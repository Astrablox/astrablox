#!/usr/bin/env bash
# Start AstraBlox v1.0 on Linux/macOS: one or more studio instances, each a Codex session running the lead
# with the lanes as its subagents, in a tmux window of session "astra".
# Usage:
#   scripts/run_studio.sh              # one instance
#   scripts/run_studio.sh 3            # three instances working different scenes
#   scripts/run_studio.sh --stop       # write STOP; every instance halts after its current step
#   scripts/run_studio.sh --dry-run    # print the commands
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"; cd "$root"
n=1; dry=0
for arg in "$@"; do
  case "$arg" in
    --stop) date -u +"STOP requested %Y-%m-%dT%H:%M:%SZ" > STOP; echo "STOP written to $root/STOP"; exit 0 ;;
    --clear-stop) rm -f STOP ;;
    --dry-run) dry=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) n="$arg" ;;
  esac
done
[ -f STOP ] && { echo "STOP file present; use --clear-stop" >&2; exit 1; }
command -v codex >/dev/null || { echo "codex not found on PATH" >&2; exit 1; }
run() { # name, command
  if [ "$dry" = 1 ]; then echo "[$1] $2"; return; fi
  if tmux has-session -t astra 2>/dev/null; then tmux new-window -t astra -n "$1" -c "$root" "$2"
  else tmux new-session -d -s astra -n "$1" -c "$root" "$2"; fi
}
for i in $(seq 1 "$n"); do
  name="lead-$i"
  prompt="You are studio instance $name: the lead of AGENTS.md with the lanes as your subagents. Read game/VISION.md and board/STATE.md, run python tools/board/board.py scenes, claim a scene from game/PLAN.md that no other instance holds (python tools/board/board.py claim-scene <id> --by $name), and run the scene cycle to acceptance. Never ask questions; decide, write the assumption into the scene card, continue until STOP exists."
  run "$name" "ASTRA_SESSION=lead ASTRA_INSTANCE=$name codex --session-name $name -c model_reasoning_effort=xhigh --dangerously-bypass-approvals-and-sandbox \"$prompt\"; exec bash"
done
echo "started $n instance(s) in tmux session astra (tmux attach -t astra)"
