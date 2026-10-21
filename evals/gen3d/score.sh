#!/usr/bin/env bash
# score.sh <generator> <up axis of its raw output, glTF terms>: for each object, clean up out/<gen>/<obj>.glb, measure
# raw + cleaned against the ground truth (plus a bounding-box baseline), render aligned 2x2 sheets.
# Expects the layout under $GEN3D (default /home/user/StudioProjects/evals/gen3d): gt/, out/<gen>/<obj>.glb.
set -euo pipefail
gen=$1 up=$2
G=${GEN3D:-/home/user/StudioProjects/evals/gen3d}
E=$(dirname "$(readlink -f "$0")")
PY=$G/venv-trellis/bin/python
cd "$G"
mkdir -p clean aligned metrics sheets baseline
declare -A GT=([SM_Spinner]=gt/SM_Spinner.glb [treasure_chest]=gt/treasure_chest/treasure_chest.gltf
               [Lantern_01]=gt/Lantern_01/Lantern_01.gltf)
for n in "${!GT[@]}"; do
    raw=out/$gen/$n.glb clean=clean/${gen}_$n.glb
    [ -f "$raw" ] || { echo "missing $raw"; continue; }
    blender -b -P "$E/cleanup.py" -- "$raw" "$clean" 10000 "$up" 2>&1 | grep CLEANUP | sed "s|^|$gen $n |"
    [ -f baseline/box_$n.glb ] || $PY -c "import trimesh,sys; g=trimesh.load(sys.argv[1], force='mesh');
trimesh.creation.box(extents=g.extents).export(sys.argv[2])" "${GT[$n]}" baseline/box_$n.glb
    # one at a time, in a capped scope: a runaway measure must not get the user's terminal OOM-killed
    cap="systemd-run --user --scope -q -p MemoryMax=12G -p MemorySwapMax=0"
    {
        $cap $PY "$E/measure.py" --up "$up" "${GT[$n]}" "$raw"
        $cap $PY "$E/measure.py" --up +y --save-aligned aligned "${GT[$n]}" "$clean" baseline/box_$n.glb
    } > metrics/$gen.$n.jsonl
done
for n in "${!GT[@]}"; do
    [ -f clean/${gen}_$n.glb ] || continue
    blender -b -P "$E/render_views.py" -- clean/${gen}_$n.glb sheets/${gen}_$n.png sheet \
        aligned/clean_${gen}_$n.align.json >/dev/null 2>&1
done
cat metrics/$gen.*.jsonl
