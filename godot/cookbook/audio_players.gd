extends Node
## Recipe: audio. Play files: AudioStreamPlayer (UI/music, no position), AudioStreamPlayer2D/3D (positional).
## stream = load("res://audio/x.wav" or ".ogg"); .play(); loop music via the import settings or
## `stream.loop_mode` (WAV) / `stream.loop` (OGG). Generate sounds in code with AudioStreamWAV (16-bit PCM bytes).
## Pitch for engines: player.pitch_scale = 0.8 + speed_ratio. Volume in dB: player.volume_db = -6.0.


static func tone(freq: float, seconds: float, rate: int = 44100) -> AudioStreamWAV:
	var n := int(seconds * rate)
	var data := PackedByteArray()
	data.resize(n * 2)
	for i in n:
		var env := minf(1.0, float(n - i) / (rate * 0.05))   # short fade-out, no click
		var s := int(sin(TAU * freq * i / rate) * 0.4 * env * 32767.0)
		data.encode_s16(i * 2, s)
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = rate
	w.stereo = false
	w.data = data
	return w


func play(stream: AudioStream, volume_db: float = 0.0) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.stream = stream
	p.volume_db = volume_db
	add_child(p)
	p.play()
	p.finished.connect(p.queue_free)   # one-shot players clean themselves up
	return p


func run_selftest() -> String:
	var beep := tone(880.0, 0.25)
	if not is_equal_approx(beep.get_length(), 0.25):
		return "length %s" % beep.get_length()
	var p := play(beep, -12.0)
	return "" if p.stream == beep and is_equal_approx(p.volume_db, -12.0) else "player not set up"
