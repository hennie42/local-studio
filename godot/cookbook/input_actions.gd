extends Node
## Recipe: define input actions in code (keyboard + gamepad), no editor needed.
## Call InputSetup-style code once at startup (an autoload or the main scene's _ready).
## Read input with Input.get_axis("move_left", "move_right"), Input.is_action_just_pressed("jump").

const KEYS := {
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"move_up": [KEY_W, KEY_UP],
	"move_down": [KEY_S, KEY_DOWN],
	"jump": [KEY_SPACE],
	"pause": [KEY_ESCAPE],
}
const PAD_BUTTONS := {"jump": [JOY_BUTTON_A], "pause": [JOY_BUTTON_START]}
## action -> [axis, direction]; the left stick drives movement
const PAD_AXES := {
	"move_left": [JOY_AXIS_LEFT_X, -1.0],
	"move_right": [JOY_AXIS_LEFT_X, 1.0],
	"move_up": [JOY_AXIS_LEFT_Y, -1.0],
	"move_down": [JOY_AXIS_LEFT_Y, 1.0],
}


static func setup_actions() -> void:
	for action: String in KEYS:
		if not InputMap.has_action(action):
			InputMap.add_action(action, 0.2)  # 0.2 = stick deadzone
		for key: Key in KEYS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key  # physical: same place on any keyboard layout
			InputMap.action_add_event(action, ev)
	for action: String in PAD_BUTTONS:
		for button: JoyButton in PAD_BUTTONS[action]:
			var ev := InputEventJoypadButton.new()
			ev.button_index = button
			InputMap.action_add_event(action, ev)
	for action: String in PAD_AXES:
		var ev := InputEventJoypadMotion.new()
		ev.axis = PAD_AXES[action][0]
		ev.axis_value = PAD_AXES[action][1]
		InputMap.action_add_event(action, ev)


func run_selftest() -> String:
	setup_actions()
	for a in KEYS:
		if not InputMap.has_action(a):
			return "missing action " + a
	if InputMap.action_get_events("jump").size() != 2:
		return "jump should have key + pad button"
	Input.action_press("move_right")
	var axis := Input.get_axis("move_left", "move_right")
	Input.action_release("move_right")
	return "" if is_equal_approx(axis, 1.0) else "axis %s" % axis
