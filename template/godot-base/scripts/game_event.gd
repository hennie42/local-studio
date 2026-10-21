extends Node
## Studio automation helper (autoload "GameEvent"). Reads game args given after `--`:
##   --autopilot        the game plays itself (check GameEvent.autopilot in your scripts)
##   --shots[=DIR]      GameEvent.shot("name") saves PNG screenshots (default DIR: shots/ next to the project/exe)
##   --quit-after=SECS  quit after SECS seconds (smoke tests)
##   --pixel-probe      2 s after boot, marker PIXEL with the average colour and variation mid-screen (renderers
##                      you can't see, e.g. a phone browser: a blank 3D view is one flat colour)
## On the web it checks the 3D view is drawn and otherwise tells the player to switch browsers (DuckDuckGo on a
## Pixel 10 drew no 3D at all). `seen` holds every marker so far: probes wait for state, not for a fixed time.
## Markers: GameEvent.marker("FINISH", "t=12.3") prints "GAME_FINISH t=12.3" (stdout, also in exported builds).

var autopilot := false
var shots_dir := ""
var seen: Dictionary = {}   # marker name -> its last data


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var args := OS.get_cmdline_user_args()
	autopilot = "--autopilot" in args
	for a in args:
		if a == "--shots":
			shots_dir = _base_dir().path_join("shots")
		elif a.begins_with("--shots="):
			shots_dir = a.substr(8)
			if shots_dir.is_relative_path():
				shots_dir = _base_dir().path_join(shots_dir)
		elif a.begins_with("--quit-after="):
			var secs := a.substr(13).to_float()
			get_tree().create_timer(secs, true, false, true).timeout.connect(func() -> void: quit(0))
	if shots_dir != "":
		DirAccess.make_dir_recursive_absolute(shots_dir)
		FileAccess.open(shots_dir.path_join(".gdignore"), FileAccess.WRITE)  # screenshots are not project assets
	marker("BOOT", "autopilot=%s shots=%s engine=%s" % [autopilot, shots_dir, Engine.get_version_info().string])
	if "--pixel-probe" in args or OS.has_feature("web"):
		_probe_view("--pixel-probe" in args)


## Average colour and variation in the middle of the screen; on the web, a message if nothing 3D was drawn.
func _probe_view(report: bool) -> void:
	await get_tree().create_timer(2.0, true, false, true).timeout
	if DisplayServer.get_name() == "headless":
		return
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var first := img.get_pixel(img.get_width() / 2, img.get_height() / 2)
	var c := Vector3.ZERO
	var spread := 0.0
	var n := 0
	for y in range(img.get_height() * 3 / 10, img.get_height() * 7 / 10, 12):
		for x in range(img.get_width() * 3 / 10, img.get_width() * 7 / 10, 12):
			var p := img.get_pixel(x, y)
			c += Vector3(p.r, p.g, p.b)
			spread += absf(p.r - first.r) + absf(p.g - first.g) + absf(p.b - first.b)
			n += 1
	c /= maxf(n, 1)
	var variation := spread / maxf(n, 1)
	if report:
		marker("PIXEL", "avg=%.2f,%.2f,%.2f variation=%.3f renderer=%s" % [c.x, c.y, c.z, variation,
			RenderingServer.get_current_rendering_method()])
	if OS.has_feature("web") and variation < 0.002 and get_tree().root.find_children("*", "Camera3D", true, false).size() > 0:
		marker("NO_3D", "the browser drew one flat colour")
		var layer := CanvasLayer.new()
		layer.layer = 100
		add_child(layer)
		var label := Label.new()
		label.text = "Your browser is blocking 3D graphics.\nPlease open this page in Firefox, Chrome or Vanadium."
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", 40)
		layer.add_child(label)
		label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		label.mouse_filter = Control.MOUSE_FILTER_IGNORE


func marker(name: String, data: String = "") -> void:
	seen[name] = data
	print("GAME_%s %s" % [name, data] if data != "" else "GAME_%s" % name)


func shot(name: String) -> void:
	if shots_dir == "":
		return
	if DisplayServer.get_name() == "headless":
		marker("SHOT", "%s skipped (headless run: no rendering)" % name)
		return
	await RenderingServer.frame_post_draw
	var path := shots_dir.path_join(name + ".png")
	var err := get_viewport().get_texture().get_image().save_png(path)
	marker("SHOT", "%s err=%d" % [path, err])


func quit(code: int = 0) -> void:
	marker("QUIT", "code=%d" % code)
	get_tree().quit(code)


func _base_dir() -> String:
	# running from the project folder (studio godot-play): the project; exported build: next to the executable
	if OS.has_feature("template"):
		return OS.get_executable_path().get_base_dir()
	return ProjectSettings.globalize_path("res://")
