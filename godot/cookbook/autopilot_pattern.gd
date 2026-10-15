extends Node
## Recipe: the studio test pattern for games. GameEvent (autoload in the template) gives:
##   GameEvent.autopilot        true when run with `-- --autopilot`
##   GameEvent.marker(name, s)  prints GAME_<NAME> s (stdout, also in exported builds) -> the test log
##   await GameEvent.shot(n)    PNG screenshot when run with --shots
##   GameEvent.quit()           end the run
## Shape: same game code for human and autopilot; the autopilot only replaces the input source.

var progress := 0
var goal := 3
var t := 0.0


func _process(delta: float) -> void:
	t += delta


func step_autopilot() -> void:   # call once per decision; a real game steers the player here
	progress += 1
	GameEvent.marker("CHECKPOINT", "%d/%d t=%.2f" % [progress, goal, t])
	if progress >= goal:
		GameEvent.marker("FINISH", "t=%.2f" % t)
		# GameEvent.quit()   # a real game quits here (a self-test must not)


func run_selftest() -> String:
	if not Engine.has_singleton("GameEvent") and get_tree().root.get_node_or_null("GameEvent") == null:
		return "GameEvent autoload missing"
	for i in goal:
		step_autopilot()
	return "" if progress == goal else "progress %d" % progress
