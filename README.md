# local-studio

**Make short films and small games with AI agents, on your own machine.** Claude directs; workers (local LLMs, Claude
models, or a mix) do the work in sandboxes, driving **Godot 4**, **Unreal Engine 5**, Blender, ffmpeg and procedural
audio. Every step is planned, checked and committed, and the director reviews before anything is accepted.

**▶ Made with it: [Don't Panic Island](https://hennie42.github.io/DontPanicIsland/)**, hex Minesweeper on a cartoon
island, playable in the browser ([source and the story of how it was made](https://github.com/hennie42/DontPanicIsland)).
18 of its 19 tickets were built unattended by local models (Gemma 4 and Bonsai 2) on a home PC; Claude planned,
reviewed and polished.

![Three local models' takes on the same 3-second Godot clip, from a capability test](docs/img/godot-clips.jpg)
*The same Godot brief ("neon crystals at night, slow orbit") made by three local models in a capability test.*

- **Two engines.** Godot 4 for 2D/3D games and stylised clips (web, Linux and Windows exports, checked headless);
  Unreal Engine 5 for photoreal cinematics and C++ games (Movie Render Queue, ray tracing).
- **Your choice of models.** Fully local (llama.cpp via llama-swap, profiles from 8 GB to 24 GB of VRAM), fully online
  (Claude models through your own login or API key), or mixed: Claude directs, local models do the bulk.
- **Measured, not guessed.** A capability suite with graders validated against reference solutions decides which
  model does what. The results and the reasoning are in [docs/models.md](docs/models.md).
- **Sandboxed workers.** Workers see only their project folder, have no network beyond the model endpoint, and reach
  GPUs and engines only through a broker that runs a fixed set of vetted actions.
- **A CC0 asset library.** `studio-assets` indexes Kenney, KayKit, Poly Haven and ambientCG, proposes sets for a
  brief on a local review page, and measures every model before it goes into a project ([docs/assets.md](docs/assets.md)).

## How it works

![Architecture: you, the director, sandboxed workers, the broker, engines, models and GPUs](docs/diagrams/architecture.drawio.svg)

You give the director a brief, or a one-line idea that `/grill-me` turns into one by interviewing you. The director
plans small steps, each with a mechanical check, and hands each step to a sandboxed worker. The worker edits the
project and asks the broker for engine and GPU jobs. The director re-runs the checks, reads the diff, looks at the
frames, and only then commits. The whole loop, the per-step handover and how models get picked:
[workflow](docs/workflow.md), [architecture](docs/architecture.md), [evals](docs/evals.md).

For a bigger game the director cuts the brief into tickets, each with an acceptance test it has validated against its
own private solution, and `studio-dispatch` runs them unattended in dependency order (first attempt on the default
worker, a follow-up, then a retry on a different model family; only failures come back to the director). After a
production, `studio-retro` turns what went wrong into findings and guards ([self-improvement](docs/self-improvement-design.md)).

The director is the `/studio` skill ([skill/studio/SKILL.md](skill/studio/SKILL.md)). Workers read a guide per
engine (`template/AGENTS.md`, `template/AGENTS-godot.md`) and use tested helpers instead of hand-written geometry.
Games get an `--autopilot` mode that plays itself and logs `GAME_` markers, so a packaged build can be tested end to end.

## Quickstart

Requirements: Linux with systemd, Python 3.10+ with numpy and pillow, [Claude Code](https://claude.com/claude-code),
bubblewrap, socat, ffmpeg, curl; for local models an NVIDIA GPU (8 GB+), the CUDA toolkit, cmake and ninja (llama.cpp
is built from source); optional: Blender, Unreal Engine 5.x. See [Platforms](#platforms) for what was tested.

```sh
git clone https://github.com/hennie42/local-studio && cd local-studio
./install.sh --dry-run          # shows what it would do: detected GPUs, suggested profile, files it writes
./install.sh                    # or: ./install.sh --profile online   (no local models)
studio-config                   # where everything lives
```

Then, in Claude Code:

```
/studio game: a small 2D platformer in Godot, keyboard and gamepad, web export
/studio 10 s neon city flythrough at night, rain, slow camera
```

`/grill-me` (recommended for anything bigger than a clip) is not part of this repo: it comes from
[mattpocock/skills](https://github.com/mattpocock/skills) (`npx skills add mattpocock/skills`, then link `grilling`
into `~/.claude/skills/`; details in [workflow](docs/workflow.md)).

| setup | how | needs |
|---|---|---|
| **online** | `./install.sh --profile online`; workers use Claude models | a Claude login or `ANTHROPIC_API_KEY`; no GPU for the LLMs |
| **mixed** (recommended with a GPU) | a local profile; direct with `claude`, workers run local models; any step can be routed to a Claude model | a GPU for the workers, Claude for the director |
| **fully local** | a local profile; run the director with `claude-local` too | a GPU with 16 GB+ for a useful director |

Godot is installed by `install.sh` (`godot-refresh`, which also keeps it updated weekly and only switches to a
release that passes the cookbook and template checks); Unreal you install yourself, then set `STUDIO_UE_ROOT` in
`~/.config/studio/studio.env`.

## Platforms

**Built and tested on one machine: [CachyOS](https://cachyos.org)** (Arch-based, kernel 7.2, systemd, the niri
Wayland compositor), Python 3.14, NVIDIA driver 615 with an RTX 5070 Ti (16 GB: the worker LLM, Unreal) and an RTX
2060 (6 GB: a small model, Godot jobs), 64 GB RAM. Everything below is untested unless it says otherwise.

- **Other Arch-based distros** should behave the same (`pacman -S bubblewrap socat ffmpeg python-numpy python-pillow`).
- **Debian, Ubuntu, Fedora:** the scripts are distribution-neutral (user-level, no sudo, systemd user units), so this
  should mostly be packages (`apt install bubblewrap socat ffmpeg python3-numpy python3-pil`). Ubuntu 23.10 and later
  restrict unprivileged user namespaces with AppArmor, which bubblewrap needs: check that `bwrap --ro-bind / / true`
  works as your user before installing.
- **X11 sessions:** the broker reads the desktop session's display variables at job time and was tested on Wayland
  only; X11 should work through the same variables.
- **AMD or Intel GPUs:** the online profile needs no GPU for the models. For local models, `models/build-llama.sh`
  builds llama.cpp with CUDA and GPU detection uses `nvidia-smi`: you'd build llama.cpp with Vulkan or ROCm instead
  and pass `--profile` by hand. Godot, Blender and ffmpeg don't care.
- **Single GPU:** supported (the `8gb`, `12gb`, `16gb` and `24gb` profiles); the GPU is then shared between the model
  and the renderer, and the broker swaps the model out for Unreal jobs.
- **macOS:** not supported. The sandbox (bubblewrap), the services (systemd) and the llama.cpp build (CUDA) are
  Linux-specific; a port would need another sandbox, launchd units and llama.cpp's Metal build. Godot, Blender,
  ffmpeg and Claude Code all run on macOS.
- **Windows:** not supported natively. The likely route is WSL2 with systemd enabled (CUDA works inside WSL2); the
  online profile is the easiest start there. GPU rendering for engine jobs through WSLg is the open question.

## What's in the repo

| path | what |
|---|---|
| `skill/studio/` | the director skill (`/studio`) and the measured routing; `skill/local-task/` delegates one task |
| `bin/` | `studio` (worker-side client), `studio-broker`, `studio-worker`, `studio-sandbox`, `studio-new`, `studio-dispatch` (ticket runs), `studio-ledger`, `studio-assets`, `studio-play` / `studio-serve` (playtest on the desktop or a phone), `studio-shotdiff` / `studio-cutcheck` (look and edit checks), `studio-retro`, `studio-config`, `godot-*` tools, `ue5` |
| `lib/` | machine config (`studio_config.py`), how workers are launched and sandboxed (`studio_agents.py`), the asset library |
| `template/` | project templates: Godot (`godot-base`), Unreal (`ue-base`, `cpp-min`), worker guides |
| `godot/cookbook/` | verified Godot recipes (each compiles and passes a self-test on every new Godot release) |
| `models/` | local models: catalog, hardware profiles, config generator, llama.cpp build, downloads, `claude-local` |
| `evals/` | capability suites, graders, scorecards, a 3D-generation bake-off, an unfinished multi-model comparison clip |
| `retros/` | what went wrong in each production and the guards it led to (Don't Panic Island, its trailer) |
| `docs/` | [workflow](docs/workflow.md), [asset library](docs/assets.md), [models](docs/models.md), [architecture](docs/architecture.md), [Godot](docs/godot.md), [Unreal](docs/unreal.md), [local models](docs/local-models.md), [evals](docs/evals.md), [security](docs/security.md), [self-improvement](docs/self-improvement-design.md) |

## Limits (honest)

- Worker output is a draft: the director checks every step, and some steps (look development, creative calls) are
  usually the director's. Local workers did 5 of 11 steps of the first film, 5 of 7 of the first Unreal game and 18
  of 19 tickets of Don't Panic Island; in that game about two thirds of the script lines are the local models' and
  the rest is the director's playtest fixes and polish.
- Local models are weak at spatial reasoning (scales, rotations, timing a jump) and at "does this feel right?"; the
  helpers and checks exist because of that. Expect retries.
- Tested on one machine (see [Platforms](#platforms)).
- Long productions take hours of local compute: Don't Panic Island's tickets took about 13 hours of GPU time.

## How it was built

local-studio was built in two weeks in 2026 by **Henrik (hennie42)** as the director of the project:
the goal, every design decision (local-first, sandboxing, which engines, the ticket workflow, the asset library's
rules), what to measure, and playtesting. **Claude (Opus 5.5, in Claude Code)** wrote the code and the docs under that
direction, ran the evaluations and productions, and kept a working log; 120 of the private repository's 121 commits
are co-authored by it. The tools were then used for real: two Unreal milestones, Don't Panic Island and its trailer,
and each production's lessons went back into the skill, the templates and the checks.

## License

MIT, see [LICENSE](LICENSE). Godot, Unreal Engine, Blender, llama.cpp, llama-swap and the models have their own
licenses; this repo ships none of them (the installer downloads Godot and the open-weight models you choose).
