extends Node
## Recipe: a small enum state machine (game flow: ready -> countdown -> racing -> finished).
## One place changes state (set_state) so enter/exit logic never gets skipped; `match` on the enum.

signal state_changed(from: State, to: State)

enum State { READY, COUNTDOWN, RACING, FINISHED }
var state := State.READY
var elapsed := 0.0
var log_lines: Array[String] = []


func set_state(next: State) -> void:
	if next == state:
		return
	_exit(state)
	var prev := state
	state = next
	elapsed = 0.0
	_enter(next)
	state_changed.emit(prev, next)


func _enter(s: State) -> void:
	log_lines.append("enter " + State.keys()[s])


func _exit(s: State) -> void:
	log_lines.append("exit " + State.keys()[s])


func update(delta: float) -> void:  # call from _process / _physics_process
	elapsed += delta
	match state:
		State.COUNTDOWN:
			if elapsed >= 3.0:
				set_state(State.RACING)
		State.RACING:
			pass  # race logic here
		_:
			pass


func run_selftest() -> String:
	set_state(State.COUNTDOWN)
	for i in 31:
		update(0.1)
	if state != State.RACING:
		return "state %s" % State.keys()[state]
	set_state(State.FINISHED)
	var want: Array[String] = ["exit READY", "enter COUNTDOWN", "exit COUNTDOWN", "enter RACING", "exit RACING", "enter FINISHED"]
	return "" if log_lines == want else "log %s" % log_lines
