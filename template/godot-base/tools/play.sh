#!/usr/bin/env bash
# tools/play.sh SECONDS "MARKER1 MARKER2 ..." [game flags...]: run scenes/main.tscn headless (via the broker) with
# the given flags (e.g. --autopilot --seed=7), print its GAME_ markers and errors, and fail unless every listed marker
# appears (as GAME_<MARKER>) and there is no SCRIPT ERROR. The dispatcher's play checks use this.
set -u
cd "$(dirname "$0")/.."
studio godot-import >/dev/null 2>&1   # registers new class_name scripts (Board, Solver, ...) before running
secs=$1; want=$2; shift 2
out=$(studio godot-play scenes/main.tscn "$secs" --headless "$@" 2>&1)
log=$(grep -o '\.studio/logs/[^ )]*\.log' <<<"$out" | tail -1)
[[ -n $log && -f $log ]] || { echo "$out"; echo "PLAY FAILED: no log"; exit 1; }
grep -E "GAME_|SCRIPT ERROR|ERROR:|Parse Error" "$log" | grep -v "GAME_MOVE" | tail -60
echo "moves: $(grep -c GAME_MOVE "$log")"
rc=0
if grep -q "SCRIPT ERROR\|Parse Error" "$log"; then echo "PLAY FAILED: script errors"; rc=1; fi
for m in $want; do grep -q "GAME_$m" "$log" || { echo "PLAY FAILED: missing GAME_$m"; rc=1; }; done
((rc == 0)) && echo "CHECK OK"
exit $rc
