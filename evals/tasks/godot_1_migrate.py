"""Godot: port four Godot 3 scripts to Godot 4.7 (the main local-model failure mode), keeping API and behaviour."""
import _godot

AREA = "godot"
TITLE = "Godot: port Godot 3 scripts to 4.7 (lint/compile clean + hidden behaviour tests)"
KIND = "agent"
TIMEOUT = 2400

PROMPT = """This is a Godot 4.7 project. Read AGENTS.md first. The four scripts in scripts/legacy/ were written for
Godot 3 and do not work in Godot 4.7: player.gd, score_board.gd, countdown.gd, spawner.gd. Port them in place to
Godot 4.7 GDScript. Keep each script's public API exactly: the same base class role (player = 2D character body,
others as they are), the same signal names and signal arguments, method names and parameters, and exported property
names (keep them exported). Keep the behaviour:
- player.gd: a 2D character that every physics frame falls with `gravity` and moves right at `speed`, using the
  engine's slide movement with up = Vector2.UP; collect() increments coins and emits coin_collected(total).
- score_board.gd: add(name, points), best() returns the name with the highest total ("" if empty),
  save_json(path) / load_json(path) persist the totals as JSON.
- countdown.gd: start() counts down `seconds` steps of 0.1 s each (printing the numbers), then emits finished.
- spawner.gd: spawn(n) instantiates enemy_scene n times at random positions with x and y in [0, 100] as children
  and returns the child count.
Use static types where they help. When you are done, `studio godot-check` must report no Godot 3 idioms and no
errors. Do not add other files to scripts/legacy/."""

LEGACY = {
    "player.gd": '''extends KinematicBody2D

signal coin_collected(total)

export var speed = 200.0
export var gravity = 900.0
var velocity = Vector2()
var coins = 0

func _physics_process(delta):
    velocity.y += gravity * delta
    velocity.x = speed
    velocity = move_and_slide(velocity, Vector2.UP)

func collect():
    coins += 1
    emit_signal("coin_collected", coins)
''',
    "score_board.gd": '''extends Node

var scores = {}

func add(name, points):
    if not scores.has(name):
        scores[name] = 0
    scores[name] += points

func best():
    var best_name = ""
    var best_points = -1
    for n in scores.keys():
        if scores[n] > best_points:
            best_points = scores[n]
            best_name = n
    return best_name

func save_json(path):
    var f = File.new()
    f.open(path, File.WRITE)
    f.store_string(to_json(scores))
    f.close()

func load_json(path):
    var f = File.new()
    if not f.file_exists(path):
        return
    f.open(path, File.READ)
    scores = parse_json(f.get_as_text())
    f.close()
''',
    "countdown.gd": '''extends Node

signal finished

export(int) var seconds = 3

func start():
    for i in range(seconds, 0, -1):
        print(i)
        yield(get_tree().create_timer(0.1), "timeout")
    emit_signal("finished")
''',
    "spawner.gd": '''extends Node2D

export(PackedScene) var enemy_scene

func spawn(n):
    for i in range(n):
        var e = enemy_scene.instance()
        e.position = Vector2(rand_range(0, 100), rand_range(0, 100))
        add_child(e)
    return get_child_count()
''',
}

TEST = r'''extends SceneTree
var got := -1
func _on_coin(total: int) -> void:
	got = total
func _init() -> void:
	await process_frame
	# player: falls and moves right through the engine's slide movement
	var P: Script = load("res://scripts/legacy/player.gd")
	var p = P.new()
	var ok_base: bool = p is CharacterBody2D
	print("TEST player_base %s %s" % ["PASS" if ok_base else "FAIL", p.get_class()])
	if ok_base:
		root.add_child(p)
		p.speed = 100.0
		for i in 20:
			await physics_frame
		print("TEST player_moves %s x=%.1f y=%.1f" % ["PASS" if p.position.x > 5.0 and p.position.y > 1.0 else "FAIL", p.position.x, p.position.y])
		p.coin_collected.connect(_on_coin)
		p.collect(); p.collect()
		print("TEST player_signal %s got=%d coins=%d" % ["PASS" if got == 2 and p.coins == 2 else "FAIL", got, p.coins])
		var props := (p.get_property_list() as Array).filter(func(d): return d.usage & PROPERTY_USAGE_EDITOR != 0).map(func(d): return d.name)
		print("TEST player_exports %s %s" % ["PASS" if "speed" in props and "gravity" in props else "FAIL", props])
	# score board: totals, best, json round trip
	var sb = load("res://scripts/legacy/score_board.gd").new()
	root.add_child(sb)
	sb.add("ann", 3); sb.add("bob", 5); sb.add("ann", 4)
	print("TEST score_best %s %s" % ["PASS" if sb.best() == "ann" else "FAIL", sb.best()])
	var path := "user://grader_scores.json"
	sb.save_json(path)
	var sb2 = load("res://scripts/legacy/score_board.gd").new()
	root.add_child(sb2)
	sb2.load_json(path)
	var rt: bool = sb2.scores.size() == 2 and int(sb2.scores["ann"]) == 7 and int(sb2.scores["bob"]) == 5
	print("TEST score_json %s %s" % ["PASS" if rt else "FAIL", sb2.scores])
	var empty = load("res://scripts/legacy/score_board.gd").new()
	print("TEST score_empty %s '%s'" % ["PASS" if empty.best() == "" else "FAIL", empty.best()])
	# countdown: awaits timers, then emits finished
	var cd = load("res://scripts/legacy/countdown.gd").new()
	root.add_child(cd)
	cd.seconds = 2
	var t0 := Time.get_ticks_msec()
	cd.start()
	await cd.finished
	var dt := Time.get_ticks_msec() - t0
	print("TEST countdown %s %d ms" % ["PASS" if dt >= 150 and dt < 3000 else "FAIL", dt])
	# spawner: instantiates a PackedScene n times in range
	var sp = load("res://scripts/legacy/spawner.gd").new()
	root.add_child(sp)
	var enemy := Node2D.new()
	var packed := PackedScene.new()
	packed.pack(enemy)
	sp.enemy_scene = packed
	var n = sp.spawn(5)
	var inside := true
	for c in sp.get_children():
		inside = inside and c.position.x >= 0 and c.position.x <= 100 and c.position.y >= 0 and c.position.y <= 100
	print("TEST spawner %s n=%s inside=%s" % ["PASS" if n == 5 and inside else "FAIL", n, inside])
	quit(0)
'''


def setup(ws):
    _godot.setup_project(ws, "Migrate")
    d = ws / "scripts/legacy"
    d.mkdir(parents=True, exist_ok=True)
    for name, src in LEGACY.items():
        (d / name).write_text(src)


def grade(ws):
    clean, lines = _godot.check(ws)
    res, details, out = _godot.hidden_test(ws, "test_migrate", TEST)
    want = ["player_base", "player_moves", "player_signal", "player_exports", "score_best", "score_json",
            "score_empty", "countdown", "spawner"]
    passed = sum(res.get(k, False) for k in want)
    score = 0.3 * clean + 0.7 * passed / len(want)
    summary = [l for l in lines if "godot-lint:" in l or "GODOT_CHECK" in l and "script(s)" in l]
    return {"score": round(score, 3), "passed": clean and passed == len(want),
            "notes": f"check {'clean' if clean else 'NOT clean'} ({'; '.join(summary)}); tests {passed}/{len(want)}"
                     + (f"; {' | '.join(details[:4])}" if details else "")}


REFERENCE = {  # a correct port, used only to validate the grader
    "player.gd": '''extends CharacterBody2D

signal coin_collected(total: int)

@export var speed: float = 200.0
@export var gravity: float = 900.0
var coins: int = 0

func _physics_process(delta: float) -> void:
	velocity.y += gravity * delta
	velocity.x = speed
	up_direction = Vector2.UP
	move_and_slide()

func collect() -> void:
	coins += 1
	coin_collected.emit(coins)
''',
    "score_board.gd": '''extends Node

var scores: Dictionary = {}

func add(name: String, points: int) -> void:
	scores[name] = scores.get(name, 0) + points

func best() -> String:
	var best_name := ""
	var best_points := -1
	for n in scores.keys():
		if scores[n] > best_points:
			best_points = scores[n]
			best_name = n
	return best_name

func save_json(path: String) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(JSON.stringify(scores))

func load_json(path: String) -> void:
	if not FileAccess.file_exists(path):
		return
	scores = JSON.parse_string(FileAccess.get_file_as_string(path))
''',
    "countdown.gd": '''extends Node

signal finished

@export var seconds: int = 3

func start() -> void:
	for i in range(seconds, 0, -1):
		print(i)
		await get_tree().create_timer(0.1).timeout
	finished.emit()
''',
    "spawner.gd": '''extends Node2D

@export var enemy_scene: PackedScene

func spawn(n: int) -> int:
	for i in range(n):
		var e := enemy_scene.instantiate()
		e.position = Vector2(randf_range(0, 100), randf_range(0, 100))
		add_child(e)
	return get_child_count()
''',
}
