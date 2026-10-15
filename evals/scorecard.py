#!/usr/bin/env python3
"""Aggregate a suite directory into scorecard.md: per (agent, model) x task, plus per-area summaries.

  scorecard.py <runs>/suite-YYYYMMDD
Runs flagged in <suite>/excluded.json ({"<phase>/<task>/<agent>/<model>/rep<N>": "reason"}) are left out
and listed at the bottom.
"""
import json
import pathlib
import statistics
import sys
from collections import defaultdict


def main():
    suite = pathlib.Path(sys.argv[1])
    excluded = json.loads((suite / "excluded.json").read_text()) if (suite / "excluded.json").exists() else {}
    rows = []
    for res in sorted(suite.glob("*/results.jsonl")):
        phase = res.parent.name
        for line in res.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            key = f"{phase}/{r['task']}/{r['agent']}/{r['model']}/rep{r['rep']}"
            r["phase"], r["key"] = phase, key
            if key not in excluded:
                rows.append(r)
    cells = defaultdict(list)
    for r in rows:
        cells[(r["area"], r["task"], r["agent"], r["model"])].append(r)
    out = [f"# Capability scorecard: {suite.name}", "",
           "Scores 0-1 per task (graders validated against reference solutions). `pass` = all checks.", ""]
    # per-area summary
    area_cells = defaultdict(list)
    for (area, task, agent, model), rs in cells.items():
        area_cells[(area, agent, model)].extend(rs)
    out += ["## Summary by area", "", "| area | agent | model | runs | passed | mean score | median min | max ctx |",
            "|---|---|---|---|---|---|---|---|"]
    for (area, agent, model), rs in sorted(area_cells.items()):
        secs = [r.get("seconds", 0) / 60 for r in rs]
        ctx = max((r.get("peak_ctx") or 0) for r in rs)
        out.append(f"| {area} | {agent} | {model} | {len(rs)} | {sum(1 for r in rs if r.get('passed'))} | "
                   f"{statistics.mean(r.get('score', 0) for r in rs):.2f} | {statistics.median(secs):.1f} | {ctx or ''} |")
    out += ["", "## Per task", "", "| area | task | agent | model | pass | scores | mean min | peak ctx | notes (last run) |",
            "|---|---|---|---|---|---|---|---|---|"]
    for (area, task, agent, model), rs in sorted(cells.items()):
        rs = sorted(rs, key=lambda r: r["rep"])
        scores = " ".join(f"{r.get('score', 0):.2f}" for r in rs)
        mins = statistics.mean(r.get("seconds", 0) / 60 for r in rs)
        ctx = max((r.get("peak_ctx") or 0) for r in rs)
        note = str(rs[-1].get("notes", "")).replace("|", "/")[:90]
        out.append(f"| {area} | {task} | {agent} | {model} | {sum(1 for r in rs if r.get('passed'))}/{len(rs)} | "
                   f"{scores} | {mins:.1f} | {ctx or ''} | {note} |")
    gpu = suite / "gpu_bench.json"
    if gpu.exists():
        out += ["", "## GPU sharing benchmark (CoolDemo final: 1080p, 8 samples, 150 frames)", "",
                "| scenario | ok | render s | VRAM peak MiB (2060 / 5070 Ti) | notes |", "|---|---|---|---|---|"]
        for name, v in json.loads(gpu.read_text()).items():
            extra = ""
            if "llm_tps_idle" in v:
                extra = f"LLM {v['llm_tps_idle']:.0f} tok/s idle, {', '.join(f'{x:.0f}' for x in v['llm_tps_during_render'] if isinstance(x, (int, float)))} during render"
            if v.get("oom"):
                extra = "out of VRAM"
            out.append(f"| {name} | {v['ok']} | {v.get('render_s') or ''} | {v['vram_peak_mib'].get('0')} / {v['vram_peak_mib'].get('1')} | {extra} |")
    if excluded:
        out += ["", "## Excluded runs", ""] + [f"- `{k}`: {v}" for k, v in excluded.items()]
    (suite / "scorecard.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[:40]))


if __name__ == "__main__":
    main()
