#!/usr/bin/env bash
# tools/probe.sh tests/<probe>.tscn SECONDS "OK LINE" [game flags...]: run a probe scene with the GPU (via the
# broker), print its result lines, and fail unless the OK line appears and the log has no SCRIPT/SHADER ERROR.
# Probes drive the real game with real input events and assert what happens on screen (the autopilot never
# touches the interface). The dispatcher's checks for presentation tickets use this.
set -u
cd "$(dirname "$0")/.."
studio godot-import >/dev/null 2>&1
scene=$1; secs=$2; want=$3; shift 3
out=$(studio godot-play "$scene" "$secs" "$@" 2>&1)
log=$(grep -o '\.studio/logs/[^ )]*\.log' <<<"$out" | tail -1)
[[ -n $log && -f $log ]] || { echo "$out"; echo "PROBE FAILED: no log"; exit 1; }
grep -E "^(ok |FAIL)|SCRIPT ERROR|SHADER ERROR|Parse Error|$want" "$log" | tail -60
rc=0
if grep -q "SCRIPT ERROR\|SHADER ERROR\|Parse Error" "$log"; then echo "PROBE FAILED: script errors"; rc=1; fi
grep -q "$want" "$log" || { echo "PROBE FAILED: no '$want' line"; rc=1; }
((rc == 0)) && echo "CHECK OK"
exit $rc
