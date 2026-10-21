#!/usr/bin/env bash
# tools/test.sh tests/test_x.gd [...]: run Godot test scripts headless (via the broker), print their output, and
# fail unless every one prints "ALL TESTS PASSED". The dispatcher's acceptance checks use this.
set -u
cd "$(dirname "$0")/.."
studio godot-import >/dev/null 2>&1   # registers new class_name scripts (Board, Solver, ...) before running
rc=0
for t in "$@"; do
  out=$(studio godot-script "$t" 2>&1)
  log=$(grep -o '\.studio/logs/[^ )]*\.log' <<<"$out" | tail -1)
  echo "== $t"
  if [[ -n $log && -f $log ]]; then grep -vE '^(GAME_BOOT|Godot Engine)' "$log" | tail -60; else echo "$out"; fi
  if [[ -z $log ]] || ! grep -q "ALL TESTS PASSED" "$log"; then echo "TEST FAILED: $t"; rc=1; fi
done
((rc == 0)) && echo "CHECK OK"
exit $rc
