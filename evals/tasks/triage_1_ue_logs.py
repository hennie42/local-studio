"""Log triage: find the root cause and fix in real (spliced) Unreal Engine logs. A small-model role test."""
import json
import pathlib
import re

AREA = "triage"
TITLE = "UE log triage: root cause + fix from 4 real crash/failure logs"
KIND = "direct"
TIMEOUT = 1800
ASSETS = pathlib.Path(__file__).resolve().parents[1] / "assets/logs"

QUESTION = """This is the tail of an Unreal Engine 5.8 log from a scripted, headless workflow that failed.
Find the root cause. Answer with ONLY a JSON object, no other text:
{"root_cause": "<one sentence naming the exact failing setting/function/line>", "fix": "<one concrete fix>"}

LOG:
"""


def run_direct(model, api):
    truth = json.loads((ASSETS / "truth.json").read_text())
    pts, notes, secs = 0.0, [], 0.0
    for name, want in truth.items():
        log = (ASSETS / name).read_text()
        r = api.chat([{"type": "text", "text": QUESTION + log}], max_tokens=3000)
        secs += r["seconds"]
        m = re.search(r"\{.*\}", r["text"], re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            got = {}
        cause, fix = str(got.get("root_cause", "")).lower(), str(got.get("fix", "")).lower()
        c_ok = any(k.lower() in cause for k in want["cause_any"])
        f_ok = any(k.lower() in fix for k in want["fix_any"])
        pts += 0.5 * c_ok + 0.5 * f_ok
        notes.append(f"{name[5:-4]}:{'C' if c_ok else 'c'}{'F' if f_ok else 'f'}")
    return {"score": round(pts / len(truth), 3), "passed": pts >= len(truth) - 0.5, "seconds_model": round(secs, 1),
            "notes": " ".join(notes) + "  (C/F = cause/fix correct)"}
