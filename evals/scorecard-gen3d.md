# 3D generation bake-off (task 15): TRELLIS.2 wins clearly, TripoSR only for simple props

Question: can single-image 3D generation fill asset-library gaps (docs/assets-design.md) where workers fail at
open-ended modelling (the SpinnerRun ship)? **Yes, with TRELLIS.2: a game-ready 10k-triangle textured prop in
about 1-2 minutes on the 5070 Ti, shape accuracy close to the original.** It needs a good input image.

## Setup
- Inputs: a 3/4 view (1024 px, transparent background, Blender Eevee) of three models with known ground truth: the
  SpinnerRun spinner (Claude's remodel after the local worker failed), Poly Haven `treasure_chest` and `Lantern_01`
  (CC0). Ground truth means accuracy is measured, not guessed.
- Per output: `cleanup.py` (join, weld, drop specks < 2 % of the object's size, normals, Y-up, origin bottom
  centre, Blender decimation only if still over 10k tris) -> `measure.py` (upright alignment: 24 turns about the up
  axis + rigid ICP; chamfer and F-score at 1/2/5 % of the bbox diagonal; tris, watertight, bodies, non-manifold
  edges) -> `render_views.py` 2x2 sheets in the ground truth's orientation. A bounding box of the ground truth is
  scored as the floor to beat. Driver: `score.sh <generator> <up axis>`.
- Data under `/home/user/StudioProjects/evals/gen3d` (inputs/, gt/, out/, clean/, metrics/, sheets/); scripts in `evals/gen3d/`.
  uv venvs, Python 3.12, torch 2.14 cu130 (system nvcc 13.4, gcc 16).

## Results (cleaned, game budget ~10k tris; F@2 % = share of surface within 2 % of the size, higher is better)

| object | TRELLIS.2 F@2 % | TripoSR F@2 % | box floor | TRELLIS.2 verdict | TripoSR verdict |
|---|---|---|---|---|---|
| Lantern_01 | **1.00** (F@1 % 0.99) | 0.95 | 0.02 | near-identical, wire bail, glass, PBR brass | good shape, washed-out colours |
| treasure_chest | **1.00** (F@1 % 0.87) | 0.15 | 0.58 | right proportions, straps, lock, handle | too deep and tilted: worse than a box |
| SM_Spinner | **0.96** (F@1 % 0.78) | 0.50 | 0.16 | right shape, crumpled panels, no emissive lights | soft blob, pods fused to hull |

| | TRELLIS.2-4B (5070 Ti) | TripoSR (2060) |
|---|---|---|
| time per object | 37-126 s generation + 7-16 s GLB export; model load ~66 s (230 s cold) | ~11 s incl. load |
| VRAM | 3.2-3.5 GiB allocated (chest 9.4); export needs the models offloaded | 5.5 GB peak (whole card) |
| output | PBR textures (2048 px), Y-up, upright | vertex colours, Z-up, tilted by the camera elevation |
| topology | not watertight; many small pieces (chest 375 bodies), some non-manifold edges | mostly one closed-ish blob |

## Findings
- **Decimate inside TRELLIS.2, not in Blender.** `DECIMATE=10000` (CuMesh simplify, then the texture is baked)
  keeps the full accuracy (lantern F@1 % 0.99 at 9.8k tris). Blender's collapse decimation shattered the
  lantern's thin non-manifold parts, and the old "drop islands < 0.5 % of faces" rule deleted real wires: both fixed.
- **Remesh OOM on large surfaces:** the chest (17.4M raw faces) runs out of memory on 16 GB in the export's
  dual-contouring remesh, so it needs `REMESH=0`. It still scores F@2 % 1.00, but has more pieces.
- **Emission is lost:** the spinner's headlights and engine glows come back as plain colour. Glow materials have to
  be re-added in the engine.
- Not watertight: fine for rendering. Collisions should come from simple shapes or a convex decomposition, not
  the mesh.
- TripoSR guesses depth from one view: fine for round, simple props, wrong for boxy ones.

## Incident: the measuring crashed the user's terminal twice
`measure.py` used `trimesh.split()` to count bodies. On a TRELLIS.2 mesh (thousands of pieces) that copies every
piece and passed a 12 GB cap. With three measures in parallel, systemd-oomd killed the whole terminal scope
(alacritty, including Claude Code) at 11:51 and 11:57. Fixed: bodies are now counted with a sparse
connected-components pass, and `score.sh` runs the measures one at a time in a
`systemd-run --user --scope -p MemoryMax=12G` scope. **Lesson: run heavy analysis jobs in a capped scope.**

## Install notes (`evals/gen3d/install-trellis.sh`)
- xformers instead of flash-attn (no multi-hour compile); CuMesh, FlexGEMM and o-voxel patched to C++20 for torch
  2.14; o-voxel installed `--no-deps` (it would rebuild its git dependencies unpatched); `transformers<5` (5.x
  moved DINOv3's layers); `einops`.
- Gated models: DINOv3 (`facebook/dinov3-vitl16-pretrain-lvd1689m`, Meta licence, access granted to hennie42;
  token in ~/.cache/huggingface). The background remover was swapped from briaai/RMBG-2.0 (gated,
  CC BY-NC) to ZhengPeng7/BiRefNet (MIT).
- TripoSR: torchmcubes needs `lerp` renamed (clashes with CUDA 13); `--bake-texture` has an upstream device bug
  (unused).

## Run
```sh
E=/home/user/local-studio/evals/gen3d; cd /home/user/StudioProjects/evals/gen3d/TRELLIS.2
curl -s localhost:8080/unload    # free the 5070 Ti from llama-swap
DECIMATE=10000 CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1 HF_HOME=/home/user/StudioProjects/evals/gen3d/hf \
HF_TOKEN_PATH=$HOME/.cache/huggingface/token ../venv-trellis/bin/python $E/run_trellis.py \
  ../weights/TRELLIS.2-4B ../out/<name> 1024_cascade <image.png>...   # REMESH=0 if the export OOMs
```

## Recommendation
Make TRELLIS.2 the asset library's gap filler (docs/assets-design.md, "Gaps"). For a missing prop: get a clean
concept image, run TRELLIS.2 at a 10k budget, clean it up, then review it like any library asset (taste
check, licence: the generated asset is ours, the models are MIT + DINOv3 licence). Open questions for later: where
the input image comes from (no local text-to-image model yet), and style consistency across generated props.
TripoSR is not worth keeping.
