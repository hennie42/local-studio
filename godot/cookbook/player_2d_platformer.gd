extends CharacterBody2D
## Recipe: 2D platformer controller (Godot 4): gravity, run, jump with coyote time and jump buffer,
## variable jump height. Movement ALWAYS in _physics_process; set `velocity`, then call move_and_slide() (no args).
## Needs a CollisionShape2D child (added in code below if missing) and actions from input_actions.gd.

@export var speed := 300.0
@export var jump_velocity := -520.0
@export var gravity := 1400.0
@export var coyote_time := 0.1      ## seconds after leaving a ledge during which a jump still works
@export var jump_buffer := 0.12     ## a jump pressed this long before landing still triggers
var autopilot_dir := 0.0            ## set by an autopilot instead of reading input (e.g. GameEvent.autopilot)
var _coyote := 0.0
var _buffer := 0.0


func _ready() -> void:
	if get_children().filter(func(c): return c is CollisionShape2D).is_empty():
		var shape := CollisionShape2D.new()
		var rect := RectangleShape2D.new()
		rect.size = Vector2(24, 40)
		shape.shape = rect
		add_child(shape)


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y += gravity * delta
		_coyote -= delta
	else:
		_coyote = coyote_time
	_buffer -= delta
	if InputMap.has_action("jump") and Input.is_action_just_pressed("jump"):
		_buffer = jump_buffer
	if _buffer > 0.0 and _coyote > 0.0:
		velocity.y = jump_velocity
		_buffer = 0.0
		_coyote = 0.0
	if InputMap.has_action("jump") and Input.is_action_just_released("jump") and velocity.y < 0.0:
		velocity.y *= 0.5  # short hop when the button is released early
	var dir := autopilot_dir
	if dir == 0.0 and InputMap.has_action("move_left"):
		dir = Input.get_axis("move_left", "move_right")
	velocity.x = dir * speed
	move_and_slide()


func jump() -> void:
	_buffer = jump_buffer  # for autopilots: same path as the button


func run_selftest() -> String:
	var floor_body := StaticBody2D.new()
	var fs := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(2000, 40)
	fs.shape = rect
	floor_body.add_child(fs)
	floor_body.position = Vector2(0, 520)
	get_parent().add_child(floor_body)
	position = Vector2(0, 450)
	for i in 60:
		await get_tree().physics_frame
	if not is_on_floor():
		floor_body.queue_free()
		return "did not land (y=%.1f)" % position.y
	var x0 := position.x
	autopilot_dir = 1.0
	jump()
	var peak := position.y
	for i in 30:
		await get_tree().physics_frame
		peak = minf(peak, position.y)
	floor_body.queue_free()
	if position.x - x0 < 100.0:
		return "did not run right (dx=%.1f)" % (position.x - x0)
	return "" if peak < 450.0 else "did not jump (peak y=%.1f)" % peak
