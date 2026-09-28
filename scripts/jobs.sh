#!/usr/bin/env bash
# Tiny background-job manager: start | status | stop | logs
#   scripts/jobs.sh start <name> <command...>
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs .pids

alive() { [[ -f ".pids/$1.pid" ]] && kill -0 "$(cat ".pids/$1.pid")" 2>/dev/null; }

case "${1:-}" in
  start)
    name="$2"; shift 2
    if alive "$name"; then echo "$name already running (pid $(cat .pids/$name.pid))"; exit 0; fi
    nohup "$@" >> "logs/$name.log" 2>&1 &
    echo $! > ".pids/$name.pid"
    echo "started $name (pid $!) -> logs/$name.log"
    ;;
  status)
    found=0
    for f in .pids/*.pid; do
      [[ -e "$f" ]] || continue
      found=1; n=$(basename "$f" .pid)
      if alive "$n"; then echo "RUNNING  $n (pid $(cat "$f"))"; else echo "STOPPED  $n"; rm -f "$f"; fi
    done
    [[ $found -eq 0 ]] && echo "no background jobs"
    echo "--- data collected ---"
    for d in data/raw/wiki/* data/raw/youtube; do
      [[ -d "$d" ]] && printf "%-28s %s files\n" "$d" "$(find "$d" -name '*.json' | wc -l | tr -d ' ')"
    done
    ;;
  stop)
    for f in .pids/*.pid; do
      [[ -e "$f" ]] || continue
      n=$(basename "$f" .pid)
      if alive "$n"; then kill "$(cat "$f")" && echo "stopped $n"; fi
      rm -f "$f"
    done
    ;;
  logs)
    ls logs/*.log >/dev/null 2>&1 || { echo "no logs yet"; exit 0; }
    tail -n 20 -f logs/*.log
    ;;
  *) echo "usage: $0 start <name> <cmd...> | status | stop | logs"; exit 1 ;;
esac
