extends Node
## Recipe: signals and coroutines in Godot 4.
## Declare: `signal hit(amount: int)`; emit: `hit.emit(3)`; connect a Callable: `hit.connect(_on_hit)`;
## extra args: `.bind(x)`; one-shot: `hit.connect(f, CONNECT_ONE_SHOT)`; disconnect: `hit.disconnect(_on_hit)`.
## Wait: `await get_tree().create_timer(0.5).timeout`, `await some_node.some_signal`, `await get_tree().process_frame`.
## (Godot 3's yield(), connect("sig", self, "method") and emit_signal("sig") strings are gone or discouraged.)

signal hit(amount: int)
signal done(result: String)

var total := 0
var tagged: Array[String] = []


func _on_hit(amount: int) -> void:
	total += amount


func _on_hit_tagged(amount: int, tag: String) -> void:
	tagged.append("%s:%d" % [tag, amount])


func slow_job() -> String:
	await get_tree().create_timer(0.05).timeout  # a coroutine: callers `await slow_job()`
	done.emit("finished")
	return "ok"


func run_selftest() -> String:
	hit.connect(_on_hit)
	hit.connect(_on_hit_tagged.bind("A"))
	hit.connect(func(a: int) -> void: total += a * 100, CONNECT_ONE_SHOT)  # lambda, fires once
	hit.emit(2)
	hit.emit(3)
	if total != 2 + 3 + 200:
		return "total %d" % total
	if tagged != ["A:2", "A:3"]:
		return "tagged %s" % tagged
	hit.disconnect(_on_hit)
	hit.emit(5)
	if total != 205:
		return "disconnect failed (%d)" % total
	var r: String = await slow_job()
	return "" if r == "ok" else "slow_job returned " + r
