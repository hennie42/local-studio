"""Vision: classify exposure and black frames of rendered frames (ground truth from controlled variants)."""
import json
import pathlib
import re

AREA = "vision"
TITLE = "Vision: exposure (under/good/over) + black-frame detection, 10 frames"
KIND = "direct"
NEEDS_VISION = True
TIMEOUT = 1800
ASSETS = pathlib.Path(__file__).resolve().parents[1] / "assets/vision"

QUESTION = """You are the render QA step of a CG animation pipeline. Judge this rendered frame.
Answer with ONLY a JSON object, no other text:
{"exposure": "underexposed" | "good" | "overexposed", "black_frame": true | false}
"black_frame" means the frame is essentially entirely black (render failure). Dark but visible content is
"underexposed"; large clipped/blown-out white or neon areas with lost detail are "overexposed"."""


def parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def run_direct(model, api):
    labels = json.loads((ASSETS / "labels.json").read_text())["exposure"]
    correct, details, secs = 0, [], 0.0
    for name, want in labels.items():
        r = api.chat([api.image(ASSETS / name), {"type": "text", "text": QUESTION}], max_tokens=3000)
        secs += r["seconds"]
        got = parse(r["text"]) or {}
        ok_exp = got.get("exposure") == want["exposure"]
        ok_black = bool(got.get("black_frame")) == want["black_frame"]
        correct += ok_exp + ok_black
        if not (ok_exp and ok_black):
            details.append(f"{name}: got {got.get('exposure')}/{got.get('black_frame')}")
    total = 2 * len(labels)
    return {"score": round(correct / total, 3), "passed": correct >= total - 2, "seconds_model": round(secs, 1),
            "notes": f"{correct}/{total} correct" + (f"; misses: {', '.join(details[:4])}" if details else "")}
