"""Godot: implement a time-trial race state machine from a spec; graded by hidden headless unit tests."""
import _godot

AREA = "godot"
TITLE = "Godot: RaceLogic class (state machine, signals, medals, best time) vs hidden tests"
KIND = "agent"
TIMEOUT = 2400

PROMPT = """This is a Godot 4.7 project. Read AGENTS.md first. Write scripts/race_logic.gd: a pure-logic class
(no nodes, no scene tree) for a time-trial race, exactly as specified:

```
class_name RaceLogic extends RefCounted
signal countdown_tick(value: int)        # emitted for 3, 2, 1 as the countdown passes each whole second
signal race_started()
signal checkpoint_passed(index: int, time: float)
signal race_finished(time: float, medal: String)

var state: String          # "ready" | "countdown" | "racing" | "finished"
var race_time: float       # seconds since race_started (0 before)
var next_index: int        # index of the checkpoint that must be passed next (0-based)

func _init(checkpoint_count: int, medal_times: Dictionary) -> void
    # medal_times e.g. {"gold": 60.0, "silver": 75.0, "bronze": 90.0}; state starts "ready"
func start_countdown() -> void
    # only from "ready" or "finished": resets race_time and next_index, state "countdown" (3 s); emits
    # countdown_tick(3) immediately
func tick(delta: float) -> void
    # countdown: after 1 s emit countdown_tick(2), after 2 s countdown_tick(1), after 3 s state "racing" and
    # race_started (leftover time beyond 3 s is NOT added to race_time); racing: race_time += delta;
    # other states: nothing
func pass_checkpoint(index: int) -> bool
    # only while racing and only if index == next_index: emit checkpoint_passed(index, race_time), advance
    # next_index, return true; passing the last checkpoint finishes the race: state "finished", update the best
    # time, emit race_finished(race_time, medal); everything else returns false and changes nothing
func medal_for(time: float) -> String
    # "gold" if time <= gold, "silver" if <= silver, "bronze" if <= bronze, else "none"
func best_time() -> float
    # the fastest finished race of this object, INF if none
func reset() -> void
    # back to "ready", race_time 0, next_index 0 (keeps the best time)
```
The tests feed `tick()` with fixed deltas (e.g. 0.1 or 0.25), so it must be exact for any delta size, including
deltas that cross several whole seconds at once (emit every tick value that was crossed, in order). Test your class
yourself with a headless script (`studio godot-script tools/test_race.gd`), and make `studio godot-check` clean."""

TEST = r'''extends SceneTree
var ticks: Array = []
var started := 0
var cps: Array = []
var fin: Array = []
func _init() -> void:
	await process_frame
	var S = load("res://scripts/race_logic.gd")
	if S == null:
		print("TEST load FAIL script missing or broken"); quit(0); return
	var r = S.new(3, {"gold": 10.0, "silver": 15.0, "bronze": 20.0})
	print("TEST load PASS")
	r.countdown_tick.connect(func(v): ticks.append(v))
	r.race_started.connect(func(): started += 1)
	r.checkpoint_passed.connect(func(i, t): cps.append([i, t]))
	r.race_finished.connect(func(t, m): fin.append([t, m]))
	_t("initial_state", r.state == "ready" and r.next_index == 0 and is_equal_approx(r.race_time, 0.0), r.state)
	_t("no_cp_when_ready", r.pass_checkpoint(0) == false and cps.is_empty(), str(cps))
	r.tick(5.0)
	_t("tick_ready_noop", r.state == "ready" and is_equal_approx(r.race_time, 0.0), "%s %s" % [r.state, r.race_time])
	r.start_countdown()
	_t("countdown_start", r.state == "countdown" and ticks == [3], str(ticks))
	for i in 9: r.tick(0.25)     # 2.25 s
	_t("countdown_ticks", ticks == [3, 2, 1] and r.state == "countdown", "%s %s" % [ticks, r.state])
	r.tick(1.0)                   # 3.25 s: racing, leftover not counted
	_t("race_start", r.state == "racing" and started == 1 and is_equal_approx(r.race_time, 0.0), "%s started=%d t=%s" % [r.state, started, r.race_time])
	for i in 40: r.tick(0.1)     # 4.0 s of racing
	_t("race_time", absf(r.race_time - 4.0) < 1e-4, str(r.race_time))
	_t("wrong_cp", r.pass_checkpoint(1) == false and r.next_index == 0 and cps.is_empty(), str(cps))
	_t("cp0", r.pass_checkpoint(0) == true and r.next_index == 1 and cps.size() == 1 and cps[0][0] == 0 and absf(cps[0][1] - 4.0) < 1e-4, str(cps))
	_t("repeat_cp", r.pass_checkpoint(0) == false and r.next_index == 1, str(r.next_index))
	for i in 50: r.tick(0.1)     # 9.0 s
	r.pass_checkpoint(1)
	r.pass_checkpoint(2)
	_t("finish", r.state == "finished" and fin.size() == 1 and absf(fin[0][0] - 9.0) < 1e-4 and fin[0][1] == "gold", str(fin))
	_t("best1", absf(r.best_time() - 9.0) < 1e-4, str(r.best_time()))
	r.tick(1.0)
	_t("finished_frozen", absf(r.race_time - 9.0) < 1e-4, str(r.race_time))
	# second race, slower: silver; best stays 9.0
	ticks.clear()
	r.start_countdown()
	r.tick(3.0)
	_t("big_delta_ticks", ticks == [3, 2, 1] and r.state == "racing" and is_equal_approx(r.race_time, 0.0), "%s %s %s" % [ticks, r.state, r.race_time])
	r.tick(12.0)
	r.pass_checkpoint(0); r.pass_checkpoint(1); r.pass_checkpoint(2)
	_t("medal_silver", fin.size() == 2 and fin[1][1] == "silver", str(fin))
	_t("best_kept", absf(r.best_time() - 9.0) < 1e-4, str(r.best_time()))
	_t("medals", r.medal_for(10.0) == "gold" and r.medal_for(10.01) == "silver" and r.medal_for(20.0) == "bronze" and r.medal_for(20.5) == "none", "%s %s %s %s" % [r.medal_for(10.0), r.medal_for(10.01), r.medal_for(20.0), r.medal_for(20.5)])
	r.reset()
	_t("reset", r.state == "ready" and r.next_index == 0 and is_equal_approx(r.race_time, 0.0) and absf(r.best_time() - 9.0) < 1e-4, "%s %s %s" % [r.state, r.next_index, r.best_time()])
	var fresh = S.new(1, {"gold": 1.0, "silver": 2.0, "bronze": 3.0})
	_t("best_inf", fresh.best_time() == INF, str(fresh.best_time()))
	_t("no_countdown_while_racing", _racing_restart(S), "")
	quit(0)

func _racing_restart(S) -> bool:
	var r = S.new(2, {"gold": 1.0, "silver": 2.0, "bronze": 3.0})
	r.start_countdown(); r.tick(3.0); r.tick(0.5)
	r.start_countdown()
	return r.state == "racing" and absf(r.race_time - 0.5) < 1e-4

func _t(name: String, ok: bool, detail: String) -> void:
	print("TEST %s %s %s" % [name, "PASS" if ok else "FAIL", detail])
'''

WANT = ["load", "initial_state", "no_cp_when_ready", "tick_ready_noop", "countdown_start", "countdown_ticks",
        "race_start", "race_time", "wrong_cp", "cp0", "repeat_cp", "finish", "best1", "finished_frozen",
        "big_delta_ticks", "medal_silver", "best_kept", "medals", "reset", "best_inf", "no_countdown_while_racing"]


def setup(ws):
    _godot.setup_project(ws, "RaceLogic")
    (ws / "tools").mkdir(exist_ok=True)


def grade(ws):
    if not (ws / "scripts/race_logic.gd").exists():
        return {"score": 0.0, "passed": False, "notes": "scripts/race_logic.gd missing"}
    clean, lines = _godot.check(ws)
    res, details, out = _godot.hidden_test(ws, "test_race", TEST)
    passed = sum(res.get(k, False) for k in WANT)
    score = 0.2 * clean + 0.8 * passed / len(WANT)
    return {"score": round(score, 3), "passed": clean and passed == len(WANT),
            "notes": f"check {'clean' if clean else 'NOT clean'}; tests {passed}/{len(WANT)}"
                     + (f"; {' | '.join(details[:4])}" if details else "")}


REFERENCE = r'''class_name RaceLogic extends RefCounted

signal countdown_tick(value: int)
signal race_started()
signal checkpoint_passed(index: int, time: float)
signal race_finished(time: float, medal: String)

var state: String = "ready"
var race_time: float = 0.0
var next_index: int = 0
var _count: int
var _medals: Dictionary
var _countdown: float = 0.0
var _best: float = INF

func _init(checkpoint_count: int, medal_times: Dictionary) -> void:
	_count = checkpoint_count
	_medals = medal_times

func start_countdown() -> void:
	if state != "ready" and state != "finished":
		return
	race_time = 0.0
	next_index = 0
	_countdown = 0.0
	state = "countdown"
	countdown_tick.emit(3)

func tick(delta: float) -> void:
	if state == "countdown":
		var before := _countdown
		_countdown += delta
		for s in [1, 2]:
			if before < s and _countdown >= s:
				countdown_tick.emit(3 - s)
		if _countdown >= 3.0:
			state = "racing"
			race_time = 0.0
			race_started.emit()
	elif state == "racing":
		race_time += delta

func pass_checkpoint(index: int) -> bool:
	if state != "racing" or index != next_index:
		return false
	checkpoint_passed.emit(index, race_time)
	next_index += 1
	if next_index >= _count:
		state = "finished"
		_best = minf(_best, race_time)
		race_finished.emit(race_time, medal_for(race_time))
	return true

func medal_for(time: float) -> String:
	if time <= _medals["gold"]:
		return "gold"
	if time <= _medals["silver"]:
		return "silver"
	if time <= _medals["bronze"]:
		return "bronze"
	return "none"

func best_time() -> float:
	return _best

func reset() -> void:
	state = "ready"
	race_time = 0.0
	next_index = 0
	_countdown = 0.0
'''
