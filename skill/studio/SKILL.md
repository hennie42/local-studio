---
name: studio
description: Make a short film (mp4) or a small game with Unreal Engine 5.8 or Godot 4.7, Blender, ffmpeg and procedural audio on this machine, with Claude as director/orchestrator and the local LLMs (claude-local / opencode workers) doing as much of the work as possible. Use when the user says /studio, or asks to create a cinematic, animation, movie clip, trailer, music video, or a game/vertical slice "locally", "with the local models", "in UE5" or "in Godot".
argument-hint: '<one-line brief, e.g. "20 s neon city flythrough at dusk" or "game: top-down orb collector">'
---

# /studio: local-first film and game production

You (Claude) are the director. Local models are the crew. Goal: a finished deliverable with **as much of the
work as possible done by local workers**, verified by you, logged in the ledger. Tooling lives in
the studio repo (`studio-config` prints its location and every configured path; README there).

## 0. Ground rules
- **Delegate by default.** Do a step yourself only if the routing table says it's not local-capable, or after
  a failed local attempt plus one sharper retry (section 4).
- **Verify everything a worker claims**: run checks yourself, read `git diff`, and look at rendered frames with
  the Read tool (you can see images). Never pass on a worker's "done" unverified.
- **Ledger every step** (`studio-ledger`). The final report quotes the ledger summary.
- **Commit** after every verified step (`git add -A && git commit -m "<step>: <what>"`). Never push.
- **GPU**: the broker owns the GPU. Workers and you call `studio ue-render` etc.; never launch UnrealEditor
  (or the `ue5` launcher, which stops the LLM) while workers run. Policy is `timeshare`: the broker unloads the
  local LLM for GPU jobs and the next worker request reloads it (reload + re-reading the worker's context costs
  ~15 s to ~2 min); don't fight it. Timesharing is safe only for GPU jobs the *worker* submits (it waits for them). Don't run
  your own GPU jobs (ue-play, ue-render) while a worker is active: its next request reloads the 15 GB model
  mid-job and UE dies with Vulkan out-of-memory (seen 2026-10-08). Do CPU work (code, builds) meanwhile. Measured: 1080p 8-sample render 34.5 s alone; co-residency with a 32K-context
  LLM works (+17% render time) but agent runs need 40-120K context, so time-sharing at 192K is the default.
  A small second GPU (6 GB) can't render 1080p ray-traced Unreal scenes: use it for small models and Godot jobs
  (STUDIO_GODOT_ON_SMALL_GPU=1), so the worker LLM on the big GPU is never unloaded for Godot.
- **Sandbox**: workers can only see the project (+ system dirs); no home dir, no other projects, no network
  except the local LLM. Don't put secrets or other projects' paths in worker prompts; they can't reach them anyway.
- Root/sudo steps: ask the user to run them in a separate terminal (the `!` prefix can't prompt for passwords).
- **Commit only on a green check:** chain checks and the commit with `&&`, never `;` (a commit once went in after a
  failing check). Stop processes by PID or systemd unit, never `pkill -f <pattern>` (it matched its own shell).

## 1. Preflight (once per session)
```sh
ensure-llama-swap && systemctl --user start studio-broker
cat ~/.config/studio/routing.json        # which local model/agent does what (from the capability tests)
```
`studio-worker` reads its default model/agent from routing.json. Measured profile (scorecard:
`evals/scorecard-20261015.md`, measured on the reference machine described in docs/models.md):
- **Default worker, Godot included: Gemma 4 26B-A4B in Claude Code** (19/20 agent runs passed across coding, UE
  Python/C++/render, Blender, ffmpeg, audio, and 8/8 in the Godot suite; 2-5 min per step; context peaks <= 45K of 131K).
- **Retry with the other model when the approach was wrong:** Bonsai 2 27B (19/20, 8/8 Godot, ~3x slower; a
  different model doesn't repeat the first one's blind spot).
- **Huge inputs (> ~100K tokens) and UE log triage: Bonsai** (3/3 recall at 188K; triage 0.88, Gemma only 0.50).
- **Small models (second GPU): only quick log triage (Spark, ~20 s) and one-file fixes**: never multi-step tool work.
- **Harness: Claude Code workers only** (OpenCode was clearly weaker with the same model).
- **Known worker slips to check in review:** spec details like "base at z = 0" (Blender), musical tempo (graders
  can't verify it: read the synth code), re-runnable level scripts, and above all **spatial maths in UE**: scale
  units (meshes import in cm; a factor 100 error gives 17 km towers), bounds extent used as a position, hand-made
  rotations, unreal.Color expecting 0-255. Workers' self-checks don't catch these (they test their own beliefs):
  measure yourself (actor bounds, mesh bounding boxes) and render a frame. In prompts, prescribe the helpers
  (su.wall_panel, su.face_point, su.camera(look_at=...)) instead of letting workers derive geometry. Vision pre-screen by Gemma 4 is good (1.00 on synthetic frames)
  but you make the visual call.

## 2. Brief to plan
If the project has a `BRIEF.md` from `/grill-me` (docs/workflow.md), treat its decisions as settled and plan from it.
Otherwise ask at most 2-3 questions if the brief is ambiguous (length, mood/style, platform for games); for a big,
vague idea (a whole game), suggest the user run `/grill-me <idea>` first. **Pick the engine**
(say which and why in the plan; the user may name one):
- **Unreal 5.8**: photoreal/cinematic 3D (ray tracing, volumetrics, Movie Render Queue), heavy scenes, C++ games
  where the look matters most. Slow iteration (shader compiles, C++ builds), Linux packages only.
- **Godot 4.7**: 2D games, web-playable games (one command exports Linux/Web/Windows), stylised or simple 3D,
  quick prototypes and clips that don't need photorealism. GDScript reloads instantly and is checked headless
  (`studio godot-check`: Godot 3 idiom lint + full compile with file:line), so workers iterate much faster.
Then create the project and write the plan:
```sh
studio-new <Name> [--cpp]            # Unreal; games: --cpp. Prints the project dir (under STUDIO_PROJECTS_UE)
studio-new <Name> --godot            # Godot 4.7 + GDScript (under STUDIO_PROJECTS_GODOT)
```
**Asset pass** (before the plan; docs/assets.md): workers place assets well and model them badly, so props,
characters, textures, HDRIs, sprites and sound effects come from the CC0 library, not from worker modelling.
Read `studio-assets taste` and `studio-assets style <project>` first, then per need search
(`studio-assets search <words> --kind model|material|hdri|sprite|tileset|ui|sound`, `show <id>`, Read the
thumbnails) and write one proposal JSON: per need a main set and at most one alternative in a different style,
`height_m` where real size matters (Kenney kits are in kit units, not metres), `decorative: true` for no
collision, and `gaps` for what the library lacks (offer a procedural Blender model, a TRELLIS.2 generation
(evals/scorecard-gen3d-20261016.md) or a brief change; never fill a gap silently). Then
`studio-assets propose <project> <file>`, run `studio-assets review <project>` in the background and give the user
the URL; when it returns: `studio-assets fetch <project>` and `studio-assets check <project> --fix`. Tickets name
approved assets by their `assets/...` path. A ticket that needs something new comes back to you for a small ad-hoc
pass; workers never search the library or the network.

Write `<project>/PLAN.md`: the deliverable spec (duration/resolution/fps or game loop + controls), then a numbered
list of **small, verifiable steps**. Each step has: id, owner suggestion (local/claude per routing), the exact files
it touches, and a **check** you can run. Keep steps to what one worker can do in < 20 min. Commit the plan.

Typical cinematic steps: environment script (Scripts/build_env.py) -> hero props (approved library assets; Blender
scripts -> assets/*.glb only for gaps ->
import script) -> materials/lighting -> Level Sequence + cameras -> preview render + QA -> audio score
(Scripts/score.py) + SFX -> final render -> encode + mux -> deliver.
Typical game steps: C++ module skeleton (GameMode, Pawn, input) -> core mechanic class -> level build script ->
HUD/score -> win/lose -> tuning -> package (`studio ue-package`) -> smoke test.
Godot steps: same shape, with GDScript scenes built in code or by generator scripts (`studio godot-script`),
`--autopilot` from the first playable step, `studio godot-play ... --autopilot --shots` as the check, then
`studio godot-export <linux|web|windows|all>` + `studio run-export 60 --autopilot`. Godot clips: scene animated from
time -> `studio godot-movie` -> `studio encode` -> mux.

**Ticket-writing checklist** (from the retros, retros/*/retro-*.md; each item cost a playtest round once):
- Every **test you write is validated as passable**: against a reference implementation, or by reasoning each check
  against the game's real states (a probe once looked for fog before the first click, when there is none by design;
  "fails cleanly today" is not enough).
- Anything a player **sees or touches** gets a real-input probe (`tools/probe.sh`, a ProbeBase scene) and in-game
  screenshots you look at, in a **wide and a tall window**; screenshots come from the viewport texture in a probe,
  not Movie Maker (it crops tall windows).
- **Look changes are measured** with `studio-shotdiff` on variants of **one view in one run** (switch the effect live
  in a probe, like DontPanicIsland's `tests/look.gd`): autopilot frames differ between runs (F40).
- **Art specs are checked from the gameplay camera** (flat labels were unreadable at the camera angle) and against
  real-world meanings (red/white/blue stripes read as the Dutch flag).
- Every **refused player action gives feedback**, and tools say what they did.
- **Audio** gets a measured check (onset grid, loop seam, loop flag) besides listening.
- Tickets over ~15 minutes of expected worker time are split (Gemma's failures were all time-outs). Split by kind:
  an image layout (cards, posters) first as a renderer checked by a contact sheet, then the compositor; an audio
  piece first as the arrangement (you write its test), then the sync to the edit (DontPanicTrailer F6, F10).
- **Unreal API steps** (imports, pipelines, Sequencer): probe the property names yourself first and put them in the
  ticket, cap the ticket at 20 min, and tell the worker where scratch scripts go (`.studio/scratch/`). Without
  names a worker spends the whole budget writing probe scripts (F5).
- Probes wait for game state, never a fixed time.
- Run new probes against **several boards/islands/seeds** before relying on them, sample motion at 3+ points, and
  have effects name their nodes readably (`add_child(node, true)`): probes validated on one island failed on others.
- A ticket names **every code path that triggers its behaviour** (player input, the autopilot, tools) and the data
  each one passes (T18: autopilot moves carry no `opened` list, so a spec that read only that missed every
  autopilot explosion).
- During a project, append a finding to `retros/<Project>/findings.jsonl` with every fix
  (docs/self-improvement-design.md); at the end run `studio-retro <project>` and turn the open guards into guards.

## 3. Delegating a step
Write the worker prompt to a file **outside the repo** (your scratchpad), self-contained:
- Goal and exact acceptance criteria (the step's check, verbatim). Files to create or modify. Files not to touch.
- Remind: "Read AGENTS.md first. Use `studio ...` for Unreal/Blender/render/encode. Commit nothing; I review."
- Include facts the worker can't know (asset paths, names of existing actors, the plan's numbers).
Run it in the background (Bash `run_in_background: true`):
```sh
studio-worker <project> --step <id> --prompt-file <file> [--model M --agent claude|opencode] --timeout 2400
```
It prints a JSON summary (result text, session_id, turns, seconds, diff stat). Only one worker at a time: the local
GPU model serves one request at a time. While it runs, plan the next step or review earlier output; don't edit
files the worker is touching.

## 4. Review, then retry or take over
1. Run the step's check yourself (against files in the project: a worker's checks against its sandbox-private /tmp
   don't count); read the diff (`git -C <project> diff --cached`); for visuals render a preview and
   Read 2-4 frames (start/middle/end + anything suspicious).
2. Pass: `studio-ledger <project> verdict --step <id> --outcome pass`, commit, next step.
3. Fail, first time: send **one sharper follow-up**: name the exact defect, the evidence (log line, frame, failing
   check) and the expected result. Small defect -> same session and model:
   `studio-worker <project> --step <id> --resume <session_id> --prompt-file <followup>`.
   Wrong approach -> fresh session with the retry model (routing.json `retry`, Bonsai):
   `studio-worker <project> --step <id> --model bonsai2-27b --prompt-file <full prompt + what went wrong>`.
4. Fail again: `studio-ledger <project> verdict --step <id> --outcome fail --note "<why>"`, then do the step yourself,
   `studio-ledger <project> add --step <id> --owner claude --outcome pass --note "<what you changed>"`, commit, and
   hand the **next** step back to the local worker. Partial success: keep the good part, fix the rest yourself.
5. Repeated failures of the same kind mean the routing is wrong: do that step type yourself for the rest of
   the project and say so in the final report.

## 5. Rendering and QA (cinematics)
- Long renders run in chunks per shot (resumable over a power-off): each chunk starts one frame early, one-shot
  props vanish on the cut frame, and after the render `studio-cutcheck <frames> --edit <edit.json>` must pass: a
  chunk's first frame ghosts the previous shot otherwise, and contact sheets don't show it (DontPanicTrailer F11).
- Water: a shader plane (shore-distance field, panned normals), not the Water plugin, which renders nothing headless
  (F3). Manual exposure needs "apply physical camera exposure" off (`su.post_process` does it; F2).
- Preview: 960x540, 1 temporal sample. QA by eye: exposure, framing, black frames, missing-texture checkerboards,
  popping, camera through geometry. Local vision models can pre-screen frames, but you make the call.
- Final: 1920x1080 (or as briefed), 8 temporal samples, warm-up 60/32. Then `studio encode`, then mux audio:
  `ffmpeg -i out/film_video.mp4 -i audio/score.wav -c:v copy -c:a aac -b:a 192k -shortest out/<Name>.mp4`.
- Audio is procedural Python (numpy/scipy) per AGENTS.md: score + SFX timed to the shot list; peaks < -1 dBFS.

## 6. Games
- Every game gets an `-autopilot` (UE) / `--autopilot` (Godot) mode that plays itself to the finish and logs
  `GAME_` markers: it is the automated end-to-end test, in the editor and in the packaged/exported build. Compiling
  is not testing: in Milestone 2 nine bugs compiled cleanly and only the autopilot playtest found them.
  Non-linear games get layered tests instead of one run (docs/godot.md, "Testing non-linear games"): logic tests,
  a reachability check of the progression graph, one scenario autopilot per route/ending (fixture start, objective
  bot on navigation), a seeded random explorer, and a coverage check over all markers.
- **The autopilot is not a playtest of the interface** (Don't Panic Island, 2026-10-18: 15/15 tickets passed their
  autopilot checks, and the first human found: clicks swallowed by a full-screen HUD Control, help button and tool
  bar off-screen (bottom-anchored panels grow down by default), centred panels hanging from the centre, two tips
  drawn on top of each other, a black screen when the small GPU's LLM held the VRAM, music timed in bars instead
  of beats, unreadable numbers at the camera angle). Every UI or presentation ticket also needs:
  a **real-input check** (a probe scene that clicks in window coordinates, `get_screen_transform() * pos`, and
  asserts the result, like DontPanicIsland's `tests/play_click.tscn`), an **in-game screenshot** reviewed by the
  director (`get_viewport().get_texture().get_image()` from a probe; Movie Maker crops tall windows), in a wide
  and a tall window shape (frame with maths, or a 1920x1080 SubViewport sharing the world), and for audio a
  measured check (onset grid, loop seam) besides listening. Before the human playtest: `godot-web-smoke` for web
  exports, and start desktop builds with `studio-play` (it frees the small GPU first).
- **Unreal**: C++ in `Source/<Name>/`; build with `studio ue-build`; levels via Python scripts; input via Enhanced
  Input set up in C++ (no Blueprint graphs: workers can't edit them). Package with `studio ue-package`, verify with
  `studio run-packaged 200 -autopilot` (markers via GameEvent.h: Shipping strips UE_LOG).
- **Godot**: delegate with `--model` from routing.json `godot.worker` (Gemma 4, same as the default worker; retry/look-critical:
  `godot.retry`, Bonsai). GDScript only; the worker must run `studio godot-check` after every edit (local models drift into
  Godot 3 syntax; `godot-api/` holds the exact 4.7 API to grep). Review: `godot-check` clean, `godot-play` log has
  the expected markers and no `SCRIPT ERROR`, screenshots look right. Exports are chosen at export time
  (`godot-export linux|web|windows|all`); the web build uses the Compatibility renderer (check its look).

**Performance (games):** measure frame time on the GPU the monitor is on (run Godot with `--gpu-index <display>`,
or `studio-play`, which picks it); `studio godot-play` runs on the Godot jobs' GPU (the RTX 2060 here), where every
frame is copied to the display GPU: DontPanicIsland measured 25 fps there and 60 fps locked on the display GPU (F43).
Break a slow frame down before optimising: script time, render-thread CPU, GPU (`tests/perf.gd` in DontPanicIsland).

## 7. Shutdown checklist (long days end with a power-off)
1. Before the deadline, `touch $STUDIO_EVAL_HOME/runs/PAUSE` (suites) or stop drivers between steps (they resume from
   their state/ledger); never kill a worker mid-run unless its result would be thrown away anyway.
2. Background tasks: every wait loop must also exit when the process it watches is gone; prefer one-shot waiters
   over 30-minute Monitors. At the end, list your background tasks and stop every leftover (TaskStop).
3. Commit both repos, update HANDOFF.md (state + next queue) and memory, remove PAUSE if tomorrow should resume.
4. `systemctl --user stop studio-broker llama-swap`; check nvidia-smi shows both GPUs empty.

## 8. Finish
Deliver: the file path(s), a frame or two (Read them yourself first), how to rebuild/re-render, and the ledger summary:
`studio-ledger <project> summary`. Report what was local vs Claude and any step types that should be re-routed.
