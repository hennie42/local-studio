@tool
extends EditorScenePostImport
## Studio asset library: adds collisions to imported models (written by `studio-assets check`).
## res://assets/collision.json maps each model's res:// path to "box", "convex" or "none" (decorative items).
## Every MeshInstance3D gets a StaticBody3D child with one CollisionShape3D; models not in the map get "convex".

const MAP_PATH := "res://assets/collision.json"


func _post_import(scene: Node) -> Object:
	var mode := "convex"
	if FileAccess.file_exists(MAP_PATH):
		var data = JSON.parse_string(FileAccess.get_file_as_string(MAP_PATH))
		if data is Dictionary and data.has(get_source_file()):
			mode = data[get_source_file()]
	if mode == "none":
		return scene
	_add_collisions(scene, scene, mode)
	return scene


func _add_collisions(node: Node, owner_root: Node, mode: String) -> void:
	for child in node.get_children():
		_add_collisions(child, owner_root, mode)
	if not node is MeshInstance3D or node.mesh == null:
		return
	var shape: Shape3D
	if mode == "box":
		var box := BoxShape3D.new()
		var aabb: AABB = node.mesh.get_aabb()
		box.size = aabb.size
		shape = box
	else:
		shape = node.mesh.create_convex_shape(true, true)
	if shape == null:
		return
	var body := StaticBody3D.new()
	body.name = "Collision"
	var col := CollisionShape3D.new()
	col.shape = shape
	if mode == "box":
		col.position = node.mesh.get_aabb().get_center()
	body.add_child(col)
	node.add_child(body)
	body.owner = owner_root
	col.owner = owner_root
