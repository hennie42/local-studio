extends RefCounted
## Recipe: persistence under user:// (per-user data dir; res:// is read-only in exported games).
## ConfigFile for settings/best times; JSON for structured data. FileAccess.open returns null on failure:
## check it (and FileAccess.get_open_error()). JSON numbers come back as float.

const SETTINGS := "user://settings.cfg"
const SAVE := "user://save.json"


static func save_best_time(level: String, seconds: float) -> Error:
	var cfg := ConfigFile.new()
	cfg.load(SETTINGS)  # fine if it does not exist yet
	if seconds < cfg.get_value("best", level, INF):
		cfg.set_value("best", level, seconds)
	return cfg.save(SETTINGS)


static func best_time(level: String) -> float:
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS) != OK:
		return INF
	return cfg.get_value("best", level, INF)


static func save_json(data: Dictionary, path: String = SAVE) -> Error:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(JSON.stringify(data, "\t"))
	return OK


static func load_json(path: String = SAVE) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


func run_selftest() -> String:
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS))
	save_best_time("city", 92.5)
	save_best_time("city", 99.0)  # slower: must not overwrite
	if not is_equal_approx(best_time("city"), 92.5):
		return "best %s" % best_time("city")
	if best_time("nowhere") != INF:
		return "missing level should be INF"
	save_json({"coins": 3, "name": "ann", "pos": [1, 2]})
	var d := load_json()
	if int(d.get("coins", -1)) != 3 or d.get("name") != "ann" or d.get("pos") != [1.0, 2.0]:
		return "json round trip %s" % d
	return ""
