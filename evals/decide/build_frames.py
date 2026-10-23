"""Frame QA set from real accepted frames: each base frame in 6 controlled variants, so the truth is known by construction.
Usage: build_frames.py OUT_DIR"""
import json
import pathlib
import random
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
from studio_config import path as cfg_path  # noqa: E402

UE, GD = cfg_path("STUDIO_PROJECTS_UE"), cfg_path("STUDIO_PROJECTS_GODOT")
EV = min((cfg_path("STUDIO_EVAL_HOME") / "runs").glob("godot-*"), default=None)  # the first Godot suite run
BASES = (
    [("ue-dpt", UE / f"DontPanicTrailer/Renders/final60_169/final.{i:04d}.png") for i in (150, 330, 520, 700, 880, 1060, 1250)]
    + [("ue-neon", UE / f"NeonRain/Renders/final/Main.{i:04d}.png") for i in (60, 260, 460)]
    + [("gd-dpi", GD / f"DontPanicIsland/shots/{n}.png") for n in ("leaderboard_menu", "leaderboard_win", "numbers_a", "numbers_b")]
    + [("gd-eval", EV / "clip_bonsai2-27b.jpg"), ("gd-eval", EV / "godot_3_platformer/claude/bonsai2-27b/rep1/ws/shots/finish.png")]
)


def to_lin(a):
    return (a / 255.0) ** 2.2


def to_srgb(a):
    return (np.clip(a, 0, 1) ** (1 / 2.2) * 255).round().astype(np.uint8)


def checker_patch(a, rng):
    h, w, _ = a.shape
    pw, ph = int(w * rng.uniform(0.18, 0.28)), int(h * rng.uniform(0.18, 0.28))
    x, y = rng.randrange(0, w - pw), rng.randrange(0, h - ph)
    cell = max(8, pw // 10)
    yy, xx = np.mgrid[0:ph, 0:pw]
    mag = ((yy // cell + xx // cell) % 2 == 0)
    patch = np.zeros((ph, pw, 3), np.uint8)
    patch[mag] = (255, 0, 255)
    a = a.copy()
    a[y:y + ph, x:x + pw] = patch
    return a


def band(a, rng):
    h = a.shape[0]
    bh = int(h * rng.uniform(0.08, 0.13))
    y = rng.randrange(int(h * 0.1), int(h * 0.9) - bh)
    a = a.copy()
    a[y:y + bh] = 0
    return a


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    labels = {}
    for i, (src, path) in enumerate(BASES):
        im = Image.open(path).convert("RGB")
        im = im.resize((1280, round(1280 * im.height / im.width)), Image.LANCZOS)
        a = np.asarray(im)
        lin = to_lin(a)
        noise = np.random.default_rng(i).normal(0, 0.004, lin.shape)
        variants = {
            "good": (a, "good", False, "none"),
            "under": (to_srgb(lin * 0.06), "underexposed", False, None),
            "over": (to_srgb(lin * 6.0), "overexposed", False, None),
            "black": (to_srgb(np.abs(lin * 0.0004 + noise * 0.05)), "underexposed", True, None),
            "tex": (checker_patch(a, rng), "good", False, "missing_texture"),
            "band": (band(a, rng), "good", False, "black_band"),
        }
        for v, (arr, exposure, black, defect) in variants.items():
            name = f"{i:02d}_{src}_{v}.jpg"
            Image.fromarray(arr).save(out / name, quality=90)
            labels[name] = {"base": i, "source": src, "variant": v, "exposure": exposure, "black_frame": black, "defect": defect}
    (out / "labels.json").write_text(json.dumps(labels, indent=1))
    print(f"{len(labels)} frames -> {out}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
