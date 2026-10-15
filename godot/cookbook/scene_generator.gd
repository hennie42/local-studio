extends RefCounted
## Recipe: build a scene in code and save it as .tscn (run as a generator: `studio godot-script tools/build_x.gd`
## with `extends SceneTree` and this code in _init()). Rules: every node that should be saved needs
## `node.owner = root` (set AFTER add_child, for all descendants); pack(root) then ResourceSaver.save().
## look_at() needs the node inside the tree: in generators use Transform3D(...).looking_at(target, Vector3.UP).


static func build_level() -> Node3D:
	var root := Node3D.new()
	root.name = "Level"
	var cam := Camera3D.new()
	cam.name = "Cam"
	cam.transform = Transform3D(Basis(), Vector3(0, 3, 8)).looking_at(Vector3.ZERO, Vector3.UP)
	_add(root, root, cam)
	var light := DirectionalLight3D.new()
	light.name = "Sun"
	light.rotation_degrees = Vector3(-50, 30, 0)
	_add(root, root, light)
	var body := StaticBody3D.new()
	body.name = "Floor"
	_add(root, root, body)
	var mesh := MeshInstance3D.new()
	mesh.name = "Mesh"
	var plane := PlaneMesh.new()
	plane.size = Vector2(20, 20)
	mesh.mesh = plane
	_add(root, body, mesh)            # grandchild: owner must still be the scene root
	var shape := CollisionShape3D.new()
	shape.name = "Shape"
	var box := BoxShape3D.new()
	box.size = Vector3(20, 0.2, 20)
	shape.shape = box
	_add(root, body, shape)
	return root


static func _add(scene_root: Node, parent: Node, child: Node) -> void:
	parent.add_child(child)
	child.owner = scene_root


static func save_scene(root: Node, path: String) -> Error:
	var packed := PackedScene.new()
	var err := packed.pack(root)
	if err != OK:
		return err
	return ResourceSaver.save(packed, path)


func run_selftest() -> String:
	var root := build_level()
	var path := "user://cookbook_level.tscn"
	var err := save_scene(root, path)
	root.free()
	if err != OK:
		return "save error %d" % err
	var inst := (load(path) as PackedScene).instantiate()
	var ok := inst.has_node("Cam") and inst.has_node("Floor/Mesh") and inst.has_node("Floor/Shape")
	var cam_pos: Vector3 = inst.get_node("Cam").position
	inst.free()
	if not ok:
		return "saved scene lost nodes (owner not set?)"
	return "" if cam_pos.is_equal_approx(Vector3(0, 3, 8)) else "camera at %s" % cam_pos
