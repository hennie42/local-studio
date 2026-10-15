# Godot

Godot 4 is the default engine for games (2D and simple 3D), anything that should run in a browser, and stylised
clips. GDScript reloads instantly and can be checked headless, which suits sandboxed workers.

## Setup and updates
`install.sh` runs `godot-refresh install latest --activate`: it downloads the official build and export templates
(checksums verified), builds the **reference bundle** for that exact version and validates it before switching:
- `api/`: the class reference, generated from the engine's own docs (one text file per class, signatures + one-line
  descriptions; `INDEX.txt` lists all classes);
- `docs/`: the official manual (getting started + tutorials), GDScript only;
- `demos/`: the official demo projects (scripts and scenes);
- `cookbook/`: verified recipes from `godot/cookbook/`: input actions, 2D/3D controllers, signals/await, tweens, scene
  generators, save/load, HUD, triggers, spawners, state machines, clip cameras, a night/neon look, audio, the
  autopilot pattern. Each compiles cleanly and passes its own self-test on that engine version.

`godot-refresh.timer` checks weekly: patch releases (4.7.2 -> 4.7.3) are installed, validated (cookbook self-tests,
template project check, export + headless autopilot run) and activated automatically; a new minor (4.8) is installed
and validated, then reported; you switch with `godot-refresh activate 4.8.0`. Projects pin their minor version
(`project.godot` features), and the broker always runs a project on the newest installed engine of its own minor.

## Worker tools (broker actions)
| action | what | GPU |
|---|---|---|
| `studio godot-check` | Godot 3 idiom lint (every hit with file:line and the fix) + full compile of every script with autoloads | no |
| `studio godot-script tools/x.gd` | headless SceneTree script: scene generators, data | no |
| `studio godot-play scenes/main.tscn 30 --headless --autopilot` | run the game logic headless (seconds) | no |
| `studio godot-play scenes/main.tscn 30 --autopilot --shots` | run windowed, screenshots to `shots/` | yes |
| `studio godot-movie scenes/clip.tscn Renders/clip 300 30` | Movie Maker: deterministic frames (+ wav) | yes |
| `studio godot-export linux\|web\|windows\|all` | exports, target chosen at export time | no |
| `studio run-export 60 --headless --autopilot` | run the exported Linux build | optional |

The project template has a `GameEvent` autoload: `GameEvent.marker("FINISH", "t=12.3")` prints `GAME_FINISH t=12.3`
(also in exported builds), `GameEvent.autopilot`, `GameEvent.shot("name")`. Every game gets an autopilot that plays
it to the end: it is the end-to-end test of a packaged build.

## Notes
- The output resolution is fixed by the project (1920x1080 viewport, stretch mode `viewport`), independent of the
  window size: tiling window managers can't change Movie Maker output.
- Web exports use the Compatibility renderer (no volumetric fog, SDFGI or SSR).
- Generators: nodes need `owner = root` to be saved into a scene; `look_at()` needs the node in the tree, so
  generators use `Transform3D.looking_at()`.
