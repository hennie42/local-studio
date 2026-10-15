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

## Testing non-linear games

The studio's autopilot (`godot/cookbook/autopilot_pattern.gd`) plays a game **once, start to finish**, logging
`GAME_` markers. That fits a level you can walk left to right. It doesn't fit branches, several endings, free
exploration or emergent systems: there is no single route to script, and a hand-scripted route breaks whenever the
layout changes. For those games the autopilot becomes a set of tests instead of one run.

**Status:** this is the design. `GameEvent` today knows only `--autopilot`; scenarios, the objective bot and the
explorer come as tested cookbook recipes with the first non-linear game (planned: the Godot pilot,
[workflow](workflow.md)).

| layer | what it checks | how | runs |
|---|---|---|---|
| 1. Logic tests | quest state, inventory, flags, win/lose rules | plain classes (no scene), tested headless like the race-logic eval task | every edit, seconds |
| 2. Reachability | every ending can be reached, no softlocks | the quest/level graph as data (`data/progression.json`: nodes, gates, unlocks); a test walks it | every edit, seconds |
| 3. Scenario autopilots | each route that matters really plays | `--autopilot --scenario <name>`: start from a fixture, an objective bot plays to the scenario's expected markers | per ticket, headless |
| 4. Explorer | crashes and stuck states no route visits | seeded random play for N seconds, checking invariants, not completion | per milestone |
| 5. Coverage | nothing is untested | markers from all scenarios together must include every branch and ending | per milestone |

**Scenarios.** One per route that matters: each ending, skipping the optional content, dying at the hard part,
sequence breaks the design allows. A scenario starts from a **fixture** (a saved state, or a teleport + flags) so it
tests its part in seconds instead of replaying the whole game. It lists its objectives and the markers it must log:

```gdscript
# scenarios.gd (sketch): name -> start fixture, objectives in order, markers the run must produce
const SCENARIOS := {
    "ending_a":   {"fixture": "before_gate", "goals": ["key_red", "door_red", "boss"], "expect": ["GAME_ENDING a"]},
    "skip_cave":  {"fixture": "start",       "goals": ["bridge", "village"],           "expect": ["GAME_VISIT village"]},
    "death_boss": {"fixture": "boss_room",   "goals": [],      "expect": ["GAME_DEATH", "GAME_RESPAWN boss_room"]},
}
```

**The objective bot** steers like a player would, through the same input path as a human (`autopilot_dir`,
`autopilot_input` in the player recipes). It plans with Godot's navigation instead of hand-made coordinates, so it
survives level changes, and it keeps the spatial maths out of the worker's hands, which is where local models are
weak:

```gdscript
# objective_bot.gd (sketch, top-down 2D: player.autopilot_input is a Vector2 direction): walk to each goal via
# the NavigationAgent2D, interact, next goal
func _physics_process(_delta: float) -> void:
    if goal_index >= goals.size():
        return
    agent.target_position = goal_node(goals[goal_index]).global_position
    if agent.is_navigation_finished():
        player.interact()
        GameEvent.marker("GOAL", goals[goal_index])
        goal_index += 1
    else:
        player.autopilot_input = player.global_position.direction_to(agent.get_next_path_position())
```

Platformers need jumps as well. The bot's navigation then carries "jump here" links (NavigationLink2D) or a small
lookahead: is there a gap or wall ahead, then jump, through the same jump buffer a human uses.

**The explorer** plays randomly with a fixed seed (logged, so a failure can be replayed) and checks invariants:
no `SCRIPT ERROR`, never stuck in place for more than 5 s while moving, never outside the level bounds, frame time
within budget. It doesn't try to win; it finds what scripted routes never touch.

**Markers** for non-linear games add `GAME_VISIT <room/branch>`, `GAME_ENDING <id>`, `GAME_DEATH`,
`GAME_SEED <n>`. The coverage check reads the logs of all scenarios and the explorer, and fails if a branch or an
ending never appears.

**In the plan:** the `/grill-me` interview settles the branch structure (endings, gates, optional content), so the
scenario list comes straight from `BRIEF.md`; each scenario is the acceptance check of the tickets that build its
route.

## Notes
- The output resolution is fixed by the project (1920x1080 viewport, stretch mode `viewport`), independent of the
  window size: tiling window managers can't change Movie Maker output.
- Web exports use the Compatibility renderer (no volumetric fog, SDFGI or SSR).
- Generators: nodes need `owner = root` to be saved into a scene; `look_at()` needs the node in the tree, so
  generators use `Transform3D.looking_at()`.
