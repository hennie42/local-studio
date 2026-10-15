extends Node
## Studio automation helper (autoload "GameEvent"). Reads game args given after `--`:
##   --autopilot        the game plays itself (check GameEvent.autopilot in your scripts)
##   --shots[=DIR]      GameEvent.shot("name") saves PNG screenshots (default DIR: shots/ next to the project/exe)
##   --quit-after=SECS  quit after SECS seconds (smoke tests)
## Markers: GameEvent.marker("FINISH", "t=12.3") prints "GAME_FINISH t=12.3" (stdout, also in exported builds).

var autopilot := false
var shots_dir := ""


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


func marker(name: String, data: String = "") -> void:
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
