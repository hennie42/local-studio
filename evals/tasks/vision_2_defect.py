"""Vision: spot render defects (missing-texture checkerboard, black band) vs clean frames."""
import json
import pathlib
import re

AREA = "vision"
TITLE = "Vision: detect render defects (missing texture / black band / none), 8 frames"
KIND = "direct"
NEEDS_VISION = True
TIMEOUT = 1800
ASSETS = pathlib.Path(__file__).resolve().parents[1] / "assets/vision"

QUESTION = """You are the render QA step of a CG animation pipeline. Look for rendering defects in this frame.
Answer with ONLY a JSON object, no other text:
{"defect": "none" | "missing_texture" | "black_band", "where": "<short location or empty>"}
"missing_texture" = a magenta/black checkerboard patch (Unreal's missing-material pattern).
"black_band" = a solid black horizontal strip across the image that is not part of the scene."""


def parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def run_direct(model, api):
    labels = json.loads((ASSETS / "labels.json").read_text())["defect"]
    correct, misses, secs = 0, [], 0.0
    for name, want in labels.items():
        r = api.chat([api.image(ASSETS / name), {"type": "text", "text": QUESTION}], max_tokens=3000)
        secs += r["seconds"]
        got = (parse(r["text"]) or {}).get("defect")
        if got == want:
            correct += 1
        else:
            misses.append(f"{name}->{got}")
    return {"score": round(correct / len(labels), 3), "passed": correct >= len(labels) - 1, "seconds_model": round(secs, 1),
            "notes": f"{correct}/{len(labels)} correct" + (f"; misses: {', '.join(misses)}" if misses else "")}
