extends Node3D
## Placeholder main scene: replace with the real game/clip. Shows the GameEvent conventions.

func _ready() -> void:
	var cam := Camera3D.new()
	cam.position = Vector3(0, 2, 6)
	add_child(cam)
	cam.look_at(Vector3.ZERO)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	add_child(sun)
	var box := MeshInstance3D.new()
	box.mesh = BoxMesh.new()
	add_child(box)
	GameEvent.marker("READY")
	if GameEvent.autopilot:
		await get_tree().create_timer(1.0).timeout
		await GameEvent.shot("main")
		GameEvent.marker("FINISH", "t=1.0")
		GameEvent.quit(0)
