"""Score decide/run.py results: accuracy per question, per engine/source, timing, and for decision models the accuracy
of the confident answers (what a pre-screen that only acts on confident answers would get).
Usage: score.py [RESULTS_DIR]"""
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
from studio_config import path as cfg_path  # noqa: E402

DIR = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else cfg_path("STUDIO_EVAL_HOME") / "decide/results"


def pct(xs):
    return f"{100 * sum(xs) / len(xs):.0f}%" if xs else "-"


def frames(rows):
    exp = [r["got"].get("exposure") == r["truth"]["exposure"] for r in rows if r["truth"]["variant"] in ("good", "under", "over", "black")]
    blk = [r["got"].get("black_frame") == r["truth"]["black_frame"] for r in rows]
    dfx = [r["got"].get("defect") == r["truth"]["defect"] for r in rows if r["truth"]["defect"] is not None]
    by_src = {}
    for r in rows:
        if r["truth"]["defect"] is not None:
            by_src.setdefault(r["truth"]["source"], []).append(r["got"].get("defect") == r["truth"]["defect"])
    conf = [r for r in rows if "conf" in r["got"] and r["truth"]["defect"] is not None]
    hi = [r["got"]["defect"] == r["truth"]["defect"] for r in conf if r["got"]["conf"]["defect"] >= 0.8]
    return {"exposure": pct(exp), "black": pct(blk), "defect": pct(dfx), "all": pct(exp + blk + dfx),
            "defect by source": " ".join(f"{k}:{pct(v)}" for k, v in sorted(by_src.items())),
            "defect @conf>=0.8": f"{pct(hi)} of {len(hi)}/{len(conf)}" if conf else "-"}


def logs(rows):
    ok = [r["got"].get("ok") == r["truth"]["ok"] for r in rows]
    fails = [r for r in rows if not r["truth"]["ok"] and r["truth"]["cause"] != "other"]
    cause = [r["got"].get("cause") == r["truth"]["cause"] for r in fails]
    by_cat = {}
    for r in fails:
        by_cat.setdefault(r["truth"]["cause"], []).append(r["got"].get("cause") == r["truth"]["cause"])
    by_eng = {}
    for r in rows:
        by_eng.setdefault(r["truth"]["engine"], []).append(r["got"].get("ok") == r["truth"]["ok"])
    conf = [r for r in fails if "conf" in r["got"]]
    hi = [r["got"]["cause"] == r["truth"]["cause"] for r in conf if r["got"]["conf"]["cause"] >= 0.8]
    return {"ok": pct(ok), "cause (failures)": pct(cause), "by cause": " ".join(f"{k}:{pct(v)}" for k, v in sorted(by_cat.items())),
            "ok by engine": " ".join(f"{k}:{pct(v)}" for k, v in sorted(by_eng.items())),
            "cause @conf>=0.8": f"{pct(hi)} of {len(hi)}/{len(conf)}" if conf else "-"}


def main():
    for p in sorted(DIR.glob("*.jsonl")):
        rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        if not rows:
            continue
        errs = sum(1 for r in rows if r["error"])
        secs = [r["seconds"] for r in rows if not r["error"]]
        s = frames(rows) if p.name.startswith("frames-") else logs(rows)
        timing = f"{statistics.median(secs):.2f}s median, {sum(secs) / 60:.1f} min total" if secs else "-"
        print(f"{p.stem:42} n={len(rows)} err={errs} {timing}")
        print("    " + "  |  ".join(f"{k}: {v}" for k, v in s.items()))


if __name__ == "__main__":
    main()
