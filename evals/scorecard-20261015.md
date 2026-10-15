# Capability scorecard: Gemma 4 vs Qwen3.6, same tooling (2026-10-15)

Same 14-task suite as `scorecard-20261008.md`, rerun on today's tooling: workers start with no MCP servers, Godot
jobs never unload the worker, vision tasks use the synthetic frames from `assets/make_vision_assets.py`. 2 runs per
task, Claude Code harness, reference machine (RTX 5070 Ti 16 GB + RTX 2060 6 GB, 64 GB DDR4-3000). Qwen3.6 skipped
long-context recall (1.00 on 2026-10-08, unchanged tooling for that direct task).

## Agent tasks (10 tasks x 2 runs: coding, Unreal, Blender, ffmpeg, audio)

| model | passed | mean score | total worker min | total turns | peak ctx |
|---|---|---|---|---|---|
| **gemma4-26b-a4b** | **19/20** | **0.995** | **57** | **172** | **45K** |
| qwen3.6-35b-a3b | 16/20 | 0.974 | 80 | 401 | 81K |

- Gemma's miss: coding_2 run 1 (rounding rule, 12/14 hidden tests; Bonsai missed the same rule on 2026-10-08).
- Qwen's misses: audio in the wrong key (A minor asked), coding_2 13/14, a C++ test suite with 0 asserts after 41
  turns, a wrong light in ue_1 after 51 turns and 81K context.
- Qwen generates faster (77.6 vs 67.8 tok/s) but needs 2.3x the turns, so Gemma finishes first.

## Direct tasks

| task | gemma4-26b-a4b | qwen3.6-35b-a3b |
|---|---|---|
| vision exposure (20 frames) | **1.00 1.00** | 0.95 0.90 |
| vision defects (8 frames) | 1.00 1.00 | 1.00 1.00 |
| UE log triage | 0.50 0.50 | **0.62 0.88** |
| long-context recall | 0.95 0.90 (3/3 at 28K and 103K; extra text) | (1.00 on 2026-10-08) |

Log triage stays with Bonsai (0.88 on 2026-10-08).

## Decision

Gemma 4 becomes the default worker for everything (it was already the Godot worker, 8/8): one model for all agent
work, no reloads between Godot and other steps. Bonsai stays retry, long context and log triage. Qwen3.6 stays in
the catalog as a fallback.

## Per task

| area | task | agent | model | pass | mean score | mean s | peak ctx |
|---|---|---|---|---|---|---|---|
| blender_media | audio_1_synth | claude | gemma4-26b-a4b | 2/2 | 1.00 | 133 | 24471 |
| blender_media | blender_1_model | claude | gemma4-26b-a4b | 2/2 | 1.00 | 96 | 26776 |
| blender_media | ffmpeg_1_edit | claude | gemma4-26b-a4b | 2/2 | 1.00 | 118 | 25899 |
| coding | coding_1_bugfix | claude | gemma4-26b-a4b | 2/2 | 1.00 | 107 | 21487 |
| coding | coding_2_feature | claude | gemma4-26b-a4b | 1/2 | 0.95 | 223 | 29830 |
| coding | coding_3_cpp | claude | gemma4-26b-a4b | 2/2 | 1.00 | 223 | 30815 |
| longctx | longctx_1_recall | direct | gemma4-26b-a4b | 2/2 | 0.93 | 93 | 0 |
| triage | triage_1_ue_logs | direct | gemma4-26b-a4b | 0/2 | 0.50 | 182 | 0 |
| ue | ue_1_scene | claude | gemma4-26b-a4b | 2/2 | 1.00 | 170 | 34244 |
| ue | ue_2_sequence | claude | gemma4-26b-a4b | 2/2 | 1.00 | 198 | 44666 |
| ue | ue_3_cpp | claude | gemma4-26b-a4b | 2/2 | 1.00 | 145 | 23096 |
| ue | ue_4_render | claude | gemma4-26b-a4b | 2/2 | 1.00 | 291 | 41321 |
| vision | vision_1_exposure | direct | gemma4-26b-a4b | 2/2 | 1.00 | 76 | 0 |
| vision | vision_2_defect | direct | gemma4-26b-a4b | 2/2 | 1.00 | 36 | 0 |
| blender_media | audio_1_synth | claude | qwen3.6-35b-a3b | 1/2 | 0.90 | 194 | 24380 |
| blender_media | blender_1_model | claude | qwen3.6-35b-a3b | 2/2 | 1.00 | 295 | 51351 |
| blender_media | ffmpeg_1_edit | claude | qwen3.6-35b-a3b | 2/2 | 1.00 | 170 | 29931 |
| coding | coding_1_bugfix | claude | qwen3.6-35b-a3b | 2/2 | 1.00 | 78 | 18139 |
| coding | coding_2_feature | claude | qwen3.6-35b-a3b | 1/2 | 0.97 | 114 | 23080 |
| coding | coding_3_cpp | claude | qwen3.6-35b-a3b | 1/2 | 0.95 | 374 | 57281 |
| triage | triage_1_ue_logs | direct | qwen3.6-35b-a3b | 1/2 | 0.75 | 166 | 0 |
| ue | ue_1_scene | claude | qwen3.6-35b-a3b | 1/2 | 0.92 | 480 | 81255 |
| ue | ue_2_sequence | claude | qwen3.6-35b-a3b | 2/2 | 1.00 | 214 | 42375 |
| ue | ue_3_cpp | claude | qwen3.6-35b-a3b | 2/2 | 1.00 | 187 | 24699 |
| ue | ue_4_render | claude | qwen3.6-35b-a3b | 2/2 | 1.00 | 287 | 42495 |
| vision | vision_1_exposure | direct | qwen3.6-35b-a3b | 2/2 | 0.93 | 171 | 0 |
| vision | vision_2_defect | direct | qwen3.6-35b-a3b | 2/2 | 1.00 | 52 | 0 |
