#!/usr/bin/env bash
# peakvram.sh <nvidia-smi gpu index> <cmd...>: runs cmd, prints wall time and the GPU's peak memory use (MiB).
gpu=$1; shift
log=$(mktemp); start=$(date +%s.%N)
( while sleep 0.5; do nvidia-smi -i "$gpu" --query-gpu=memory.used --format=csv,noheader,nounits; done ) >"$log" &
sampler=$!
"$@"; rc=$?
kill $sampler
echo "PEAKVRAM gpu=$gpu peak_mib=$(sort -n "$log" | tail -1) wall_s=$(awk "BEGIN{printf \"%.1f\", $(date +%s.%N) - $start}") rc=$rc"
rm -f "$log"; exit $rc
