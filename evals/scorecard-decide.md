# Decision models and Mellum2 vs our routing: frame QA and job-log triage

Can a native **decision model** (llama.cpp `/v1/systemone`: typed `choice` / `score` / `noul` answers with
probabilities, no generated text) classify and score what Godot and Unreal produce? And is **JetBrains Mellum2**
(12B-A2.5B MoE) a fit for any local role? Reference machine; models on the RTX 5070 Ti unless marked 2060.
llama.cpp master f5027fb (Clef and H2O-Lightning need it; the production build at the time was 2.5 weeks older).

Code: `evals/decide/` (`build_frames.py`, `build_logs.py`, `run.py`, `score.py`); data and raw results in
`$STUDIO_EVAL_HOME/decide/`.

## The two sets

- **Frames (96):** 16 accepted frames from real productions (Don't Panic trailer in UE, NeonRain, Don't Panic
  Island screens, Godot suite shots), each in 6 variants with truth known by construction: good, underexposed,
  overexposed, black, a missing-texture checkerboard patch, a black band. Questions: exposure (choice of 3),
  black frame (yes/no), defect (none / missing texture / black band).
- **Logs (98):** real broker jobs from four productions (Godot check/script/play/export, UE python/build/play,
  Blender), the excerpt a director reads (signal lines + last 15 lines, same shape for passes and failures).
  Truth: the exit code for "did it work"; for failures a rule-based cause (code error, test failure, timeout, bad
  request), spot-checked by hand. Questions: ok (yes/no), cause (choice of 6). The 98 jobs scored here are saved as
  `decide/logs.json`; rebuilding draws a different sample with the same counts per category.

## Frames

| model | how | all | exposure | black | defect | s / frame |
|---|---|---|---|---|---|---|
| **Clef-Flash** (Cloudflare, Q4_K_M + mmproj, 7 GB) | decision | **95%** | 89% | 99% | 96% | **0.42** |
| H2O-Lightning-4B (Q4_K_M + mmproj, 3.4 GB) | decision | 93% | 84% | 98% | 96% | 0.61 (2060: 2.55) |
| Gemma 4 26B-A4B (current vision pre-screen) | chat | 92% | 78% | 100% | 96% | 7.3 |
| Gemma 4 26B-A4B, new build (vision fix #30882) | chat | 91% | 77% | 98% | 98% | 8.3 |
| Gemma 4 E4B (2060), old / new build | chat | 82% / 82% | 62% / 64% | 100% | 71% | 10.1 / 7.6 |
| Qwen3.5-4B (2060, 13 frames only: 33 s each) | chat | 97% | 89% | 100% | 100% | 32.8 |
| pplx-decider-flash v1.2 (Perplexity's GGUF) | decision | - | - | - | - | HTTP 501: not detected as a decision model |

- Decision models answer **17-20x faster** than Gemma at the same accuracy. When Clef-Flash or H2O is confident
  (>= 0.8) about a defect, it was right on every frame (38 and 40 of 48 frames).
- Exposure is where everyone loses: NeonRain's night frames (dark by design) and flat UI screens of the Godot game.
  That is the question, not the models: exposure needs a per-shot reference, missing texture / band / black is
  reliable everywhere.
- Gemma 4's vision fix (llama.cpp #30882, wrong encoder activation) changes nothing measurable here (26B 92 -> 91%,
  E4B 82 -> 82%).

## Logs

| model | how | ok | cause (failures) | s / log |
|---|---|---|---|---|
| Gemma 4 26B-A4B | chat | **94%** | **89%** | 8.4 |
| Spark-X2.5-4B (2060, current quick triage) | chat | 90% | 87% | 0.61 |
| Mellum2.1 12B Thinking (old build) | chat | 92% | 83% | 1.45 |
| Mellum2 12B Instruct Q4_K_M | chat | 83% | 86% | 0.15 |
| Gemma 4 E4B (2060) | chat | 90% | 82% | 6.4 |
| lev (4B) | decision | 93% | 76% | 0.19 |
| Clef-Flash | decision | 84% | 79% | 0.13 |
| H2O-Lightning-4B | decision | 86% | 72% | 0.12 |
| Kev-4B | decision | 91% | 65% | 0.18 |
| Laya (0.4 GB) | decision | 71% | 65% | 0.03 |
| Julia-1 (0.2 GB) | decision | 30% | 11% | HTTP 500 on 54 of 98 (long inputs) |

Decision models are no better than a 4B chat model here, and the markers in our logs (`GODOT_CHECK n failed`,
`GAME_END`, `Result: Failed`, exit codes) already answer "did it work" exactly. Every model misses the same
Blender jobs (exit 0 with error text in the log) and most timeouts (a log that ends normally gives no hint).

## Mellum2 in our roles

| role | result | vs current | fit (0-10) |
|---|---|---|---|
| Agent worker in Claude Code | new build: coding bug fix PASS (12/12, 8 turns, 42 s); Godot race logic FAIL (wrong path; moved: check not clean, 0/21). Godot suite on the old build: 0/4 | Gemma 4: 19/20, Godot 8/8 | 2 |
| UE log triage (root cause + fix, free text) | 2.1: 0.62 / 0.50 old build, 0.38 / 0.50 new; Instruct 0.62 / 0.62 in 2-7 s | Bonsai 0.88, Spark 0.56-0.75 | 3 |
| Job-log classification | Instruct 83% / 86% at 0.15 s; 2.1 92% / 83% at 1.45 s | Spark 90% / 87% on the small GPU | 5 |
| Long context recall | 2.1 Thinking: 0/3 at 29K and 103K (4 runs): reasons past the 4K answer budget, copying code into its reasoning; 1 manual run of 4 answered 3/3. Instruct: 2/3 at 29K | Bonsai 3/3 to 188K | 2 |
| Small model next to the worker (2060, Claude Code's haiku slot) | Instruct Q4 runs with the experts in RAM (`--n-cpu-moe`) at ~1.2 s per log, same answers | Spark fits entirely, 0.6 s, same accuracy | 4 |
| Vision pre-screen | no vision | - | n/a |
| Code completion (FIM, its original use) | the studio has no such step | - | n/a |

Mellum2 is fast and competent at short single-shot coding and classification, but in every role we have, a model
we already run is as good or better. The routing note "loses the task inside Claude Code's long system prompt" is
out of date: on the current llama.cpp it completes simple agent tasks.
