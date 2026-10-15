# Studio project guide: Godot 4.7 (read this first)

You are working in a sandboxed Godot project directory. You can read/write files and run ordinary commands here
(python3, git, ffmpeg with CPU codecs). **Never write outputs or test results to /tmp**: it is private to your
sandbox and discarded; use the project (`Renders/`, `out/`, `shots/`). You CANNOT run Godot, Blender or GPU tools
directly; ask the studio broker with the `studio` command. `studio help` lists the actions. Every job writes its
full log to `.studio/logs/` and prints a filtered summary (errors, `GAME_` markers, script output).

| Need | Command |
|---|---|
| Check all scripts (Godot 3 idioms + Godot's own parser) | `studio godot-check` |
| Run a headless generator script (no window, no GPU) | `studio godot-script tools/build_x.gd [--flag --key=value]` |
| Import new assets (after adding .glb/.png/.wav) | `studio godot-import` |
| Run the game logic fast, no window/GPU (seconds) | `studio godot-play scenes/main.tscn 30 --headless --autopilot` |
| Run the game windowed + screenshots (to look at it) | `studio godot-play scenes/main.tscn 30 --autopilot --shots` |
| Render frames with Movie Maker (GPU) | `studio godot-movie scenes/clip.tscn Renders/clip 300 30` |
| Export | `studio godot-export linux` (or `web`, `windows`, `all`) -> `build/<platform>/` |
| Run the Linux export | `studio run-export 60 --headless --autopilot` (or without --headless) |
| Blender script (models -> assets/*.glb) | `studio blender tools/make_x.py [-- args]` |
| PNG frames -> video | `studio encode Renders/clip 30 out/clip.mp4` |

## Godot 4, not Godot 3: look things up, don't trust memory
Your training data is full of Godot 3 code that does NOT work in Godot 4.7. `godot-ref/` (read `godot-ref/INDEX.md`)
matches the installed engine exactly; search it with grep before writing code:
- `godot-ref/cookbook/`: **verified recipes** (each compiles and passes a self-test on this engine): input actions,
  2D/3D character controllers, signals/await, tweens, scene generators, save/load, HUD, triggers, spawners, state
  machines, clip cameras, night/neon look, audio, the autopilot pattern. Start here; `README.md` lists them.
- `godot-ref/api/`: the class reference: `INDEX.txt` (one line per class), `<Class>.txt` (properties, methods with
  signatures, signals, constants). E.g. `grep -n "move_and_slide\|velocity" godot-ref/api/CharacterBody2D.txt`.
- `godot-ref/demos/`: the official demo projects (scripts + scenes): `grep -rln "Area2D" godot-ref/demos | head`.
- `godot-ref/docs/`: the official manual, GDScript only: `grep -rn "Movie Maker" godot-ref/docs | head`.
Run `studio godot-check` after every edit; it lists every Godot 3 idiom with file:line and the fix, then runs
Godot's parser on each script. Fix everything it reports before running the game.

| Godot 3 (wrong) | Godot 4.7 (right) |
|---|---|
| `export var speed = 5` / `onready var x = $X` / `tool` | `@export var speed := 5.0` / `@onready var x := $X` / `@tool` |
| `yield(get_tree().create_timer(1), "timeout")` | `await get_tree().create_timer(1.0).timeout` |
| `connect("pressed", self, "_on_pressed")`, `emit_signal("hit", 3)` | `pressed.connect(_on_pressed)`, `hit.emit(3)` |
| `KinematicBody2D`, `move_and_slide(velocity, Vector2.UP)` | `CharacterBody2D`: set `velocity`, then `move_and_slide()` (no args) |
| `Spatial`, `KinematicBody`, `Position3D`, `Sprite` | `Node3D`, `CharacterBody3D`, `Marker3D`, `Sprite2D` |
| `scene.instance()`, `Tween.new()`, `File.new()` | `scene.instantiate()`, `create_tween()`, `FileAccess.open(...)` |
| `rand_range`, `deg2rad`, `stepify`, `.empty()` | `randf_range`, `deg_to_rad`, `snapped`, `.is_empty()` |
| `setget`, `OS.get_ticks_msec()`, `TileMap` | `var x: int: set = _set_x`, `Time.get_ticks_msec()`, `TileMapLayer` |

Use static types (`var hp: int = 3`, `:=`, typed function signatures): the parser then catches wrong method names
and argument types at `godot-check` time instead of at runtime.

## Project layout and conventions
- `project.godot`: renderer Forward+ (Compatibility on the web), viewport 1920x1080 with stretch mode `viewport`
  (deterministic output resolution for Movie Maker and screenshots; the window size doesn't matter).
- `scenes/` (.tscn), `scripts/` (.gd attached to scenes), `tools/` (generator scripts and Python helpers),
  `assets/` (glb, png), `audio/` (wav/ogg). Don't edit or commit `.godot/` (engine cache) or `godot-ref/` (generated reference).
- Autoload `GameEvent` (scripts/game_event.gd): `GameEvent.marker("FINISH", "t=12.3")` prints `GAME_FINISH t=12.3`
  (works in exported builds too); `GameEvent.autopilot` is true with `--autopilot`; `await GameEvent.shot("name")`
  saves a PNG when run with `--shots`; `GameEvent.quit()` ends the run. Game args go after `--` (the studio actions
  add it): read them with `OS.get_cmdline_user_args()`.

## Building scenes
Prefer **building node trees in code** (in `_ready()`) or with **generator scripts**; hand-writing .tscn text is
error-prone (resource ids, load_steps). A generator (`studio godot-script tools/build_level.gd`):
```gdscript
extends SceneTree
func _init() -> void:
    var root := Node3D.new(); root.name = "Level"
    var cam := Camera3D.new(); cam.name = "Cam"; root.add_child(cam)
    cam.owner = root                       # REQUIRED: nodes without owner are NOT saved into the scene
    cam.position = Vector3(0, 2, 6)
    var packed := PackedScene.new()
    var err := packed.pack(root)
    err = err if err != OK else ResourceSaver.save(packed, "res://scenes/level.tscn")
    print("GAME_BUILD level.tscn err=%d" % err)
    quit(0 if err == OK else 1)
```
`look_at()` only works on nodes inside the tree: in generators, set rotations with `Basis.looking_at()` /
`Transform3D.looking_at()` instead (`cam.transform = Transform3D(Basis(), pos).looking_at(target, Vector3.UP)`).
Scripts attached to scene nodes: `node.set_script(load("res://scripts/x.gd"))`.

## Games
- Movement in `_physics_process(delta)`; input via actions. Define input actions in code (an autoload or the main
  scene's `_ready`): `InputMap.add_action("jump")`, `var ev := InputEventKey.new(); ev.physical_keycode = KEY_SPACE;
  InputMap.action_add_event("jump", ev)` (gamepad: `InputEventJoypadButton` / `InputEventJoypadMotion`).
- Every game gets an **`--autopilot` mode** that plays itself to the end, logs `GAME_START`, progress markers,
  `GAME_FINISH ...` and quits (`GameEvent.quit()`). **Iterate with `--headless`** (`studio godot-play
  scenes/main.tscn 30 --headless --autopilot`): physics, signals and markers all run, it takes seconds and needs no
  GPU. Add a position marker while tuning (e.g. `GameEvent.marker("POS", "x=%.0f y=%.0f" % [...])` every 0.5 s) so
  the log shows where the autopilot gets stuck. Run windowed with `--shots` only to look at the result (screenshots
  in `shots/`). Non-linear games (branches, several endings, open areas): the plan names **scenarios** instead of
  one route; each starts from a fixture, steers with navigation (never hand-made coordinates) and must log its
  expected markers (`GAME_VISIT`, `GAME_ENDING`). Errors in the log: `SCRIPT ERROR`, `ERROR:`,
  `at: res://...:LINE`.
- Exports: presets Linux / Web / Windows exist in export_presets.cfg; pick at export time with
  `studio godot-export <linux|web|windows|all>`. The web build uses the Compatibility renderer (no SDFGI, no
  volumetric fog): if the web build matters, check it looks acceptable without those.

## Clips (Movie Maker)
- Animate deterministically from time: Movie Maker runs at a fixed fps, so `delta` is exactly 1/fps; use
  `_process(delta)` accumulators, `AnimationPlayer`, or tweens. Camera moves: `Path3D` + `PathFollow3D`
  (`progress_ratio`) or interpolate transforms by hand.
- `studio godot-movie scenes/clip.tscn Renders/clip <frames> 30` writes `Renders/clip/frame00000000.png ...` (and
  `frame.wav` if the scene plays audio). Look at a few frames with your file-reading tool, then
  `studio encode Renders/clip 30 out/clip.mp4`.
- Look: `WorldEnvironment` + `Environment` (`tonemap_mode = Environment.TONE_MAPPER_AGX` or ACES, `glow_enabled`,
  `volumetric_fog_enabled`, `sdfgi_enabled`, `ssr_enabled` for wet reflections), `DirectionalLight3D`/`OmniLight3D`
  /`SpotLight3D` (`light_energy`, `shadow_enabled`), `StandardMaterial3D` (`emission_enabled`, `emission_energy_multiplier`,
  `roughness`, `metallic`). Check names in godot-ref/api/ (e.g. `grep -n fog godot-ref/api/Environment.txt`); recipe:
  `godot-ref/cookbook/night_environment.gd` and `movie_camera.gd`.

## Blender and audio
Models: Blender Python (`studio blender tools/make_x.py`), export GLB into `assets/`, then `studio godot-import`
and `load("res://assets/x.glb").instantiate()`. Blender units = 1 m = 1 Godot unit; +Y up in Godot (glTF converts).
Audio: `tools/studio_audio.py` (numpy, 48 kHz synth: pads, bass, drums, risers, impacts, `Timeline` -> WAV); play in
Godot with `AudioStreamPlayer` (`stream = load("res://audio/x.wav")`), or mux into a clip with ffmpeg.
