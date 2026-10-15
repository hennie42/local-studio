#!/usr/bin/env python3
"""Capability test harness for the local models.

  harness.py run    --tasks 'coding_*' --models bonsai2-27b,qwen3.6-35b-a3b --agents claude,opencode --reps 3
  harness.py report <run-dir>
  harness.py list

Each task is a module in tasks/ defining:
  AREA, TITLE, KIND ("agent" | "direct"), TIMEOUT (s)
  agent tasks:  PROMPT (str), setup(ws) -> None, grade(ws) -> dict(score 0..1, passed, notes)
  direct tasks: run_direct(model, api) -> dict(score, passed, notes, ...)   (api = Api instance)
Agent runs are sandboxed: claude-local via Claude Code's sandbox, opencode via bubblewrap
(--standalone so its tools run inside the sandbox). GPU/engine work goes through `studio`.
"""
import argparse
import base64
import datetime
import fnmatch
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
from studio_agents import AGENTS, MODEL_CTX, has_vision, is_online, parse_stream, worker_env  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
TASKS_DIR = HERE / "tasks"
from studio_config import path as cfg_path  # noqa: E402
RUNS_ROOT = pathlib.Path(os.environ.get("EVAL_RUNS", str(cfg_path("STUDIO_EVAL_HOME") / "runs")))
LLAMA = os.environ.get("LLAMA_URL", "http://127.0.0.1:8080")
STUDIO_BIN = HERE.parent / "bin"
REGISTRY = pathlib.Path.home() / ".local/state/studio/projects"

# context window per model (must match llama-swap -c); claude-local needs it for auto-compact
# ------------------------------------------------------------------ helpers
class Api:
    """Direct OpenAI-compatible calls for non-agent tasks (vision, long context)."""

    def __init__(self, model):
        self.model = model

    def chat(self, content, max_tokens=4000, timeout=1800, **extra):
        body = {"model": self.model, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": content}], **extra}
        t = time.time()
        req = urllib.request.Request(LLAMA + "/v1/chat/completions", json.dumps(body).encode(),
                                     {"content-type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=timeout))
        msg = r["choices"][0]["message"]
        return {"text": (msg.get("content") or "").strip(), "seconds": round(time.time() - t, 1),
                "usage": r.get("usage", {}), "timings": r.get("timings", {})}

    @staticmethod
    def image(path):
        data = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
        mime = "image/png" if str(path).endswith(".png") else "image/jpeg"
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}


def load_task(name):
    if str(TASKS_DIR) not in sys.path:
        sys.path.insert(0, str(TASKS_DIR))  # tasks share helpers (_ue.py, _media.py)
    spec =importlib.util.spec_from_file_location(f"task_{name}", TASKS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.NAME = name
    return mod


def all_tasks():
    return sorted(p.stem for p in TASKS_DIR.glob("*.py") if not p.stem.startswith("_"))


def ensure_model(model):
    """Load the model (llama-swap swaps within the GPU group) and wait until it answers."""
    if is_online(model):   # Anthropic API: nothing to load
        return True
    for _ in range(3):
        try:
            Api(model).chat("Reply with OK.", max_tokens=16, timeout=600)
            return True
        except Exception as e:
            print(f"   ! loading {model} failed: {e}", flush=True)
            time.sleep(5)
    return False


def ensure_services(local=True):
    if local:
        subprocess.run([str(pathlib.Path.home() / ".local/bin/ensure-llama-swap")], check=True)
    if subprocess.run(["systemctl", "--user", "is-active", "-q", "studio-broker"]).returncode != 0:
        subprocess.run(["systemctl", "--user", "start", "studio-broker"], check=True)


def register_project(ws):
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    lines = REGISTRY.read_text().splitlines() if REGISTRY.exists() else []
    if str(ws) not in lines:
        with REGISTRY.open("a") as f:
            f.write(f"{ws}\n")


def unregister_project(ws):
    if REGISTRY.exists():
        keep = [l for l in REGISTRY.read_text().splitlines() if l.strip() and l.strip() != str(ws)]
        REGISTRY.write_text("".join(f"{l}\n" for l in keep))


def git(ws, *args):
    subprocess.run(["git", "-c", "user.name=eval", "-c", "user.email=eval@local", *args], cwd=ws,
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ------------------------------------------------------------------ runner
def run_one(task, agent, model, rep, run_dir):
    rec = {"task": task.NAME, "area": task.AREA, "agent": agent, "model": model, "rep": rep,
           "started": datetime.datetime.now().isoformat(timespec="seconds")}
    cell = run_dir / task.NAME / agent / model / f"rep{rep}"
    cell.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        if task.KIND == "direct":
            res = task.run_direct(model, Api(model))
            rec.update(res)
        else:
            ws = cell / "ws"
            if ws.exists():
                shutil.rmtree(ws)
            ws.mkdir()
            (ws / ".studio").mkdir()
            task.setup(ws)
            git(ws, "init", "-q")
            git(ws, "add", "-A")
            git(ws, "commit", "-qm", "task setup", "--allow-empty")
            register_project(ws)
            argv, env_extra = AGENTS[agent](ws, model, task.PROMPT)
            env = worker_env(env_extra)
            out = cell / "agent.jsonl"
            with open(out, "w") as f, open(cell / "agent.err", "w") as ferr:
                try:
                    limit = min(task.TIMEOUT, MAX_TIMEOUT) if MAX_TIMEOUT else task.TIMEOUT
                    p = subprocess.run(argv, cwd=ws, env=env, stdout=f, stderr=ferr, stdin=subprocess.DEVNULL,
                                       timeout=limit)
                    rec["agent_exit"] = p.returncode
                except subprocess.TimeoutExpired:
                    rec["agent_exit"] = 124
            rec["agent_seconds"] = round(time.time() - t0, 1)
            met = parse_stream(agent, out)
            rec.update({k: met[k] for k in ("turns", "peak_ctx", "agent_error")})
            subprocess.run(["git", "add", "-A"], cwd=ws, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            diff = subprocess.run(["git", "diff", "--cached", "--stat"], cwd=ws, capture_output=True, text=True).stdout
            rec["diff_stat"] = diff.strip().splitlines()[-1] if diff.strip() else "no changes"
            res = task.grade(ws)
            rec.update(res)
            unregister_project(ws)
    except Exception as e:
        rec.update(score=0.0, passed=False, notes=f"harness error: {e}", trace=traceback.format_exc()[-1500:])
    rec["seconds"] = round(time.time() - t0, 1)
    (cell / "result.json").write_text(json.dumps(rec, indent=1))
    with open(run_dir / "results.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    status = "PASS" if rec.get("passed") else "fail"
    print(f"   {status} {task.NAME:28} {agent:8} {model:18} rep{rep} score={rec.get('score', 0):.2f} "
          f"{rec['seconds']:>6.0f}s turns={rec.get('turns')} ctx={rec.get('peak_ctx')} | {str(rec.get('notes', ''))[:90]}",
          flush=True)
    return rec


MAX_TIMEOUT = 0


def cmd_run(a):
    global MAX_TIMEOUT
    MAX_TIMEOUT = a.max_timeout
    names = [n for n in all_tasks() if any(fnmatch.fnmatch(n, pat) for pat in a.tasks.split(","))]
    if not names:
        sys.exit("no tasks match")
    tasks = [load_task(n) for n in names]
    run_dir = pathlib.Path(a.out) if a.out else RUNS_ROOT / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(json.dumps(vars(a), indent=1))
    models = a.models.split(",")
    ensure_services(local=any(not is_online(m) for m in models))
    agents = a.agents.split(",")
    print(f"run dir: {run_dir}\ntasks: {', '.join(names)}", flush=True)
    skip_file = run_dir.parent / "skip_models.txt"  # lets a running suite drop models without editing run_suite.sh
    skip = set(skip_file.read_text().split()) if skip_file.exists() else set()
    pause_file = run_dir.parent / "PAUSE"  # touch it to stop cleanly before the next run; delete it to resume
    # Resume: every (task, agent, model, rep) that already has a result is skipped.
    done = set()
    if (run_dir / "results.jsonl").exists():
        for line in (run_dir / "results.jsonl").read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["task"], r["agent"], r["model"], r["rep"]))
    for model in models:  # group by model so each model loads once
        if model in skip:
            print(f"== model {model}: skipped (listed in {skip_file})", flush=True)
            continue
        todo = [(task, agent, rep) for task in tasks
                if not (getattr(task, "NEEDS_VISION", False) and not has_vision(model))
                and not (task.KIND == "direct" and is_online(model))   # direct tasks call llama-swap's API
                for agent in (["direct"] if task.KIND == "direct" else agents)
                for rep in range(1, a.reps + 1)
                if (task.NAME, agent, model, rep) not in done]
        if not todo:
            print(f"== model {model}: all runs already done", flush=True)
            continue
        print(f"== model {model}: loading ({len(todo)} runs to do)", flush=True)
        if not ensure_model(model):
            print(f"   ! skipping {model}: could not load", flush=True)
            continue
        for task, agent, rep in todo:
            if pause_file.exists():
                print(f"== paused ({pause_file} exists); rerun the same command to resume", flush=True)
                sys.exit(3)
            run_one(task, agent, model, rep, run_dir)
    cmd_report(argparse.Namespace(run_dir=str(run_dir)))


def cmd_report(a):
    run_dir = pathlib.Path(a.run_dir)
    if not (run_dir / "results.jsonl").exists():
        print("no results")
        return
    recs = [json.loads(l) for l in (run_dir / "results.jsonl").read_text().splitlines() if l.strip()]
    cells = {}
    for r in recs:
        cells.setdefault((r["area"], r["task"], r["agent"], r["model"]), []).append(r)
    lines = ["| area | task | agent | model | pass | mean score | mean s | peak ctx |", "|---|---|---|---|---|---|---|---|"]
    for (area, task, agent, model), rs in sorted(cells.items()):
        n = len(rs)
        passed = sum(1 for r in rs if r.get("passed"))
        score = sum(r.get("score", 0) for r in rs) / n
        secs = sum(r.get("seconds", 0) for r in rs) / n
        ctx = max((r.get("peak_ctx") or 0) for r in rs)
        lines.append(f"| {area} | {task} | {agent} | {model} | {passed}/{n} | {score:.2f} | {secs:.0f} | {ctx} |")
    table = "\n".join(lines)
    (run_dir / "scorecard.md").write_text(table + "\n")
    print(table)


def cmd_regrade(a):
    """Re-score stored agent runs with the current graders (no model re-run). The original score is kept in
    `score_original`; results.jsonl is rewritten (backup alongside)."""
    run_dir = pathlib.Path(a.run_dir)
    path = run_dir / "results.jsonl"
    recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    pats = a.tasks.split(",")
    changed = 0
    for r in recs:
        if r["agent"] == "direct" or not any(fnmatch.fnmatch(r["task"], p) for p in pats):
            continue
        ws = run_dir / r["task"] / r["agent"] / r["model"] / f"rep{r['rep']}" / "ws"
        if not ws.is_dir():
            continue
        res = load_task(r["task"]).grade(ws)
        if res.get("score") != r.get("score") or res.get("passed") != r.get("passed"):
            r.setdefault("score_original", r.get("score"))
            changed += 1
            print(f"  {r['task']:18} {r['agent']:8} {r['model']:16} rep{r['rep']}: {r.get('score')} -> {res.get('score')} | {res.get('notes')}")
        r.update(res)
    path.with_suffix(".jsonl.bak").write_text(path.read_text())
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))
    print(f"regraded; {changed} changed (backup: {path.with_suffix('.jsonl.bak').name})")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--tasks", default="*")
    r.add_argument("--models", required=True)
    r.add_argument("--agents", default="claude")
    r.add_argument("--reps", type=int, default=1)
    r.add_argument("--out")
    r.add_argument("--max-timeout", type=int, default=0, help="cap each task's TIMEOUT (s)")
    rp = sub.add_parser("report")
    rp.add_argument("run_dir")
    sub.add_parser("list")
    rg = sub.add_parser("regrade")
    rg.add_argument("run_dir")
    rg.add_argument("--tasks", default="*")
    a = ap.parse_args()
    if a.cmd == "run":
        cmd_run(a)
    elif a.cmd == "report":
        cmd_report(a)
    elif a.cmd == "regrade":
        cmd_regrade(a)
    else:
        for n in all_tasks():
            t = load_task(n)
            print(f"{n:30} {t.AREA:15} {t.KIND:7} {t.TITLE}")


if __name__ == "__main__":
    main()
