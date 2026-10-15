"""ffmpeg: assemble an edit with crossfades, a title and a faded soundtrack."""
import subprocess
import numpy as np
import _media

AREA = "blender_media"
TITLE = "ffmpeg: 3 clips + xfades + title + faded soundtrack"
KIND = "agent"
TIMEOUT = 1200

PROMPT = """Using ffmpeg (CPU encoders are fine), create out/edit.mp4 from clips/a.mp4, clips/b.mp4 and
clips/c.mp4 (3 seconds each, in that order) with:
- 1920x1080, 30 fps, H.264 video in yuv420p;
- 0.5-second crossfade transitions between consecutive clips (total length 8.0 s);
- the text "LOCAL STUDIO" in white, centred, during the first 2 seconds only
  (font: /usr/share/fonts/TTF/DejaVuSans-Bold.ttf if it exists, otherwise any available font);
- audio/music.wav as the AAC soundtrack, cut to the video length, with a 1-second fade-out at the end.
Put the command(s) in make_edit.sh, run it, and verify the result with ffprobe."""


def setup(ws):
    (ws / "clips").mkdir()
    (ws / "audio").mkdir()
    (ws / "out").mkdir()
    for name, color in (("a", "red"), ("b", "0x00C000"), ("c", "blue")):
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=c={color}:s=1280x720:r=25:d=3",
                        "-vf", "drawbox=x=40:y=40:w=200:h=120:color=white@0.3:t=fill", "-pix_fmt", "yuv420p",
                        "-c:v", "libx264", str(ws / f"clips/{name}.mp4")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000:duration=12",
                    "-af", "volume=0.5", str(ws / "audio/music.wav")], check=True)


def centre_white_share(path, t):
    """Share of near-white pixels in the centre band (where the title goes). Counting text pixels works
    for any font size; mean brightness did not (small titles barely move the average)."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1",
                        "-vf", "crop=iw*0.6:ih*0.3:iw*0.2:ih*0.35,scale=384:108", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, timeout=60)
    if len(p.stdout) < 384 * 108 * 3:
        return None
    px = np.frombuffer(p.stdout[: 384 * 108 * 3], dtype=np.uint8).reshape(-1, 3)
    return float((px.min(axis=1) > 200).mean())


def audio_rms(path, start, dur):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(path), "-vn",
                        "-ac", "1", "-ar", "48000", "-f", "s16le", "-"], capture_output=True, timeout=60)
    a = np.frombuffer(p.stdout, dtype="<i2").astype(float) / 32768.0
    return float(np.sqrt((a ** 2).mean())) if a.size else 0.0


def grade(ws):
    out = ws / "out/edit.mp4"
    if not out.exists():
        return {"score": 0.0, "passed": False, "notes": "no out/edit.mp4"}
    info = _media.probe(out)
    v, a = info.get("video") or {}, info.get("audio") or {}
    checks = {
        "h264_1080p30": v.get("codec") == "h264" and (v.get("width"), v.get("height")) == (1920, 1080)
                        and abs(v.get("fps", 0) - 30) < 0.01 and v.get("pix_fmt") == "yuv420p",
        "duration_8s": abs(info.get("duration", 0) - 8.0) < 0.15,
        "aac": a.get("codec") == "aac",
        "make_edit.sh": (ws / "make_edit.sh").exists(),
    }
    order = []
    for t in (1.0, 4.0, 7.0):
        rgb = _media.frame_rgb(out, t)
        order.append(int(np.argmax(rgb)) if rgb is not None else -1)
    checks["clip_order"] = order == [0, 1, 2]
    early, late = centre_white_share(out, 1.0), centre_white_share(out, 2.2)  # same clip, with and without title
    checks["title_first_2s"] = early is not None and late is not None and early > 0.003 and late < 0.0005
    rms_mid, rms_end = audio_rms(out, 3.0, 1.0), audio_rms(out, 7.7, 0.25)
    checks["audio_fadeout"] = rms_mid > 0.01 and rms_end < 0.4 * rms_mid
    score = sum(checks.values()) / len(checks)
    failed = [k for k, v in checks.items() if not v]
    return {"score": round(score, 3), "passed": not failed,
            "notes": f"dur={info.get('duration', 0):.2f} order={order}" + (f"; failed: {', '.join(failed)}" if failed else "")}
