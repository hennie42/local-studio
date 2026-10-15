# Godot cookbook (verified recipes)

Every recipe is a complete Godot 4 script that compiles without Godot 3 idioms and passes its own
`run_selftest()` headless on the engine version of this bundle (`godot-cookbook-test`; godot-refresh re-runs it
for every new release). Copy the patterns, not necessarily whole files. Read the `##` comment at the top first.

| recipe | shows |
|---|---|
| input_actions.gd | input actions in code: keyboard (physical keys) + gamepad buttons/sticks; Input.get_axis/get_vector |
| player_2d_platformer.gd | CharacterBody2D: gravity, run, jump with coyote time + jump buffer + short hop; autopilot hook |
| player_3d_controller.gd | CharacterBody3D: camera-relative movement, gravity, jump, turn to face movement |
| signals_and_await.gd | typed signals, emit, connect Callables, bind, one-shot lambdas, disconnect, await timers/signals/coroutines |
| tweens.gd | create_tween: property/sub-property, parallel, transitions, method/callback/interval, await finished |
| scene_generator.gd | build a node tree in code, owner rules, pack + ResourceSaver.save, Transform3D.looking_at in generators |
| save_load.gd | user:// persistence: ConfigFile (settings/best times), JSON with FileAccess, error handling |
| hud_ui.gd | CanvasLayer HUD in code: MarginContainer, anchor presets, font size/colour/outline overrides, timer text |
| triggers_areas_groups.gd | Area2D triggers, collision layers vs masks, groups, safe queue_free in physics callbacks |
| spawner_timer.gd | Timer node, PackedScene.instantiate(), spawn cap, cleanup |
| state_machine.gd | enum state machine with enter/exit hooks, match, state_changed signal |
| movie_camera.gd | deterministic clip cameras: orbit transform from time, Path3D + PathFollow3D, smoothstep easing |
| night_environment.gd | night/neon look: AgX tonemap, glow, volumetric fog, SSR wet floor, emissive neon, fog-lit lights |
| audio_players.gd | AudioStreamPlayer one-shots, generated AudioStreamWAV tones, volume/pitch |
| autopilot_pattern.gd | the studio test pattern: GameEvent.autopilot, GAME_ markers, shots, quit |
