#!/usr/bin/env bash
# Start the AstraBlox v1.0 studio on Linux/macOS: one Codex session per lane plus the supervisor, each in
# a tmux window of session "astra". Lanes and efforts come from tools/board/lanes.json (contract §2, §13).
#
#   scripts/run_studio.sh                  # all lanes + supervisor
#   scripts/run_studio.sh lead world       # subset
#   scripts/run_studio.sh --stop           # write STOP; the supervisor signals every session and exits
#   scripts/run_studio.sh --dry-run        # print commands only
#   tmux attach -t astra                   # look at the windows
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
dry=0; nosup=0; lanes=()
for arg in "$@"; do
  case "$arg" in
    --stop) date -u +"STOP requested %Y-%m-%dT%H:%M:%SZ" > STOP; echo "STOP written to $root/STOP"; exit 0 ;;
    --clear-stop) rm -f STOP ;;
    --dry-run) dry=1 ;;
    --no-supervisor) nosup=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) lanes+=("$arg") ;;
  esac
done
[ -f STOP ] && { echo "STOP file present; run with --clear-stop" >&2; exit 1; }
command -v codex >/dev/null || { echo "codex not found on PATH" >&2; exit 1; }
command -v tmux >/dev/null || { echo "tmux not found" >&2; exit 1; }
py=$(command -v python3 || command -v python)

# lane<TAB>effort lines from lanes.json
mapfile -t table < <("$py" -c 'import json,sys; d=json.load(open(sys.argv[1]))
for l in d["lanes"]: print(l["name"]+"\t"+l["effort"])' tools/board/lanes.json)

run() { # window-name, command
  if [ "$dry" = 1 ]; then echo "[$1] $2"; return; fi
  if tmux has-session -t astra 2>/dev/null; then tmux new-window -t astra -n "$1" -c "$root" "$2"
  else tmux new-session -d -s astra -n "$1" -c "$root" "$2"; fi
}
started=()
for row in "${table[@]}"; do
  name="${row%%$'\t'*}"; effort="${row##*$'\t'}"
  if [ "${#lanes[@]}" -gt 0 ]; then
    keep=0; for l in "${lanes[@]}"; do [ "$l" = "$name" ] && keep=1; done; [ "$keep" = 1 ] || continue
  fi
  prompt="You are the $name session of the AstraBlox studio. Read board/STATE.md, then run: python tools/board/board.py next --lane $name -- and work the task it names (claim it first, refresh the heartbeat with board.py heartbeat --session $name while working, finish with a report and a signal to lead). When there is no task, wait for signals; a signal names a file, read it before acting. Never ask questions; decide, write the assumption in the report, continue."
  run "$name" "ASTRA_SESSION=$name codex --session-name $name -c model_reasoning_effort=$effort --dangerously-bypass-approvals-and-sandbox \"$prompt\"; exec bash"
  started+=("$name")
done
[ "${#started[@]}" -gt 0 ] || { echo "no lanes matched: ${lanes[*]}" >&2; exit 1; }
if [ "$nosup" = 0 ]; then
  run supervisor "ASTRA_SESSION=supervisor $py tools/board/supervisor.py; exec bash"
  started+=(supervisor)
fi
echo "started: ${started[*]}  (tmux attach -t astra)"
