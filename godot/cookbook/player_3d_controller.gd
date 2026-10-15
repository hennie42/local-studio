extends CharacterBody3D
## Recipe: 3D character controller: moves relative to the camera's yaw, gravity, jump, faces its movement.
## Input from input_actions.gd (move_left/right/up/down, jump). Godot 3D: +Y up, -Z forward, units = metres.

@export var speed := 6.0
@export var jump_velocity := 5.0
@export var turn_speed := 10.0
var camera_yaw := 0.0                 ## set from the camera rig (radians)
var autopilot_input := Vector2.ZERO   ## x = right, y = forward; used when non-zero
var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")


func _ready() -> void:
	if get_children().filter(func(c): return c is CollisionShape3D).is_empty():
		var s := CollisionShape3D.new()
		var cap := CapsuleShape3D.new()
		cap.radius = 0.4
		cap.height = 1.8
		s.shape = cap
		s.position.y = 0.9
		add_child(s)


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	elif InputMap.has_action("jump") and Input.is_action_just_pressed("jump"):
		velocity.y = jump_velocity
	var input := autopilot_input
	if input == Vector2.ZERO and InputMap.has_action("move_left"):
		input = Input.get_vector("move_left", "move_right", "move_down", "move_up")
	# camera-relative: forward is -Z rotated by the camera yaw
	var dir := (Basis(Vector3.UP, camera_yaw) * Vector3(input.x, 0.0, -input.y)).normalized()
	velocity.x = dir.x * speed
	velocity.z = dir.z * speed
	if dir.length() > 0.01:
		rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), clampf(turn_speed * delta, 0.0, 1.0))
	move_and_slide()


func run_selftest() -> String:
	var floor_body := StaticBody3D.new()
	var fs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(50, 1, 50)
	fs.shape = box
	floor_body.add_child(fs)
	floor_body.position.y = -0.5
	get_parent().add_child(floor_body)
	position = Vector3(0, 1, 0)
	for i in 40:
		await get_tree().physics_frame
	if not is_on_floor():
		floor_body.queue_free()
		return "did not land (y=%.2f)" % position.y
	autopilot_input = Vector2(0, 1)   # forward
	camera_yaw = 0.0
	for i in 30:
		await get_tree().physics_frame
	floor_body.queue_free()
	return "" if position.z < -2.0 else "did not move forward (z=%.2f)" % position.z
