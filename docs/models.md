# Models: what we tested, what won, and why

Everything here was measured on one **reference machine**: Intel i9-10920X (12 cores), 64 GB DDR4, an
**RTX 5070 Ti 16 GB** (the worker GPU) and an **RTX 2060 6 GB** (small models, Godot rendering), Linux (CachyOS),
llama.cpp via llama-swap, Claude Code as the worker harness. Scores come from the graded capability suites in
`evals/` (graders are validated against reference solutions before any model runs), plus what happened in real
productions. Other hardware: see [Choosing for your hardware](#choosing-for-your-hardware).

**Short version**

| role | model | why |
|---|---|---|
| default worker: Unreal, Blender, coding, ffmpeg, audio **and Godot** | **Gemma 4 26B-A4B** (UD-Q4_K_XL, experts partly in RAM) | 19/20 agent runs in the capability suite (Qwen3.6 16/20 on the same tooling), 8/8 in the Godot suite; fewest turns, smallest contexts; vision pre-screen 1.00 |
| retry / long context / log triage / look-critical steps | **Bonsai 2 27B** (Qwen3.8-27B in ternary weights, PrismML fork) | also 19/20 and 8/8 Godot, a *different* model family (a retry doesn't repeat the first one's blind spot), 188K context recall 3/3, log triage 0.88, best-looking renders by eye; ~3x slower |
| fallback worker | Qwen3.6-35B-A3B (UD-Q4_K_XL) | 16/20 on the same tooling, 4/8 Godot; fastest tokens but 2.3x the turns |
| quick log triage on a small second GPU | Spark-X2.5-4B | 0.56-0.75 on log triage (varies run to run) in ~20 s; never for multi-step tool work |
| director | Claude (Claude Code) | plans, reviews, makes the visual calls; local workers draft and the director verifies |

## Capability suite, rerun: Gemma 4 vs Qwen3.6

The same suite on today's tooling (no stray MCP tools in workers, synthetic vision frames); table:
`evals/scorecard-gemma-qwen.md`.

| model | agent tasks passed | mean | worker time | turns | peak ctx | vision | log triage |
|---|---|---|---|---|---|---|---|
| **Gemma 4 26B-A4B** | **19/20** | **0.995** | **57 min** | **172** | **45K** | **1.00 / 1.00** | 0.50 |
| Qwen3.6-35B-A3B | 16/20 | 0.974 | 80 min | 401 | 81K | 0.93 / 1.00 | 0.75 |

Qwen3.6 generates faster (77.6 vs 67.8 tok/s) but takes 2.3x the turns, and its misses were spec slips (wrong
musical key, a wrong light, a C++ test file with 0 asserts). Gemma's one miss was the same rounding rule Bonsai
missed in the first suite. With Gemma also the Godot worker, one model now does all agent work.

**Two parallel workers on one GPU?** Measured (Gemma 4, llama-server `-np 2 --kv-unified` vs `-np 1`,
same 131K context shared): generation for two requests at once reaches 1.3x the total tokens/s (59 vs 45 tok/s, each
request dropping to 44 tok/s), but prompt processing doesn't scale at all (~830 tok/s shared), so two 36K-token
prompts take exactly as long either way (106 s). Agent turns are a mix of both, so a second slot would gain ~10-20%
while making each worker slower and sharing one context budget. Not worth it: workers run one at a time.

## Capability suite (first run)

14 tasks in 7 areas: coding (bug fix, feature, C++), Unreal (scene, sequence, C++ actor, render via the broker),
Blender + media (model a prop, ffmpeg edit, procedural audio), vision (exposure and defect judgement on frames), long
context recall, and Unreal log triage. Agent tasks run 2 reps; full table: `evals/scorecard-suite.md`.

| model (Claude Code harness) | coding | Unreal | Blender + media | vision | long ctx | log triage |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | 6/6, median 2.3 min | 8/8, 3.4 min | 5/6 (a prop's base above z=0) | 0.96 | 106K: 3/3 | 0.62 |
| Bonsai 2 27B | 5/6, 9.6 min | 8/8, 5.9 min | 6/6 | 0.96 | **188K: 3/3** | **0.88** |
| Qwen3.8-27B Q3 | - | - | - | **0.97** | 49K max | 0.44 |
| Spark-X2.5-4B (OpenCode) | 0.82 | - | 0/2 | - | 26K: 3/3 | 0.75 in 0.4 min |
| Qwen3.5-4B / 9B (OpenCode) | 1/2 | - | 0/4 | 0.87 (4B) | small | 0.25 |

**Harness matters as much as the model.** The same Bonsai model in OpenCode instead of Claude Code: Unreal 2/3
instead of 8/8, Blender/media equal, coding slightly worse, and slower with larger contexts. All workers now run in
Claude Code (`claude-local`). One OpenCode run was excluded because the worker read its own grader: that led to the
stricter sandbox (workers can read nothing outside their project).

**Small-GPU challengers**, 2 runs each on the 2060, same tooling (`evals/scorecard-small-gpu.md`):

| model | UE log triage | vision exposure / defects | recall (32K) |
|---|---|---|---|
| Gemma 4 E4B | **0.69** (~90 s) | 0.78 / 0.81 | 0.90 |
| Spark-X2.5-4B | 0.56 (~20 s) | no vision | 1.00 |
| Qwen3.5-4B | 0.31 | **0.95 / 1.00** (~2-3 min) | 1.00 |
| Ministral 3 8B | 0.38 | 0.65 / 0.62 | context too small |

No small model is good enough to change the routing: triage stays with Bonsai (0.88) and vision with Gemma 4 26B
(1.00). Gemma 4 E4B is the best small model for triage, Qwen3.5-4B for vision; Ministral 3 8B was dropped.

**Small models** (4-9B on the 6 GB card) can fix a single file or triage a log, but fail multi-step tool work
(Blender 0/3, ffmpeg 0/3): they never get delegated agent tasks.

## Godot suite

4 tasks: port four Godot 3 scripts to 4.7 (behaviour tests), a race-logic class against 21 hidden tests, a 2D
platformer whose **exported Linux build** must finish the level on autopilot, and a 3D clip via Movie Maker. Same
prompts and time limits for every model. Table: `evals/scorecard-godot.md`.

Two runs per task for the three capable models (scores of run 1 and run 2):

| model | port | race logic | platformer + export | clip | passed | worker time per 4 tasks |
|---|---|---|---|---|---|---|
| **Gemma 4 26B-A4B** | 1.00 1.00 | 1.00 1.00 | 1.00 1.00 | 1.00 1.00 | **8/8** | **~31 min** |
| **Bonsai 2 27B** | 1.00 1.00 | 1.00 1.00 | 1.00 1.00 | 1.00 1.00 | **8/8** | ~91 min |
| Qwen3.6-35B-A3B | 1.00 1.00 | 0.96 1.00 | 0.35 0.70 | 0.70 1.00 | 4/8 | ~77 min |
| Qwen3.8-27B Q3 | 1.00 | 0.00 | 0.25 | 0.15 | 1/4 | context-capped |
| Mellum2.1 12B-A2.5B | 0.00 | 0.00 | 0.25 | 0.15 | 0/4 | gave up |

- **Godot 3 drift was not the problem.** Research and community reports say local models mix Godot 3 syntax into
  Godot 4 code; with the tooling (a version-exact API reference in every project, a drift linter, a full compile
  check, verified cookbook recipes) none of the three capable models shipped any. Failures were **behaviour** (an
  autopilot that couldn't time the jump over a gap, a spec edge case) and **time**.
- **Gemma 4** solved every task with the fewest turns and smallest contexts. By eye its clip was the weakest of the
  passing ones (blown-out floor), so look-critical steps go to Bonsai.
- **Mellum2.1** (12B, fast: 245 tok/s) mistook Claude Code's long system prompt for the user's message and replied
  "I'm ready to help!": too small for this harness.
- **Qwen3.8-27B** only fits in 16 GB as Q3 with a 49K context; Claude Code's system prompt plus the task overflow it
  and auto-compaction fails. Its scores measure the context cap, not the model. (Its own chat template also rejects
  Claude Code's `developer` role: we give it Bonsai's template, from the same model family.)
- **Qwen3.6** did better in its second run (3/4: race logic and clip passed) after two tooling fixes between the
  runs (no stray MCP tools, no model reloads for Godot jobs), but missed the platformer both times: its autopilot
  needed most of the time limit and the export never happened.

## What production taught us (beyond the suites)

The suites are small tasks. In real productions (a 20 s Unreal film, a C++ Unreal game, a 10 s comparison clip):
- Workers are strong on code and API plumbing and **weak on spatial maths**: scale units (a 100x error made 17 km
  towers), bounds used as positions, hand-made rotations. Their own checks don't catch it. Prescribing tested
  helpers (`su.wall_panel`, `su.face_point`) fixed it: the same city step that failed twice in the film passed on the
  first try in the comparison clip.
- Code that compiles is not a working game: in the C++ game nine bugs compiled cleanly (overlap flags, tick
  disabled, input class) and only the self-playing **autopilot** test found them. Every game gets one.
- Every GPU job used to unload the worker LLM (2-4 min to reload and re-read 60-100K tokens of context); for Godot
  that dominated the run time. Godot now renders on the small GPU and runs logic headless.
- Workers loaded the user's own MCP servers (outside the sandbox, ~100 extra tools in every request): workers now
  start with no MCP servers. Base context for a task dropped from 43K to 23K tokens.

## Choosing for your hardware

`install.sh` suggests a profile from your GPUs; profiles live in `models/profiles/` and only the reference one is
measured. The others are estimates from the same models and the VRAM each needs:

| profile | GPU | worker | retry | Godot | notes |
|---|---|---|---|---|---|
| `online` | none needed | Claude Sonnet | Claude Opus | Claude Sonnet | API costs; no local setup; the studio works the same |
| `8gb` | 8 GB | Bonsai 2 (49K ctx) | Qwen3.6 (mostly in RAM, slow) | Bonsai 2 | small contexts: consider `online` or mixed for big steps |
| `12gb` | 12 GB | Bonsai 2 (131K) | Gemma 4 (experts in RAM) | Gemma 4 | |
| `16gb` | 16 GB | Gemma 4 | Bonsai 2 | Gemma 4 | the reference models without the small GPU |
| `16gb+6gb-reference` | 16 GB + 6 GB | Gemma 4 | Bonsai 2 | Gemma 4 | **measured** |
| `24gb` | 24 GB | Gemma 4 (all in VRAM) | Bonsai 2 | Gemma 4 | |

RAM matters for MoE models whose experts live in system RAM (Qwen3.6, Gemma 4 on smaller cards): faster RAM means
faster generation, and with **128 GB** the strongest open model we looked at, Qwen3.8-Flash-Next (125B MoE, 6B
active), becomes practical (users report ~600 tok/s prompt processing and ~15 tok/s generation on a 16 GB card +
128 GB RAM; with 64 GB it doesn't fit). Research notes and sources: `docs/godot-model-research.md`.

**Adding a model:** add it to `models/catalog.json` (files, flags, context, vision), put it in a profile, run
`install.sh --no-build` (or `models/download.sh` + `models/gen-config.py llama-swap`), then measure it:
`evals/harness.py run --tasks '*' --models <id> --agents claude` and compare with the scorecards.
