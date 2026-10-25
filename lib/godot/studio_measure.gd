extends SceneTree
## Studio asset library: measures models as the game sees them (written for `studio-assets check`, F17).
## Instances each scene, then merges the AABBs of its MeshInstance3Ds in the scene root's space. Blender's measure
## reads the file; this one also catches importer changes and what an "origin: keep" item really does in the game.
## Usage: godot --headless --path PROJECT -s studio_measure.gd -- IN.json OUT.json
## IN.json: ["res://...glb", ...]; OUT.json: {res_path: {dims_m, origin_offset_m, meshes} | {error}}
## origin_offset_m: the bottom centre of the bounds minus the scene origin, in Godot axes (y up), unscaled.


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var paths = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var out := {}
	for p in paths:
		out[p] = _measure(p)
	var f := FileAccess.open(args[1], FileAccess.WRITE)
	if f == null:
		push_error("studio_measure: can't write %s (%s)" % [args[1], error_string(FileAccess.get_open_error())])
		quit(1)
		return
	f.store_string(JSON.stringify(out))
	f.close()
	quit()


func _measure(path: String) -> Dictionary:
	var res = load(path)
	if not res is PackedScene:
		return {"error": "not loadable as a scene (imported?)"}
	var scene: Node = res.instantiate()   # not added to the tree: _init runs before the root enters it
	var box := AABB()
	var meshes := 0
	for mi in scene.find_children("*", "MeshInstance3D", true, false):
		if mi.mesh == null:
			continue
		var b: AABB = _to_scene(mi, scene) * mi.get_aabb()
		box = b if meshes == 0 else box.merge(b)
		meshes += 1
	scene.free()
	if meshes == 0:
		return {"error": "no meshes"}
	var c := box.get_center()
	return {"dims_m": [_r(box.size.x), _r(box.size.y), _r(box.size.z)],
			"origin_offset_m": [_r(c.x), _r(box.position.y), _r(c.z)], "meshes": meshes}


func _to_scene(node: Node, scene: Node) -> Transform3D:
	var t := Transform3D.IDENTITY
	while node != scene:
		if node is Node3D:
			t = node.transform * t
		node = node.get_parent()
	return t


func _r(v: float) -> float:
	return snappedf(v, 0.0001)
