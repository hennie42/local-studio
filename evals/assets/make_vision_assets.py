#!/usr/bin/env python3
"""make_vision_assets.py [out_dir]: synthetic test frames for the vision tasks (labels true by construction).

Draws an isometric neon cube grid (a stand-in for a rendered night scene) at 960x540, then derives:
  good_1..3 / clean_1..3   correct exposure (different layouts and palettes)
  over_1..3                overexposed (gain + clipping: washed-out highlights)
  under_1..2               underexposed (dim but visible)
  black_1..2               (nearly) black frames
  tex_1..3                 a magenta/black checkerboard patch (Unreal's missing-texture look)
  band_1..2                a black horizontal band across the picture
and writes labels.json. Deterministic (fixed seeds).
"""
import json
import math
import pathlib
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 960, 540
PALETTES = [  # (centre colour, middle, edge) in 0..1
    ((0.95, 0.95, 1.0), (0.2, 0.85, 1.0), (1.0, 0.15, 0.75)),
    ((1.0, 0.85, 0.4), (1.0, 0.3, 0.5), (0.35, 0.2, 1.0)),
    ((0.8, 1.0, 0.9), (0.2, 1.0, 0.5), (0.1, 0.4, 1.0)),
]


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def scene(seed, palette, n=11, tile=30):
    """Isometric grid of cubes whose heights follow a ripple; colours by distance from the centre; soft glow."""
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), (4, 4, 8))
    d = ImageDraw.Draw(img)
    cx, cy = W / 2 + rnd.uniform(-60, 60), H / 2 - 40 + rnd.uniform(-20, 20)
    phase = rnd.uniform(0, math.tau)
    cubes = []
    for i in range(n):
        for j in range(n):
            u, v = i - n / 2 + 0.5, j - n / 2 + 0.5
            r = math.hypot(u, v) / (n / 2)
            h = tile * (0.6 + 1.4 * max(0.0, math.cos(r * 3.0 + phase)) * (1 - r * 0.5))
            col = lerp(palette[0], palette[1], min(r * 1.8, 1)) if r < 0.55 else lerp(palette[1], palette[2], min((r - 0.55) * 2.2, 1))
            cubes.append((u + v, u, v, h, col))
    for _, u, v, h, col in sorted(cubes):          # back to front
        x, y = cx + (u - v) * tile, cy + (u + v) * tile * 0.5
        top = [(x, y - h - tile * 0.5), (x + tile, y - h), (x, y - h + tile * 0.5), (x - tile, y - h)]
        left = [(x - tile, y - h), (x, y - h + tile * 0.5), (x, y + tile * 0.5), (x - tile, y)]
        right = [(x + tile, y - h), (x, y - h + tile * 0.5), (x, y + tile * 0.5), (x + tile, y)]
        for poly, shade in ((left, 0.55), (right, 0.35), (top, 1.0)):
            c = tuple(int(255 * min(1.0, ch * shade)) for ch in col)
            d.polygon(poly, fill=c, outline=(0, 0, 0))
    glow = img.filter(ImageFilter.GaussianBlur(14))
    a = np.asarray(img, np.float32) + 0.6 * np.asarray(glow, np.float32)
    return np.clip(a, 0, 255)


def save(a, path):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path, quality=92)


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "vision")
    out.mkdir(parents=True, exist_ok=True)
    base = [scene(10 + k, PALETTES[k % 3]) for k in range(6)]
    labels = {"exposure": {}, "defect": {}}
    for k in range(3):
        save(base[k], out / f"good_{k + 1}.jpg")
        labels["exposure"][f"good_{k + 1}.jpg"] = {"exposure": "good", "black_frame": False}
        a = np.clip(base[(k + 1) % 6] * 3.2 + 60, 0, 255)                       # washed out
        save(a, out / f"over_{k + 1}.jpg")
        labels["exposure"][f"over_{k + 1}.jpg"] = {"exposure": "overexposed", "black_frame": False}
    for k in range(2):
        save(base[3 + k] * 0.18, out / f"under_{k + 1}.jpg")                     # dim but visible
        labels["exposure"][f"under_{k + 1}.jpg"] = {"exposure": "underexposed", "black_frame": False}
        save(np.zeros_like(base[0]) + k, out / f"black_{k + 1}.jpg")             # a black frame: nothing rendered
        #   (a darkened scene still shows faint structure and reads as "very underexposed", not as a black frame)
        labels["exposure"][f"black_{k + 1}.jpg"] = {"exposure": "underexposed", "black_frame": True}
    for k in range(3):
        save(base[3 + k], out / f"clean_{k + 1}.jpg")
        labels["defect"][f"clean_{k + 1}.jpg"] = "none"
        a = base[(k + 4) % 6].copy()                                             # checkerboard patch
        x0, y0, s = 120 + 220 * k, 150 + 40 * k, 24
        for yy in range(6):
            for xx in range(8):
                a[y0 + yy * s:y0 + (yy + 1) * s, x0 + xx * s:x0 + (xx + 1) * s] = (255, 0, 255) if (xx + yy) % 2 == 0 else (0, 0, 0)
        save(a, out / f"tex_{k + 1}.jpg")
        labels["defect"][f"tex_{k + 1}.jpg"] = "missing_texture"
    for k in range(2):
        a = base[k * 2].copy()                                                   # black band
        y0 = 150 + 120 * k
        a[y0:y0 + 70] = 8
        save(a, out / f"band_{k + 1}.jpg")
        labels["defect"][f"band_{k + 1}.jpg"] = "black_band"
    (out / "labels.json").write_text(json.dumps(labels, indent=1) + "\n")
    print(f"wrote {len(labels['exposure']) + len(labels['defect'])} images + labels.json to {out}")


if __name__ == "__main__":
    main()
