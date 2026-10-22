# Local LLMs for Godot / GDScript on this machine (research, 2026)

Hardware: i9-10920X (12C/24T), 64 GB DDR4, RTX 5070 Ti 16 GB (worker GPU), RTX 2060 6 GB (small models).
Godot target: 4.7.x stable (4.7.2 is the latest maintenance release), GDScript.

## What the evidence says
- **No GDScript leaderboard covers local models.** GameDevBench (333 Godot tasks, ICML 2026) only has huge open
  models: Qwen3.5-397B 5.4 %, Kimi K2.5 ~20 %, vs 50-70 % for frontier hosted agents. GameLogicBench (Godot 4.4,
  2026) evaluates only big hosted/open models (Claude Opus 5 52.8 %, Qwen-3.8-Max 44.4 %); 74 % of failures were
  "runs but violates a behavioural requirement", not syntax. Scaffold/harness changes scores a lot.
  -> Our own measurements on our own harness are the only reliable signal.
- **The only hands-on local Godot 4 test on 16 GB** (note.com, 2026, RTX 5080 16 GB, Q4_K_M): Qwen3.6-35B-A3B
  8.7/10 (consistent over two runs), Gemma 4 26B-A4B 6.5, an 8B VL model 4.5, Nemotron-3-Nano-Omni 4.0 (Godot 3
  syntax). Single author, graded by Claude: anecdotal but matches our capability-suite result.
- **Main failure mode is Godot 3 drift**: `yield`, `KinematicBody2D`, `export var`, `onready var`, 3-arg
  `connect("sig", self, "method")`, `move_and_slide(velocity, ...)`, `Position2D`, `Sprite`, old `Tween` node,
  `instance()`. Smaller/local models drift more. Vendors and users agree that a loop that **runs the game and reads
  the errors** reduces drift more than switching models.
- **Godot fine-tunes** (godot-dodo 2023, Gemma 4 E4B / Qwen2.5-Coder 7B community tunes, SpawnPoint-Coder-7B) are
  small and not agentic: not useful as workers.

## Candidates for this hardware
| model | fit on 16 GB (+64 GB RAM) | evidence | verdict |
|---|---|---|---|
| Qwen3.6-35B-A3B (have) | Q4_K_XL with expert offload; 131K ctx | best local Godot 4 result; strongest tool use in its class (TAU2 81 vs Gemma 68) | **baseline / default** |
| Bonsai 2 27B (have) | yes, 192K ctx | our suite: equal quality, ~3x slower | incumbent retry model |
| Gemma 4 26B-A4B | UD-Q4_K_XL ~17 GB, expert offload | 2nd in the Godot test; weaker tool calling, template quirks reported | **test** (different family = good retry model if it works) |
| Qwen3.8-27B dense (have Q3) | Q3 on 16 GB; Q4_K_M only across both GPUs (16+6) | newest Apache Qwen (2026), no Godot data | **test** (Q3 alone; Q4 split optional) |
| Mellum2.1 12B-A2.5B | Q4 ~7 GB, fast | 2026, RL for coding agents, self-reported SWE-bench 47 %; llama.cpp support unconfirmed | test only if its GGUF runs on our llama.cpp; maybe a fast sub-agent |
| Devstral Small 2 24B | Q4_K_M ~14 GB, tight KV | agentic, vendor SWE-bench 68 %; no Godot data | optional |
| Qwen3.8-Flash-Next (125B MoE, 6B active) | **no**: smallest sane quant 88 GB; 16 GB + 64 GB users report 15-20 tok/s prefill | strongest open model in reach | only with **128 GB RAM** (reported ~600 tok/s prefill, ~15 tok/s decode on a 5070 Ti + 128 GB) |

## Harness measures (bigger lever than the model, per all sources)
1. Version-exact API reference in every project: `godot --doctool` (XML class reference of the installed 4.7.x)
   -> workers grep it inside the sandbox (no network needed) instead of trusting memory.
2. A Godot-3-drift linter (rules above) as a check and as a `studio` action; run before every scene run.
3. Run-and-read-errors loop: headless parse check, run scenes headless with `GAME_` markers / `-autopilot`, Movie Maker
   (`--write-movie`) frames for visual checks; same pattern as the UE autopilot.
4. Godot section in AGENTS.md with the drift list and the 4.x idioms.
(Godot MCP servers exist (godot-mcp, godot-mcp-runtime, ...) but need the editor/network; our CLI broker covers the
same loop inside the sandbox.)

## Sources
- note.com 16 GB Godot 4 test: https://note.com/dapper_crab2524/n/n1d72e66c9e46
- Summer Engine, best LLM for GDScript 2026: https://www.summerengine.com/blog/best-llm-for-godot
- GameDevBench paper: https://arxiv.org/html/2602.11103v2 ; leaderboard: https://benchlm.ai/benchmarks/gamedevbench
- GameLogicBench: https://arxiv.org/html/2609.21562v2
- LAMB Godot 3->4 benchmark: https://github.com/gabriel-gubert/LAMB-Godot-Benchmark
- godot-dodo: https://github.com/minosvasilias/godot-dodo
- Qwen3.6 vs Gemma 4: https://www.datalearner.com/en/ai-models/compare/qwen3-6-35b-a3b/vs/google-gemma-4-26b-a4b
- Qwen3.8 releases: https://www.latent.space/p/ainews-qwen-38-max24t-and-27b-new
- Qwen3.8-Flash-Next speeds: https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/discussions/3 ;
  sizes: https://huggingface.co/bartowski/Qwen3.8-Flash-Next-GGUF
- Mellum2.1: https://datanorth.ai/news/jetbrains-mellum2-1-jumps-from-2-to-47-on-bug-fixes ;
  local: https://modelfit.io/blog/jetbrains-mellum2-1-12b-coding-model-mac/
- Devstral Small 2 GGUF: https://huggingface.co/unsloth/Devstral-Small-2-24B-Instruct-2512-GGUF
- Gemma 4 GGUF: https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF
- Godot 3 drift: https://www.surmado.com/blog/ai-mistakes-in-godot-4-code
- Godot 4.7.1: https://godotengine.org/article/maintenance-release-godot-4-7-1/
- Godot MCP runtime bridge: https://mcpservers.org/es/servers/erodenn/godot-mcp-runtime
