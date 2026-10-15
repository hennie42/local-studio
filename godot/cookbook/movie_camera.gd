extends Node3D
## Recipe: deterministic camera moves for clips (Movie Maker steps time by exactly 1/fps, so drive everything
## from accumulated time, never from wall-clock). Two patterns: orbit around a target, and a Path3D + PathFollow3D
## spline with progress_ratio. Ease with smoothstep for gentle starts/stops.

@export var duration := 3.0
var t := 0.0
var cam: Camera3D
var path_follow: PathFollow3D


func orbit_transform(center: Vector3, radius: float, height: float, start_deg: float, sweep_deg: float, u: float) -> Transform3D:
	var a := deg_to_rad(start_deg + sweep_deg * smoothstep(0.0, 1.0, u))
	var pos := center + Vector3(sin(a) * radius, height, cos(a) * radius)
	return Transform3D(Basis(), pos).looking_at(center, Vector3.UP)


func build_path(points: PackedVector3Array) -> void:
	var path := Path3D.new()
	var curve := Curve3D.new()
	for p in points:
		curve.add_point(p)
	path.curve = curve
	add_child(path)
	path_follow = PathFollow3D.new()
	path_follow.loop = false
	path_follow.rotation_mode = PathFollow3D.ROTATION_NONE
	path.add_child(path_follow)


func _ready() -> void:
	cam = Camera3D.new()
	cam.fov = 40.0
	add_child(cam)
	cam.make_current()


func _process(delta: float) -> void:
	t += delta
	var u := clampf(t / duration, 0.0, 1.0)
	cam.global_transform = orbit_transform(Vector3.ZERO, 8.0, 2.5, 0.0, 90.0, u)


func run_selftest() -> String:
	var a := orbit_transform(Vector3.ZERO, 8.0, 2.5, 0.0, 90.0, 0.0)
	var b := orbit_transform(Vector3.ZERO, 8.0, 2.5, 0.0, 90.0, 1.0)
	if not a.origin.is_equal_approx(Vector3(0, 2.5, 8)) or not b.origin.is_equal_approx(Vector3(8, 2.5, 0)):
		return "orbit %s %s" % [a.origin, b.origin]
	var fwd := -b.basis.z            # cameras look down -Z
	if fwd.dot((Vector3.ZERO - b.origin).normalized()) < 0.999:
		return "orbit camera not looking at the centre"
	build_path(PackedVector3Array([Vector3(0, 0, 0), Vector3(10, 0, 0)]))
	path_follow.progress_ratio = 0.5
	await get_tree().process_frame
	return "" if path_follow.global_position.is_equal_approx(Vector3(5, 0, 0)) else "path %s" % path_follow.global_position
