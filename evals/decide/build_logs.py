"""Log set from real broker jobs (Godot, Unreal, Blender): the excerpt a director would read, the exit code as truth
for "did it work", and a rule-based failure category. Usage: build_logs.py OUT.json"""
import glob
import json
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
from studio_config import path as cfg_path  # noqa: E402

SIGNAL = re.compile(r"Error|error:|Fatal|Traceback|Exception|FAILED|warning: |LogPython: |BUILD_|RENDER_|STUDIO_|GAME_|GODOT_|"
                    r"godot-lint|godot-check|\.gd:\d+|Result: |Total execution time|BUILD SUCCESSFUL|AutomationTool exiting", re.I)
NOISE = re.compile(r"LogConfig: Set CVar|ErrorTest|Error test|Error with|UnifiedErrorTest|Icon_error|LogConsoleManager")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
CODE = re.compile(r"Parse Error|SCRIPT ERROR|Compilation failed|Traceback|SyntaxError|LogPython: Error|\berror: |"
                  r"errors generated|OtherCompilationError|RulesError|NameError|AttributeError|TypeError", re.I)
TEST = re.compile(r"\b\d+ FAILED|FAILED:|TEST_FAIL|assert|result=lose|GAME_TIMEOUT|expected .* got", re.I)


def excerpt(text, max_lines=60):
    """Same shape for passes and failures: signal lines, then the last 15 lines."""
    lines = [ANSI.sub("", l) for l in text.splitlines()]
    hits = [l for l in lines if SIGNAL.search(l) and not NOISE.search(l)]
    tail = lines[-15:]
    return "\n".join(l[:300] for l in hits[-(max_lines - 15):] + ["..."] + tail)


def category(r, full):
    if r.get("exit") == 0:
        return "ok"
    if r.get("exit") == 2 and (r.get("error") or not full.strip() or "not a" in full[:300]):
        return "bad_request"
    if CODE.search(full):
        return "code_error"
    if TEST.search(full):
        return "test_failure"
    if r.get("exit") in (124, 143, 137):
        return "timeout"
    return "other"


def main(out):
    items = []
    roots = (cfg_path("STUDIO_PROJECTS_UE"), cfg_path("STUDIO_PROJECTS_GODOT"))
    for p in sorted(p for r in roots for p in glob.glob(f"{r}/*/.studio/spool/res/*.json")):
        try:
            r = json.loads(pathlib.Path(p).read_text())
        except (OSError, json.JSONDecodeError):
            continue
        root = pathlib.Path(p).parents[3]
        log = root / r["log"] if r.get("log") else None
        full = log.read_text(errors="replace") if log and log.exists() else (r.get("error") or "")
        if r.get("action") in ("godot-import", "rm") or not full.strip():
            continue
        items.append({"id": r["id"], "project": root.name, "action": r["action"], "args": " ".join(r.get("args", []))[:200],
                      "exit": r.get("exit"), "category": category(r, full), "text": excerpt(full)})
    rng = random.Random(7)
    by = {}
    for it in items:
        by.setdefault((it["category"], it["action"].split("-")[0]), []).append(it)
    pick = []
    for (cat, eng), xs in sorted(by.items()):
        n = 6 if cat == "ok" else 14
        pick += rng.sample(xs, min(n, len(xs)))
    pathlib.Path(out).write_text(json.dumps(pick, indent=1))
    from collections import Counter
    print(len(items), "jobs;", len(pick), "picked:", dict(Counter((x["category"], x["action"].split("-")[0]) for x in pick)))


if __name__ == "__main__":
    main(sys.argv[1])
