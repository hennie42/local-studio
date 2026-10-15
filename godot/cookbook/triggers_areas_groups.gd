extends Node2D
## Recipe: triggers. Area2D/3D emit body_entered/area_entered when a PhysicsBody (or Area) overlaps.
## Collision LAYER = what I am, MASK = what I detect: the area's mask must include the body's layer.
## Groups tag nodes: add_to_group("player"); body.is_in_group("player"); get_tree().get_nodes_in_group("coins").
## Overlaps are computed in physics frames: await get_tree().physics_frame before get_overlapping_bodies().

const LAYER_PLAYER := 1 << 1   # layer 2
const LAYER_PICKUP := 1 << 2   # layer 3
var picked: Array[String] = []


func make_pickup(pos: Vector2, id: String) -> Area2D:
	var a := Area2D.new()
	a.position = pos
	a.collision_layer = LAYER_PICKUP
	a.collision_mask = LAYER_PLAYER          # only the player triggers it
	a.monitoring = true
	var s := CollisionShape2D.new()
	var c := CircleShape2D.new()
	c.radius = 16.0
	s.shape = c
	a.add_child(s)
	a.add_to_group("pickups")
	a.body_entered.connect(_on_pickup.bind(a, id))
	add_child(a)
	return a


func _on_pickup(body: Node2D, area: Area2D, id: String) -> void:
	if body.is_in_group("player"):
		picked.append(id)
		area.queue_free()   # never free physics objects during the callback with free(); queue_free is safe


func run_selftest() -> String:
	make_pickup(Vector2(100, 0), "coin_a")
	make_pickup(Vector2(400, 0), "coin_b")
	var player := CharacterBody2D.new()
	player.collision_layer = LAYER_PLAYER
	player.collision_mask = 1
	var s := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = Vector2(20, 20)
	s.shape = r
	player.add_child(s)
	player.add_to_group("player")
	player.position = Vector2(0, 0)
	add_child(player)
	for i in 30:
		player.velocity = Vector2(800, 0)
		player.move_and_slide()
		await get_tree().physics_frame
	if picked != ["coin_a", "coin_b"]:
		return "picked %s at x=%.0f" % [picked, player.position.x]
	await get_tree().process_frame
	return "" if get_tree().get_nodes_in_group("pickups").is_empty() else "pickups not freed"
