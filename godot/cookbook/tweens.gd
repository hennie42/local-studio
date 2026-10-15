extends Node2D
## Recipe: tweens (Godot 4 has no Tween node: create one with create_tween(); it starts automatically).
## Sequence by default; .parallel() / set_parallel(true) for simultaneous; set_trans/set_ease for curves;
## tween_property(obj, "prop", final, seconds), tween_method(callable, from, to, s), tween_callback(c),
## tween_interval(s); .set_loops(n); `await tween.finished`. A node's tweens die with the node.

var value := 0.0


func run_selftest() -> String:
	position = Vector2.ZERO
	var t := create_tween()
	t.tween_property(self, "position", Vector2(100, 0), 0.1).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	t.parallel().tween_property(self, "modulate:a", 0.0, 0.1)  # sub-property path with ':'
	t.tween_interval(0.02)
	t.tween_method(func(v: float) -> void: value = v, 0.0, 1.0, 0.05)
	var called := [false]
	t.tween_callback(func() -> void: called[0] = true)
	await t.finished
	if not position.is_equal_approx(Vector2(100, 0)):
		return "position %s" % position
	if not is_equal_approx(modulate.a, 0.0):
		return "alpha %s" % modulate.a
	if not is_equal_approx(value, 1.0) or not called[0]:
		return "method/callback %s %s" % [value, called[0]]
	return ""
