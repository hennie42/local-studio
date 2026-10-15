# Local models

Local models are served by [llama-swap](https://github.com/mostlygeek/llama-swap) on `127.0.0.1:8080`, one endpoint
that speaks both the OpenAI and the Anthropic API, so Claude Code (`claude-local`) and OpenCode (`opencode-local`)
can use it. llama-swap starts and swaps llama.cpp servers on demand: one big model at a time on the worker GPU, one
small model at a time on an optional second GPU.

## Files
| file | what |
|---|---|
| `models/catalog.json` | every model: download files, llama.cpp server (stock or the PrismML fork), flags, context, vision, which GPU, what we measured |
| `models/profiles/*.json` | hardware profiles: which models on which GPU, preloads, per-model overrides, and the routing (which model does which step type) |
| `models/gen-config.py` | profile + catalog -> llama-swap config, download list, OpenCode config, effective catalog |
| `models/build-llama.sh` | clone/pull and build llama.cpp (and the PrismML fork when a profile needs it); detects CUDA architectures |
| `models/download.sh PROFILE` | fetch the GGUF files (resumable) into `STUDIO_MODELS_DIR` |
| `models/bin/claude-local` | Claude Code against llama-swap; the model is `STUDIO_LOCAL_MODEL` or `LOCAL_LLM_MODEL` |
| `models/templates/` | chat templates we had to fix (see the catalog notes) |

`install.sh` does all of it for the chosen profile; to change models later, edit the profile or the catalog and run
`models/gen-config.py llama-swap PROFILE -o ~/.config/llama-swap/config.yaml` (llama-swap reloads it).

## Things we learned
- **Bonsai 2 27B** needs the PrismML llama.cpp fork (ternary PTQ1_0 weights: 27B in ~6 GB) and `min_p 0.05`.
- **MoE models** (Qwen3.6-35B-A3B, Gemma 4 26B-A4B) fit 16 GB by keeping some layers' experts in system RAM
  (`--n-cpu-moe N`): generation speed then depends on RAM bandwidth (enable XMP/EXPO).
- Leave ~1 GB of VRAM free: a nearly full card can slow generation drastically.
- Chat templates: some GGUFs' built-in templates reject Claude Code's `developer` role (HTTP 500 on every request):
  give them a compatible template (`chat_template` in the catalog).
- Claude Code needs a large context: its system prompt plus a task is 20-30K tokens before any work. Below ~64K,
  auto-compaction fails on real tasks.
- If every model start fails with "health check timed out" after interrupted loads, restart llama-swap
  (`systemctl --user restart llama-swap`).
- Workers start with `--strict-mcp-config` and no MCP servers: your own MCP servers would run outside the sandbox
  and add tool definitions to every request.
