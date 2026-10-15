extends SceneTree
# Compile every project script with autoloads registered; report failures as CHECK lines.
func _init() -> void:
	await process_frame
	var bad := 0
	var files := _scan("res://")
	for f in files:
		var s: GDScript = ResourceLoader.load(f, "GDScript", ResourceLoader.CACHE_MODE_IGNORE)
		var ok := s != null and s.can_instantiate()  # loading compiles; reload() refuses scripts with live instances (autoloads)
		if not ok:
			bad += 1
			print("GODOT_CHECK FAIL ", f)
	print("GODOT_CHECK %d script(s), %d failed" % [files.size(), bad])
	quit(1 if bad else 0)

func _scan(dir: String) -> PackedStringArray:
	var out := PackedStringArray()
	for d in DirAccess.get_directories_at(dir):
		if d.begins_with(".") or d in ["godot-api", "godot-ref", "build", "Renders", "addons", "out", "shots"]:
			continue
		out.append_array(_scan(dir.path_join(d)))
	for f in DirAccess.get_files_at(dir):
		if f.ends_with(".gd"):
			out.append(dir.path_join(f))
	return out
