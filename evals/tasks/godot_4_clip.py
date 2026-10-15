"""Godot: a 3 s 3D night clip rendered with Movie Maker and encoded to mp4."""
import json
import subprocess

import _godot

AREA = "godot"
TITLE = "Godot: 3 s 3D night clip (orbit, glow, fog, reflections) via Movie Maker -> mp4"
KIND = "agent"
TIMEOUT = 2400

PROMPT = """This is a Godot 4.7 project (Forward+ renderer, 1920x1080 viewport). Read AGENTS.md first. Make a
3-second clip (90 frames at 30 fps) in a new scene scenes/clip.tscn (script scripts/clip.gd, nodes built in code):
- Night: dark blue-black background, a WorldEnvironment with glow enabled and volumetric fog (thin, so the lights
  read as shafts/haze), a filmic tonemapper.
- Subject: a cluster of 5-8 tall glowing crystals or neon pillars (emissive materials in 2-3 neon colours: magenta,
  cyan, amber) standing on a dark glossy floor that reflects them (low roughness + screen-space reflections), plus
  one or two coloured OmniLights near them.
- Camera: one slow continuous orbit around the cluster (about a quarter turn over the 90 frames), slightly above,
  always looking at the cluster, driven deterministically by elapsed time (Movie Maker uses a fixed 1/30 s step).
Render it with `studio godot-movie scenes/clip.tscn Renders/clip 90 30`, look at the first, middle and last frame
(Renders/clip/frame00000000.png, frame00000045.png, frame00000089.png) and fix anything that looks wrong (black
frames, blown out, subject off-screen), then encode with `studio encode Renders/clip 30 out/clip.mp4`.
`studio godot-check` must be clean."""


def setup(ws):
    _godot.setup_project(ws, "Clip")


def _probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=width,height,nb_read_frames,avg_frame_rate", "-of", "json", str(path)],
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads(p.stdout)["streams"][0]
    except (KeyError, IndexError, json.JSONDecodeError):
        return {}


def _frame(path, idx, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vf", f"select=eq(n\\,{idx})",
                    "-vframes", "1", "-pix_fmt", "rgb24", str(out)], timeout=120)


def grade(ws):
    import numpy as np
    from PIL import Image
    notes, score = [], 0.0
    clean, _ = _godot.check(ws)
    score += 0.15 * clean
    notes.append("check " + ("clean" if clean else "NOT clean"))
    frames = sorted((ws / "Renders/clip").glob("frame*.png"))
    movie = len(frames) >= 90
    score += 0.1 * movie
    notes.append(f"Movie Maker frames {len(frames)}")
    clip = ws / "out/clip.mp4"
    if not clip.exists():
        return {"score": round(score, 3), "passed": False, "notes": "; ".join(notes + ["out/clip.mp4 missing"])}
    s = _probe(clip)
    n = int(s.get("nb_read_frames", 0) or 0)
    spec = s.get("width") == 1920 and s.get("height") == 1080 and 88 <= n <= 92
    score += 0.2 * spec
    notes.append(f"mp4 {s.get('width')}x{s.get('height')} {n} frames")
    g = ws / ".studio/grader"
    g.mkdir(parents=True, exist_ok=True)
    imgs = []
    for i in (0, n // 2, max(n - 1, 0)):
        f = g / f"f{i}.png"
        _frame(clip, i, f)
        if f.exists():
            imgs.append(np.asarray(Image.open(f).convert("RGB"), dtype=np.float32))
    if len(imgs) == 3:
        means = [float(a.mean()) for a in imgs]
        exposed = all(8 <= m <= 170 for m in means)
        bright = max(float((a.max(axis=2) > 200).mean()) for a in imgs)   # glowing highlights present
        motion = float(np.abs(imgs[0] - imgs[2]).mean())
        colour = max(float((a.max(axis=2) - a.min(axis=2)).mean()) for a in imgs)   # neon, not grey
        score += 0.2 * exposed + 0.2 * (motion > 3.0) + 0.15 * (bright > 0.002 and colour > 8)
        notes.append(f"means {[round(m) for m in means]}, motion {motion:.1f}, highlights {bright:.3f}, colour {colour:.0f}")
    return {"score": round(score, 3), "passed": score >= 0.999, "notes": "; ".join(notes)}
