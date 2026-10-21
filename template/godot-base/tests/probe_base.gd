class_name ProbeBase
extends Node
## Base for probe scenes: start the real game, drive it with real input events in window coordinates (as a player
## does) and assert what happens. The autopilot calls the game logic directly and never meets the interface, so
## anything a player sees or touches needs a probe (retros/DontPanicIsland). Subclasses implement run() and print
## "<NAME> OK" when fails == 0. A probe scene is a Node with the subclass script.
## Run: tools/probe.sh tests/<probe>.tscn SECONDS "<NAME> OK" [game flags]

## The marker that means "ready for input": wait for it, never for a fixed time (a fixed wait was flaky).
var ready_marker := "READY"
var main: Node
var fails := 0


func check(ok: bool, what: String) -> void:
	print(("ok   " if ok else "FAIL ") + what)
	if not ok:
		fails += 1


func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	var waited := 0.0
	while waited < 60.0 and not GameEvent.seen.has(ready_marker):
		await wait(0.25)
		waited += 0.25
	check(GameEvent.seen.has(ready_marker), "the game reported %s" % ready_marker)
	await wait(0.5)
	await run()
	get_tree().quit()


func run() -> void:
	pass


func wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout


func frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


## Viewport coordinates -> window coordinates (what the OS sends): with a stretched viewport they differ.
func win(pos: Vector2) -> Vector2:
	return get_viewport().get_screen_transform() * pos


## A 3D point's position on screen (viewport coordinates).
func screen_of(point: Vector3) -> Vector2:
	return get_viewport().get_camera_3d().unproject_position(point)


func click(pos: Vector2, button: MouseButton = MOUSE_BUTTON_LEFT) -> void:
	for pressed in [true, false]:
		var ev := InputEventMouseButton.new()
		ev.button_index = button
		ev.pressed = pressed
		ev.position = win(pos)
		ev.global_position = ev.position
		Input.parse_input_event(ev)
		await frames(1)
	await frames(2)


func tap(pos: Vector2, hold_seconds: float = 0.0) -> void:
	var ev := InputEventScreenTouch.new()
	ev.index = 0
	ev.pressed = true
	ev.position = win(pos)
	Input.parse_input_event(ev)
	if hold_seconds > 0.0:
		await wait(hold_seconds)
	else:
		await frames(2)
	var up := ev.duplicate() as InputEventScreenTouch
	up.pressed = false
	Input.parse_input_event(up)
	await frames(2)


## A screenshot of what the player sees (the viewport texture: Movie Maker crops tall windows).
func shot(path: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(path)
