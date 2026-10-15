extends Node2D
## Recipe: timed spawning with a Timer node and a PackedScene (preload("res://scenes/enemy.tscn") in a real game).
## instantiate() (not instance()); keep a cap; free with queue_free(); Timer: wait_time, one_shot, timeout signal.

@export var max_alive := 3
var scene: PackedScene
var spawned := 0
var timer: Timer


func _ready() -> void:
	timer = Timer.new()
	timer.wait_time = 0.02
	timer.one_shot = false
	timer.timeout.connect(_spawn)
	add_child(timer)


func _spawn() -> void:
	if get_tree().get_nodes_in_group("enemies").size() >= max_alive:
		return
	var e := scene.instantiate() as Node2D
	e.position = Vector2(randf_range(0, 100), randf_range(0, 100))
	e.add_to_group("enemies")
	add_child(e)
	spawned += 1


func run_selftest() -> String:
	var proto := Node2D.new()
	scene = PackedScene.new()
	scene.pack(proto)
	proto.free()
	timer.start()
	await get_tree().create_timer(0.3).timeout
	timer.stop()
	var alive := get_tree().get_nodes_in_group("enemies").size()
	if alive != max_alive:
		return "alive %d, expected cap %d" % [alive, max_alive]
	for e in get_tree().get_nodes_in_group("enemies"):
		e.queue_free()
	await get_tree().process_frame
	return "" if get_tree().get_nodes_in_group("enemies").is_empty() else "not freed"
