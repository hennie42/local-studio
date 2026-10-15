#!/usr/bin/env python3
"""godot_scorecard.py <run-dir> [out.md]: Godot suite scorecard (scores, time, and HOW each worker worked:
reference-bundle lookups, checks, headless vs GPU game runs) + a contact sheet of every clip run."""
import collections
import json
import pathlib
import re
import subprocess
import sys

TASKS = ["godot_1_migrate", "godot_2_logic", "godot_3_platformer", "godot_4_clip"]
SHORT = {"godot_1_migrate": "port 3->4", "godot_2_logic": "race logic", "godot_3_platformer": "platformer+export",
         "godot_4_clip": "Movie Maker clip"}


def usage(agent_jsonl):
    """Count tool use from the worker's stream: godot-ref lookups by kind, checks, headless/windowed runs, renders."""
    c = collections.Counter()
    if not agent_jsonl.exists():
        return c
    for line in agent_jsonl.read_text(errors="replace").splitlines():
        if '"tool_use"' not in line:
            continue
        for m in re.finditer(r'"input":\{(.*?)\}\}', line):
            inp = m.group(1)
            for kind in ("cookbook", "api", "demos", "docs"):
                if f"godot-ref/{kind}" in inp:
                    c[f"ref_{kind}"] += 1
            if "studio godot-check" in inp:
                c["check"] += 1
            if "studio godot-play" in inp:
                c["play_headless" if "--headless" in inp else "play_gpu"] += 1
            if "studio godot-movie" in inp:
                c["movie"] += 1
            if "studio godot-export" in inp:
                c["export"] += 1
    return c


def main():
    run = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else run / "scorecard.md"
    rows = [json.loads(l) for l in (run / "results.jsonl").read_text().splitlines() if l.strip()]
    models = list(dict.fromkeys(r["model"] for r in rows))
    runs = {}
    for r in rows:
        runs.setdefault((r["model"], r["task"]), []).append(r)
    by = {k: v[-1] for k, v in runs.items()}   # the latest run, for the tool-use table
    lines = [f"# Godot capability suite: {run.name}", "",
             "Scores per run (rep 1, rep 2), mean minutes per run in brackets; Claude Code harness, same prompts/time limits; Godot GPU jobs on a second GPU (worker LLM "
             "never unloaded), headless game runs available. Score 0..1 (pass = 1.0).", "",
             "| model | " + " | ".join(SHORT[t] for t in TASKS) + " | mean | passed | worker min per 4 tasks |",
             "|---|" + "---|" * (len(TASKS) + 3)]
    for m in models:
        cells, scores, mins, passed, n = [], [], 0.0, 0, 0
        for t in TASKS:
            rs = runs.get((m, t), [])
            if not rs:
                cells.append("-")
                continue
            ok = sum(bool(r.get("passed")) for r in rs)
            scores += [r["score"] for r in rs]
            mins += sum((r.get("seconds") or 0) for r in rs) / 60
            passed += ok
            n += len(rs)
            sc = " ".join(f"{r['score']:.2f}" for r in rs)
            cells.append(f"{'**' if ok == len(rs) else ''}{sc}{'**' if ok == len(rs) else ''}"
                         f" ({sum((r.get('seconds') or 0) for r in rs) / 60 / len(rs):.0f}m)")
        mean = sum(scores) / len(scores) if scores else 0
        lines.append(f"| {m} | " + " | ".join(cells) + f" | {mean:.2f} | {passed}/{n} | {mins / max(n / 4, 1):.0f} |")
    lines += ["", "## How they worked (tool use per run)", "",
              "| model | task | turns | peak ctx | cookbook | api | demos | docs | checks | headless runs | GPU runs | renders | exports | notes |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        for t in TASKS:
            r = by.get((m, t))
            if not r:
                continue
            u = usage(run / t / "claude" / m / "rep1" / "agent.jsonl")
            lines.append(f"| {m} | {SHORT[t]} | {r.get('turns') or '-'} | {r.get('peak_ctx') or r.get('ctx') or '-'} | "
                         f"{u['ref_cookbook']} | {u['ref_api']} | {u['ref_demos']} | {u['ref_docs']} | {u['check']} | "
                         f"{u['play_headless']} | {u['play_gpu']} | {u['movie']} | {u['export']} | "
                         f"{(r.get('notes') or '')[:140].replace('|', '/')} |")
    # contact sheet of the clips (first/middle/last frame per model) for a visual verdict
    strips = []
    for m in models:
        d = run / "godot_4_clip" / "claude" / m / "rep1" / "ws" / "Renders" / "clip"
        frames = sorted(d.glob("frame*.png")) if d.is_dir() else []
        if len(frames) >= 3:
            pick = [frames[0], frames[len(frames) // 2], frames[-1]]
            strip = run / f"clip_{m}.jpg"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *sum((["-i", str(f)] for f in pick), []),
                            "-filter_complex",
                            "[0]scale=480:-1[a];[1]scale=480:-1[b];[2]scale=480:-1[c];[a][b][c]hstack=3,"
                            f"drawtext=fontfile=/usr/share/fonts/TTF/DejaVuSans-Bold.ttf:text='{m}':x=10:y=10:"
                            "fontsize=22:fontcolor=white:box=1:boxcolor=black@0.5", str(strip)], check=False)
            if strip.exists():
                strips.append(strip)
    if strips:
        sheet = run / "clips_contact_sheet.jpg"
        args = sum((["-i", str(s)] for s in strips), [])
        if len(strips) > 1:
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args, "-filter_complex",
                            "".join(f"[{i}]" for i in range(len(strips))) + f"vstack={len(strips)}", str(sheet)],
                           check=False)
        else:
            sheet.write_bytes(strips[0].read_bytes())
        lines += ["", f"Clip frames (first/middle/last per model): {sheet}"]
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
