extends CanvasLayer
## Recipe: HUD built in code. A CanvasLayer draws on top of the game, unaffected by Camera2D/3D.
## Position Controls with anchor presets (set_anchors_and_offsets_preset), grow direction and margins;
## font size via add_theme_font_size_override; colours via add_theme_color_override.

var timer_label: Label
var score_label: Label
var message: Label


func _ready() -> void:
	layer = 10
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE   # a full-screen container must let clicks through to the game
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 24)
	add_child(margin)
	timer_label = _label(HORIZONTAL_ALIGNMENT_CENTER, 40)
	timer_label.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	margin.add_child(timer_label)
	score_label = _label(HORIZONTAL_ALIGNMENT_RIGHT, 28)
	score_label.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	margin.add_child(score_label)
	message = _label(HORIZONTAL_ALIGNMENT_CENTER, 64)
	message.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	message.grow_horizontal = Control.GROW_DIRECTION_BOTH
	message.grow_vertical = Control.GROW_DIRECTION_BOTH
	message.add_theme_color_override("font_color", Color(0.55, 1.0, 1.0))
	message.add_theme_color_override("font_outline_color", Color.BLACK)
	message.add_theme_constant_override("outline_size", 8)
	add_child(message)


func _label(align: HorizontalAlignment, size: int) -> Label:
	var l := Label.new()
	l.horizontal_alignment = align
	l.add_theme_font_size_override("font_size", size)
	return l


func set_time(seconds: float) -> void:
	var cs := int(round(seconds * 100.0))
	timer_label.text = "%02d:%02d.%02d" % [cs / 6000, (cs / 100) % 60, cs % 100]


func set_score(n: int, total: int) -> void:
	score_label.text = "RING %d/%d" % [n, total]


func show_message(text: String, seconds: float = 0.0) -> void:
	message.text = text
	message.visible = true
	if seconds > 0.0:
		await get_tree().create_timer(seconds).timeout
		message.visible = false


func run_selftest() -> String:
	set_time(83.456)
	set_score(3, 16)
	if timer_label.text != "01:23.46":
		return "timer text " + timer_label.text
	if score_label.text != "RING 3/16":
		return "score text " + score_label.text
	await show_message("GO!", 0.05)
	return "" if not message.visible else "message still visible"
