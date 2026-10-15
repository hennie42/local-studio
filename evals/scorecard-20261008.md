# Capability scorecard: suite-20261007

Scores 0-1 per task (graders validated against reference solutions). `pass` = all checks.

## Summary by area

| area | agent | model | runs | passed | mean score | median min | max ctx |
|---|---|---|---|---|---|---|---|
| blender_media | claude | bonsai2-27b | 6 | 6 | 1.00 | 9.8 | 108257 |
| blender_media | claude | qwen3.6-35b-a3b | 6 | 5 | 0.98 | 6.7 | 86619 |
| blender_media | opencode | bonsai2-27b | 3 | 3 | 1.00 | 13.0 | 91156 |
| blender_media | opencode | qwen3.5-4b | 2 | 0 | 0.00 | 13.2 | 16860 |
| blender_media | opencode | qwen3.5-9b | 2 | 0 | 0.36 | 3.9 | 14706 |
| blender_media | opencode | spark-4b | 2 | 0 | 0.14 | 15.0 | 19831 |
| coding | claude | bonsai2-27b | 6 | 5 | 0.98 | 9.6 | 112156 |
| coding | claude | qwen3.6-35b-a3b | 6 | 6 | 1.00 | 2.3 | 28848 |
| coding | opencode | bonsai2-27b | 3 | 2 | 0.96 | 6.6 | 118363 |
| coding | opencode | qwen3.5-4b | 1 | 1 | 1.00 | 1.7 | 12765 |
| coding | opencode | qwen3.5-9b | 1 | 0 | 0.82 | 1.9 | 12679 |
| coding | opencode | spark-4b | 1 | 0 | 0.82 | 2.0 | 14740 |
| longctx | direct | bonsai2-27b | 1 | 1 | 1.00 | 5.9 |  |
| longctx | direct | qwen3.5-4b | 1 | 1 | 1.00 | 1.1 |  |
| longctx | direct | qwen3.5-9b | 1 | 0 | 0.00 | 0.0 |  |
| longctx | direct | qwen3.6-35b-a3b | 1 | 1 | 1.00 | 5.1 |  |
| longctx | direct | qwen3.8-27b-q3 | 1 | 1 | 1.00 | 0.4 |  |
| longctx | direct | spark-4b | 1 | 1 | 1.00 | 0.3 |  |
| triage | direct | bonsai2-27b | 2 | 2 | 0.88 | 1.0 |  |
| triage | direct | qwen3.5-4b | 2 | 0 | 0.25 | 3.9 |  |
| triage | direct | qwen3.5-9b | 2 | 0 | 0.25 | 3.7 |  |
| triage | direct | qwen3.6-35b-a3b | 2 | 0 | 0.62 | 3.1 |  |
| triage | direct | qwen3.8-27b-q3 | 2 | 0 | 0.44 | 3.6 |  |
| triage | direct | spark-4b | 2 | 0 | 0.75 | 0.4 |  |
| ue | claude | bonsai2-27b | 8 | 8 | 1.00 | 5.9 | 104923 |
| ue | claude | qwen3.6-35b-a3b | 8 | 8 | 1.00 | 3.4 | 38263 |
| ue | opencode | bonsai2-27b | 3 | 2 | 0.83 | 11.2 | 106432 |
| vision | direct | bonsai2-27b | 4 | 4 | 0.96 | 0.4 |  |
| vision | direct | qwen3.5-4b | 4 | 3 | 0.87 | 3.4 |  |
| vision | direct | qwen3.6-35b-a3b | 4 | 4 | 0.96 | 1.8 |  |
| vision | direct | qwen3.8-27b-q3 | 4 | 4 | 0.97 | 1.2 |  |

## Per task

| area | task | agent | model | pass | scores | mean min | peak ctx | notes (last run) |
|---|---|---|---|---|---|---|---|---|
| blender_media | audio_1_synth | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 8.4 | 62219 | dur=20.00s peak=-2.0dB key_ratio=78.7 |
| blender_media | audio_1_synth | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 9.6 | 56974 | dur=20.00s peak=-2.5dB key_ratio=22.6 |
| blender_media | audio_1_synth | opencode | bonsai2-27b | 1/1 | 1.00 | 13.0 | 54205 | dur=20.00s peak=-2.0dB key_ratio=52.5 |
| blender_media | blender_1_model | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 24.6 | 108257 | h=4.80 tris=70 objs=4 |
| blender_media | blender_1_model | claude | qwen3.6-35b-a3b | 1/2 | 1.00 0.88 | 14.7 | 86619 | h=5.10 tris=70 objs=4; failed: base_at_zero |
| blender_media | blender_1_model | opencode | bonsai2-27b | 1/1 | 1.00 | 22.4 | 91156 | h=5.20 tris=80 objs=4 |
| blender_media | blender_1_model | opencode | qwen3.5-4b | 0/1 | 0.00 | 11.3 | 16860 | no assets/tree.glb |
| blender_media | blender_1_model | opencode | qwen3.5-9b | 0/1 | 0.00 | 4.1 | 14706 | no assets/tree.glb |
| blender_media | blender_1_model | opencode | spark-4b | 0/1 | 0.00 | 15.0 | 17026 | no assets/tree.glb |
| blender_media | ffmpeg_1_edit | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 6.7 | 54276 | dur=8.00 order=[0, 1, 2] |
| blender_media | ffmpeg_1_edit | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 3.2 | 34017 | dur=8.00 order=[0, 1, 2] |
| blender_media | ffmpeg_1_edit | opencode | bonsai2-27b | 1/1 | 1.00 | 2.3 | 27028 | dur=8.00 order=[0, 1, 2] |
| blender_media | ffmpeg_1_edit | opencode | qwen3.5-4b | 0/1 | 0.00 | 15.0 | 16630 | no out/edit.mp4 |
| blender_media | ffmpeg_1_edit | opencode | qwen3.5-9b | 0/1 | 0.71 | 3.8 | 14656 | dur=8.00 order=[1, 2, -1]; failed: clip_order, audio_fadeout |
| blender_media | ffmpeg_1_edit | opencode | spark-4b | 0/1 | 0.29 | 15.0 | 19831 | dur=3.50 order=[2, -1, -1]; failed: duration_8s, aac, clip_order, title_first_2s, audio_fa |
| coding | coding_1_bugfix | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 1.8 | 27989 | hidden 12/12, own tests pass (16 tests) |
| coding | coding_1_bugfix | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 1.4 | 17726 | hidden 12/12, own tests pass (18 tests) |
| coding | coding_1_bugfix | opencode | bonsai2-27b | 1/1 | 1.00 | 1.5 | 15424 | hidden 12/12, own tests pass (9 tests) |
| coding | coding_1_bugfix | opencode | qwen3.5-4b | 1/1 | 1.00 | 1.7 | 12765 | hidden 12/12, own tests pass (23 tests) |
| coding | coding_1_bugfix | opencode | qwen3.5-9b | 0/1 | 0.82 | 1.9 | 12679 | hidden 9/12, own tests pass (26 tests) |
| coding | coding_1_bugfix | opencode | spark-4b | 0/1 | 0.82 | 2.0 | 14740 | hidden 9/12, own tests pass (10 tests) |
| coding | coding_2_feature | claude | bonsai2-27b | 1/2 | 0.89 1.00 | 9.6 | 62383 | hidden 14/14; suite pass; new tests yes |
| coding | coding_2_feature | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 2.3 | 22901 | hidden 14/14; suite pass; new tests yes |
| coding | coding_2_feature | opencode | bonsai2-27b | 0/1 | 0.89 | 6.6 | 36985 | hidden 12/14 failed: 10% total;round half up; suite pass; new tests yes |
| coding | coding_3_cpp | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 18.8 | 112156 | hidden 17/17; own build+ctest pass (148 asserts) |
| coding | coding_3_cpp | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 3.3 | 28848 | hidden 17/17; own build+ctest pass (67 asserts) |
| coding | coding_3_cpp | opencode | bonsai2-27b | 1/1 | 1.00 | 25.0 | 118363 | hidden 17/17; own build+ctest pass (127 asserts) |
| longctx | longctx_1_recall | direct | bonsai2-27b | 1/1 | 1.00 | 5.9 |  | 24K: 3/3 in 18s; 106K: 3/3 in 102s; 188K: 3/3 in 236s |
| longctx | longctx_1_recall | direct | qwen3.5-4b | 1/1 | 1.00 | 1.1 |  | 24K: 3/3 in 64s; 90K skipped (ctx 32K); 180K skipped (ctx 32K) |
| longctx | longctx_1_recall | direct | qwen3.5-9b | 0/1 | 0.00 | 0.0 |  | no length fits the context |
| longctx | longctx_1_recall | direct | qwen3.6-35b-a3b | 1/1 | 1.00 | 5.1 |  | 24K: 3/3 in 62s; 106K: 3/3 in 244s; 180K skipped (ctx 131K) |
| longctx | longctx_1_recall | direct | qwen3.8-27b-q3 | 1/1 | 1.00 | 0.4 |  | 24K: 3/3 in 22s; 90K skipped (ctx 49K); 180K skipped (ctx 49K) |
| longctx | longctx_1_recall | direct | spark-4b | 1/1 | 1.00 | 0.3 |  | 26K: 3/3 in 16s; 90K skipped (ctx 32K); 180K skipped (ctx 32K) |
| triage | triage_1_ue_logs | direct | bonsai2-27b | 2/2 | 0.88 0.88 | 1.0 |  | camera:CF skincache:CF property:Cf quit:CF  (C/F = cause/fix correct) |
| triage | triage_1_ue_logs | direct | qwen3.5-4b | 0/2 | 0.12 0.38 | 3.9 |  | camera:cf skincache:CF property:Cf quit:cf  (C/F = cause/fix correct) |
| triage | triage_1_ue_logs | direct | qwen3.5-9b | 0/2 | 0.25 0.25 | 3.7 |  | camera:cf skincache:CF property:cf quit:cf  (C/F = cause/fix correct) |
| triage | triage_1_ue_logs | direct | qwen3.6-35b-a3b | 0/2 | 0.62 0.62 | 3.1 |  | camera:Cf skincache:CF property:Cf quit:Cf  (C/F = cause/fix correct) |
| triage | triage_1_ue_logs | direct | qwen3.8-27b-q3 | 0/2 | 0.50 0.38 | 3.6 |  | camera:cf skincache:CF property:cf quit:Cf  (C/F = cause/fix correct) |
| triage | triage_1_ue_logs | direct | spark-4b | 0/2 | 0.75 0.75 | 0.4 |  | camera:CF skincache:CF property:Cf quit:Cf  (C/F = cause/fix correct) |
| ue | ue_1_scene | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 5.4 | 56728 | all checks pass |
| ue | ue_1_scene | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 3.4 | 32724 | all checks pass |
| ue | ue_1_scene | opencode | bonsai2-27b | 0/1 | 0.50 | 25.4 | 106432 | light wrong; camera missing; 70 labelled actors (duplicates?) |
| ue | ue_2_sequence | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 19.5 | 104923 | all checks pass |
| ue | ue_2_sequence | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 3.5 | 38263 | all checks pass |
| ue | ue_3_cpp | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 6.1 | 43955 | build OK |
| ue | ue_3_cpp | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 2.6 | 20786 | build OK |
| ue | ue_3_cpp | opencode | bonsai2-27b | 1/1 | 1.00 | 11.2 | 49693 | build OK |
| ue | ue_4_render | claude | bonsai2-27b | 2/2 | 1.00 1.00 | 5.3 | 57432 | all checks pass |
| ue | ue_4_render | claude | qwen3.6-35b-a3b | 2/2 | 1.00 1.00 | 4.0 | 34984 | all checks pass |
| ue | ue_4_render | opencode | bonsai2-27b | 1/1 | 1.00 | 3.0 | 27600 | all checks pass |
| vision | vision_1_exposure | direct | bonsai2-27b | 2/2 | 0.90 0.95 | 0.5 |  | 19/20 correct; misses: over_2.jpg: got good/False |
| vision | vision_1_exposure | direct | qwen3.5-4b | 2/2 | 0.95 0.90 | 3.7 |  | 18/20 correct; misses: good_3.jpg: got overexposed/False, over_1.jpg: got None/None |
| vision | vision_1_exposure | direct | qwen3.6-35b-a3b | 2/2 | 0.95 1.00 | 2.8 |  | 20/20 correct |
| vision | vision_1_exposure | direct | qwen3.8-27b-q3 | 2/2 | 0.95 0.95 | 1.2 |  | 19/20 correct; misses: over_2.jpg: got good/False |
| vision | vision_2_defect | direct | bonsai2-27b | 2/2 | 1.00 1.00 | 0.3 |  | 8/8 correct |
| vision | vision_2_defect | direct | qwen3.5-4b | 1/2 | 0.75 0.88 | 2.3 |  | 7/8 correct; misses: clean_2.jpg->black_band |
| vision | vision_2_defect | direct | qwen3.6-35b-a3b | 2/2 | 1.00 0.88 | 1.2 |  | 7/8 correct; misses: clean_2.jpg->None |
| vision | vision_2_defect | direct | qwen3.8-27b-q3 | 2/2 | 1.00 1.00 | 1.2 |  | 8/8 correct |

## GPU sharing benchmark (CoolDemo final: 1080p, 8 samples, 150 frames)

| scenario | ok | render s | VRAM peak MiB (2060 / 5070 Ti) | notes |
|---|---|---|---|---|
| A_5070ti_alone | True | 34.5 | 4958 / 7325 |  |
| B_5070ti_coresident_32k | True | 40.4 | 4958 / 15353 | LLM 93 tok/s idle, 66, 66 during render |
| C_2060_alone | False |  | 5716 / 393 | out of VRAM |

## Excluded runs

- `oc-big/ue_2_sequence/opencode/bonsai2-27b/rep1`: contaminated: the worker read its own grader (old sandbox allowed reads outside the project); fixed sandbox since
