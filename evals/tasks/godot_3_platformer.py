"""Godot: a small 2D platformer with input actions, coins, goal, --autopilot, exported for Linux and Web."""
import re
import shutil

import _godot

AREA = "godot"
TITLE = "Godot: 2D platformer + --autopilot, exported Linux/Web; exported build must finish the level"
KIND = "agent"
TIMEOUT = 3000

PROMPT = """This is a Godot 4.7 project (name Platformer). Read AGENTS.md first. Make a small 2D platformer
(the main scene stays scenes/main.tscn; replace the placeholder 3D content and scripts/main.gd):
- A level built in code: a floor from x = 0 to 900 and from x = 1000 to 2000 at y = 500 (a 100 px gap between),
  as StaticBody2D with rectangle collision shapes and something visible (ColorRect or Polygon2D).
- A player: CharacterBody2D (collision shape about 24 x 40 px, visible), starting at (100, 450), moving left/right
  at ~300 px/s with gravity and a jump that clears the gap; movement in _physics_process with move_and_slide().
- Input actions created in code: move_left (A, Left arrow, gamepad left stick left), move_right (D, Right arrow,
  left stick right), jump (Space, gamepad A button).
- 5 coins (Area2D with a collision shape and a visible shape) along the way at x = 300, 600, 1100, 1400, 1700,
  reachable by running/jumping; collecting one removes it and logs `GameEvent.marker("COIN", "n/5")`.
- A goal (Area2D) at x = 1900: touching it logs `GameEvent.marker("FINISH", "t=<seconds since start> coins=<n>/5")`
  and quits shortly after (GameEvent.quit()). At the start log `GameEvent.marker("START")`.
- An --autopilot mode (GameEvent.autopilot) that plays the level by itself through the same player code (e.g. hold
  right, jump before the gap), collects all coins and reaches the goal.
- A Camera2D following the player.
Iterate on the autopilot with `studio godot-play scenes/main.tscn 30 --headless --autopilot` (seconds, no GPU), look
at the result once with `studio godot-play scenes/main.tscn 30 --autopilot --shots` (a screenshot), make
`studio godot-check` clean, then export Linux and Web builds with `studio godot-export linux` and
`studio godot-export web`, and check the export with `studio run-export 30 --autopilot`."""

REFERENCE_MAIN = r'''extends Node2D
## Reference solution (grader validation only).

var coins := 0
var t := 0.0
var done := false


func _ready() -> void:
	_setup_input()
	_platform(0, 900, 500)
	_platform(1000, 2000, 500)
	var player := CharacterBody2D.new()
	player.set_script(load("res://scripts/player.gd"))
	player.position = Vector2(100, 450)
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(24, 40)
	shape.shape = rect
	player.add_child(shape)
	var vis := ColorRect.new()
	vis.size = Vector2(24, 40)
	vis.position = Vector2(-12, -20)
	vis.color = Color(0.3, 0.8, 1.0)
	player.add_child(vis)
	var cam := Camera2D.new()
	player.add_child(cam)
	add_child(player)
	for x in [300, 600, 1100, 1400, 1700]:
		_area(Vector2(x, 470), 14.0, Color(1, 0.85, 0.2), _on_coin)
	_area(Vector2(1900, 450), 30.0, Color(0.2, 1, 0.4), _on_goal)
	GameEvent.marker("START")


func _process(delta: float) -> void:
	t += delta


func _setup_input() -> void:
	for a in ["move_left", "move_right", "jump"]:
		if not InputMap.has_action(a):
			InputMap.add_action(a)
	for pair in [["move_left", KEY_A], ["move_left", KEY_LEFT], ["move_right", KEY_D], ["move_right", KEY_RIGHT], ["jump", KEY_SPACE]]:
		var e := InputEventKey.new()
		e.physical_keycode = pair[1]
		InputMap.action_add_event(pair[0], e)
	var jb := InputEventJoypadButton.new()
	jb.button_index = JOY_BUTTON_A
	InputMap.action_add_event("jump", jb)
	for pair in [["move_left", -1.0], ["move_right", 1.0]]:
		var m := InputEventJoypadMotion.new()
		m.axis = JOY_AXIS_LEFT_X
		m.axis_value = pair[1]
		InputMap.action_add_event(pair[0], m)


func _platform(x0: float, x1: float, y: float) -> void:
	var body := StaticBody2D.new()
	body.position = Vector2((x0 + x1) / 2.0, y + 20.0)
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(x1 - x0, 40)
	shape.shape = rect
	body.add_child(shape)
	var vis := ColorRect.new()
	vis.size = rect.size
	vis.position = -rect.size / 2.0
	vis.color = Color(0.35, 0.3, 0.4)
	body.add_child(vis)
	add_child(body)


func _area(pos: Vector2, radius: float, color: Color, cb: Callable) -> void:
	var a := Area2D.new()
	a.position = pos
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = radius
	shape.shape = circle
	a.add_child(shape)
	var vis := Polygon2D.new()
	var pts := PackedVector2Array()
	for i in 12:
		pts.append(Vector2.from_angle(TAU * i / 12.0) * radius)
	vis.polygon = pts
	vis.color = color
	a.add_child(vis)
	a.body_entered.connect(cb.bind(a))
	add_child(a)


func _on_coin(_body: Node2D, coin: Area2D) -> void:
	coin.queue_free()
	coins += 1
	GameEvent.marker("COIN", "%d/5" % coins)


func _on_goal(_body: Node2D, _goal: Area2D) -> void:
	if done:
		return
	done = true
	GameEvent.marker("FINISH", "t=%.2f coins=%d/5" % [t, coins])
	await get_tree().create_timer(0.3).timeout
	GameEvent.quit(0)
'''

REFERENCE_PLAYER = r'''extends CharacterBody2D

const SPEED := 300.0
const JUMP := -520.0
const GRAVITY := 1400.0


func _physics_process(delta: float) -> void:
	velocity.y += GRAVITY * delta
	var dir := Input.get_axis("move_left", "move_right")
	var jump := Input.is_action_just_pressed("jump")
	if GameEvent.autopilot:
		dir = 1.0
		jump = position.x > 830.0 and position.x < 880.0
	velocity.x = dir * SPEED
	if jump and is_on_floor():
		velocity.y = JUMP
	move_and_slide()
'''


def setup(ws):
    _godot.setup_project(ws, "Platformer")


def grade(ws):
    notes, score = [], 0.0
    clean, _ = _godot.check(ws)
    score += 0.15 * clean
    notes.append("check " + ("clean" if clean else "NOT clean"))
    src = "\n".join(p.read_text(errors="replace") for p in ws.rglob("*.gd")
                    if ".godot" not in p.parts and ".studio" not in p.parts and "godot-api" not in p.parts)
    inputs = all(re.search(p, src) for p in (r"InputMap\.add_action", r"InputEventJoypad(Button|Motion)",
                                              r"KEY_(A|D|SPACE|LEFT|RIGHT)\b", r"move_and_slide\(\s*\)"))
    score += 0.1 * inputs
    notes.append("inputs " + ("ok" if inputs else "missing (actions/gamepad/keys/move_and_slide)"))
    exes = sorted((ws / "build/linux").glob("*.x86_64")) if (ws / "build/linux").is_dir() else []
    exe = exes[0] if exes else ws / "build/linux/Platformer.x86_64"
    web = (ws / "build/web/index.html").exists() and any((ws / "build/web").glob("*.wasm"))
    score += 0.1 * exe.exists() + 0.05 * web
    notes.append(f"exports linux={'yes' if exe.exists() else 'NO'} web={'yes' if web else 'NO'}")
    target = exe if exe.exists() else None
    out = ""
    if target:
        tmp = ws / ".studio/grader/run"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        shutil.copy2(target, tmp / target.name)
        import subprocess
        try:
            p = subprocess.run([str(tmp / target.name), "--headless", "--", "--autopilot"], cwd=tmp,
                               capture_output=True, text=True, timeout=90)
            out = p.stdout + p.stderr
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        (ws / ".studio/grader/export_run.log").write_text(out)
        how = "exported build"
    else:  # fall back to the project itself (less credit)
        rc, out = _godot.run(ws, ["--headless", "--path", ".", "--", "--autopilot"], "project_run.log", timeout=90)
        how = "project (no export)"
    marks = _godot.markers(out)
    fin = [m for m in marks if m.startswith("GAME_FINISH")]
    coins = [m for m in marks if m.startswith("GAME_COIN")]
    t = float(re.search(r"t=([\d.]+)", fin[0]).group(1)) if fin and re.search(r"t=([\d.]+)", fin[0]) else 0.0
    started = any(m.startswith("GAME_START") for m in marks)
    finished = bool(fin) and started and t >= 2.0
    score += (0.35 if target else 0.2) * finished + 0.25 * min(len(coins), 5) / 5
    errors = [l for l in out.splitlines() if "SCRIPT ERROR" in l][:2]
    notes.append(f"{how}: start={started} finish={'t=%.1f' % t if fin else 'NO'} coins {len(coins)}/5"
                 + (f"; errors: {' | '.join(errors)}" if errors else ""))
    return {"score": round(score, 3), "passed": score >= 0.999, "notes": "; ".join(notes)}
