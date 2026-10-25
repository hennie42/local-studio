#!/usr/bin/env python3
"""Collector for the progress dashboard (docs/dashboard-design.md): builds the /api/status JSON from files that
already exist (ledgers, dispatch state, broker spools, job units, Claude Code transcripts), so nothing can drift.

`collect()` returns the whole status dict (the page's contract, documented in docs/dashboard.md); `text_summary()`
and `status_line()` render it for terminals. Read-only except for the usage cache in ~/.cache/studio-status/.
"""
import datetime
import json
import os
import pathlib
import re
import statistics
import subprocess
import time
import urllib.request

from studio_config import cfg, path as cfg_path

HOME = pathlib.Path.home()
STUDIO = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = HOME / ".local/state/studio/projects"
TRANSCRIPTS = HOME / ".claude/projects"
CACHE = HOME / ".cache/studio-status/usage.json"
LLAMA_SWAP_CONFIG = HOME / ".config/llama-swap/config.yaml"
QUEUE = STUDIO / "queue.json"
SHUTDOWN_HOUR = 23            # the user's usual power-off: worst-case ETAs past it turn amber
STALL_GRACE_S = 300           # an attempt this long past its timeout is stalled
JOB_SILENT_S = 30 * 60        # a running job's log silent this long is stalled
WORKER_SILENT_S = 15 * 60     # a worker transcript silent this long (and no GPU job pending) is stalled
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")


def jobs_dir():
    return cfg_path("STUDIO_EVAL_HOME") / "jobs"


def now_iso(t=None):
    return datetime.datetime.fromtimestamp(t or time.time()).isoformat(timespec="seconds")


def parse_time(s):
    try:
        t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return t.timestamp() if t.tzinfo else time.mktime(t.timetuple())


def read_json(p, default=None):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except (OSError, ValueError):
        return default


def read_jsonl(p):
    out = []
    try:
        for line in pathlib.Path(p).read_text().splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def tail_lines(p, n=20, max_bytes=65536):
    try:
        with open(p, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            data = f.read().decode("utf-8", "replace")
    except OSError:
        return []
    lines = [l for l in data.splitlines() if l.strip()]
    return lines[-n:]


def mtime(p):
    try:
        return p.stat().st_mtime
    except OSError:
        return 0


# ---------------------------------------------------------------- processes


def processes():
    """Running studio-worker / studio-dispatch processes: [{kind, pid, start, args}]."""
    out = []
    boot = time.time() - float(pathlib.Path("/proc/uptime").read_text().split()[0])
    tick = os.sysconf("SC_CLK_TCK")
    for d in pathlib.Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            args = (d / "cmdline").read_bytes().split(b"\0")
            stat = (d / "stat").read_text()
        except OSError:
            continue
        args = [a.decode("utf-8", "replace") for a in args if a]
        if len(args) < 2:
            continue
        exe = next((pathlib.Path(a).name for a in args[:2] if pathlib.Path(a).name.startswith("studio-")), None)
        if exe not in ("studio-worker", "studio-dispatch"):
            continue
        start = boot + int(stat.rsplit(")", 1)[1].split()[19]) / tick
        rest = args[args.index(next(a for a in args if pathlib.Path(a).name == exe)) + 1:]
        out.append({"kind": exe, "pid": int(d.name), "start": start, "args": rest})
    return out


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


# ---------------------------------------------------------------- projects


def registered_projects():
    seen, out = set(), []
    for line in (REGISTRY.read_text().splitlines() if REGISTRY.exists() else []):
        p = pathlib.Path(line.strip())
        if line.strip() and p.is_dir() and str(p) not in seen:
            seen.add(str(p))
            out.append(p)
    return out


def ledger_steps(recs):
    """Per step: who made it pass. Worker lines (owner local, no outcome) count attempts; a dispatcher line or a
    verdict carries the outcome; a claude 'add' pass after local attempts is an escalation."""
    steps = {}
    for r in recs:
        s = steps.setdefault(str(r.get("step")), {"id": str(r.get("step")), "attempts": 0, "status": "open",
                                                   "by": None, "model": None, "first_try": False,
                                                   "local_seconds": 0.0, "time": None, "note": ""})
        s["time"] = r.get("time") or s["time"]
        if r.get("owner") == "local" and r.get("outcome") is None and r.get("kind") is None:
            s["attempts"] += 1
            s["local_seconds"] += r.get("seconds") or 0
            s["model"] = r.get("model")
            continue
        out = r.get("outcome")
        if out is None or s["status"] == "pass":
            continue
        s["note"] = (r.get("note") or "")[:160]
        if out == "pass" and r.get("owner") == "claude":
            s.update(status="pass", by="escalated" if s["attempts"] else "director")
        elif out == "pass":   # verdict on a worker attempt, or the dispatcher's check
            if r.get("owner") == "local" and r.get("attempt"):
                s["attempts"] = max(s["attempts"], r["attempt"])
                s["model"] = r.get("model") or s["model"]
            s.update(status="pass", by="local", first_try=s["attempts"] <= 1)
        else:
            s["status"] = "failing"
    return list(steps.values())


def steps_line(steps):
    done = [s for s in steps if s["status"] == "pass"]
    local = [s for s in done if s["by"] == "local"]
    first = sum(1 for s in local if s["first_try"])
    esc = sum(1 for s in done if s["by"] == "escalated")
    director = sum(1 for s in done if s["by"] == "director")
    return {"done": len(done), "local": len(local), "first_try": first, "after_retry": len(local) - first,
            "escalated": esc, "director": director,
            "text": f"{len(local)} of {len(done)} steps done locally: {first} first try, {len(local) - first} after"
                    f" retry, {esc} escalated" + (f", {director} director-owned" if director else "")}


def dispatch_view(p, state, tickets, procs):
    """Ticket board, ETA and stalls for a dispatcher project."""
    order = [t["id"] for t in tickets.get("tickets", [])]
    tmap = {t["id"]: t for t in tickets.get("tickets", [])}
    board, durations = [], []
    for tid in order:
        s = state.get(tid, {"status": "pending", "attempts": []})
        atts = s.get("attempts", [])
        secs = sum(a.get("seconds") or 0 for a in atts)
        if s.get("status") == "pass" and atts:
            durations.append(secs / 60)
        board.append({"id": tid, "title": tmap[tid].get("title", ""), "status": s.get("status", "pending"),
                      "owner": tmap[tid].get("owner", "local"), "deps": tmap[tid].get("deps", []),
                      "attempts": [{"n": a.get("n"), "kind": a.get("kind"), "model": a.get("model"),
                                    "check": a.get("check"), "minutes": round((a.get("seconds") or 0) / 60, 1)}
                                   for a in atts],
                      "max_attempts": tmap[tid].get("attempts", 3), "timeout": tmap[tid].get("timeout", 2400),
                      "minutes": round(secs / 60, 1), "commit": s.get("commit")})
    running = any(pr["kind"] == "studio-dispatch" and pr["args"] and pathlib.Path(pr["args"][0]).resolve() == p
                  for pr in procs)
    remaining = [b for b in board if b["status"] in ("pending", "running") and b["owner"] == "local"]
    eta = None
    if remaining:
        med = statistics.median(durations) if durations else 20.0
        cur = next((b for b in board if b["status"] == "running"), None)
        cur_elapsed = 0.0
        if cur:
            log = tail_lines(p / ".studio/dispatch.log", 50)
            starts = [l for l in log if l[20:].startswith(cur["id"] + " attempt 1 ")]
            t0 = parse_time(starts[-1][:19]) if starts else None
            cur_elapsed = (time.time() - t0) / 60 if t0 else 0
        likely = sum(med for _ in remaining) - min(cur_elapsed, med * 0.9)
        worst = sum(b["max_attempts"] * b["timeout"] / 60 for b in remaining) - cur_elapsed
        done_t, worst_t = time.time() + likely * 60, time.time() + max(worst, 0) * 60
        cutoff = datetime.datetime.now().replace(hour=SHUTDOWN_HOUR, minute=0, second=0).timestamp()
        eta = {"remaining": len(remaining), "median_min": round(med, 1), "likely_min": round(likely),
               "worst_min": round(max(worst, 0)), "done": now_iso(done_t), "worst": now_iso(worst_t),
               "amber": worst_t > cutoff, "running": running}
    return board, eta, running


def worker_activity(p, procs):
    """The running local attempt(s) for this project: from studio-worker processes."""
    out = []
    for pr in procs:
        if pr["kind"] != "studio-worker" or not pr["args"] or pathlib.Path(pr["args"][0]).resolve() != p:
            continue
        a = pr["args"]
        step, timeout = opt(a, "--step", "?"), int(opt(a, "--timeout", "2400"))
        cells = sorted((p / ".studio/workers").glob(f"{step}-*"), key=mtime)
        cell = cells[-1] if cells else None
        n = int(cell.name.rsplit("-", 1)[1]) if cell else None
        transcript = cell / "agent.jsonl" if cell else None
        last = mtime(transcript) if transcript else 0
        elapsed = time.time() - pr["start"]
        out.append({"step": step, "attempt": n, "model": opt(a, "--model") or cfg.get("STUDIO_LOCAL_MODEL", ""),
                    "pid": pr["pid"], "started": now_iso(pr["start"]), "elapsed_s": round(elapsed),
                    "timeout_s": timeout, "silent_s": round(time.time() - last) if last else None,
                    "resume": "--resume" in a})
    return out


def gpu_jobs(p):
    """Broker requests: pending (req without res) and the last few results."""
    spool = p / ".studio/spool"
    pending = []
    for req in sorted((spool / "req").glob("*.json")):
        r = read_json(req, {})
        pending.append({"id": r.get("id", req.stem), "action": r.get("action"), "args": r.get("args", [])[:3],
                        "since": now_iso(mtime(req))})
    results = []
    for res in sorted((spool / "res").glob("*.json"))[-8:]:
        r = read_json(res, {})
        results.append({"id": r.get("id", res.stem), "action": r.get("action"), "exit": r.get("exit"),
                        "seconds": r.get("duration_s"), "time": id_time(r.get("id", res.stem)),
                        "args": [str(x) for x in r.get("args", [])[:2]]})
    return pending, results


def id_time(rid):
    m = re.match(r"(\d{8})-(\d{6})", rid or "")
    if not m:
        return None
    return datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").isoformat()


def latest_image(p):
    """The newest render or screenshot: newest image in the newest of a few known folders."""
    dirs = []
    for base in ("Renders", "out", "screenshots", "shots", ".studio/shots"):
        b = p / base
        if b.is_dir():
            dirs.append(b)
            dirs += [d for d in b.iterdir() if d.is_dir()]
    best = None
    for d in sorted(dirs, key=mtime, reverse=True)[:3]:
        try:
            for e in os.scandir(d):
                if e.name.lower().endswith(IMAGE_EXT) and e.is_file():
                    m = e.stat().st_mtime
                    if not best or m > best[0]:
                        best = (m, e.path)
        except OSError:
            pass
    return {"path": best[1], "time": now_iso(best[0])} if best else None


def project_view(p, procs):
    studio = p / ".studio"
    ledger = read_jsonl(studio / "ledger.jsonl")
    tickets = read_json(p / "tickets.json")
    state = read_json(studio / "dispatch.json", {})
    steps = ledger_steps(ledger)
    workers = worker_activity(p, procs)
    pending, results = gpu_jobs(p)
    v = {"name": p.name, "path": str(p), "engine": "godot" if (p / "project.godot").exists() else "unreal",
         "paused": (studio / "PAUSE").exists(), "steps": steps, "steps_line": steps_line(steps),
         "workers": workers, "gpu_pending": pending, "gpu_recent": results, "board": None, "eta": None,
         "dispatcher": False, "can_pause": tickets is not None, "image": latest_image(p)}
    if tickets:
        v["board"], v["eta"], v["dispatcher"] = dispatch_view(p, state, tickets, procs)
        v["resume_cmd"] = f"studio-job {p.name}-dispatch --project {p} -- studio-dispatch {p} run"
        c = {}
        for b in v["board"]:
            c[b["status"]] = c.get(b["status"], 0) + 1
        v["counts"] = c
    acts = [mtime(studio / f) for f in ("ledger.jsonl", "dispatch.log", "dispatch.json")]
    acts += [mtime(studio / "spool/res"), mtime(studio / "workers")]
    v["last_activity"] = now_iso(max(acts)) if max(acts) else None
    v["active"] = bool(workers or pending or v["dispatcher"])
    return v


# ---------------------------------------------------------------- jobs (studio-job units)


def systemd_show(units, props):
    if not units:
        return {}
    r = subprocess.run(["systemctl", "--user", "show", *units, "-p", ",".join(props)],
                       capture_output=True, text=True)
    out, blocks = {}, r.stdout.split("\n\n")
    for u, b in zip(units, blocks):
        out[u] = dict(l.split("=", 1) for l in b.splitlines() if "=" in l)
    return out


def jobs():
    d = jobs_dir()
    metas = [read_json(f) for f in sorted(d.glob("*.json"))] if d.is_dir() else []
    metas = [m for m in metas if m and m.get("name")]
    units = [f"studio-job-{m['name']}.service" for m in metas]
    info = systemd_show(units, ["ActiveState", "SubState", "Result"])
    out = []
    for m, u in zip(metas, units):
        i = info.get(u, {})
        exit_f = d / f"{m['name']}.exit"
        log = pathlib.Path(m.get("log", d / f"{m['name']}.log"))
        active = i.get("ActiveState") in ("active", "activating", "deactivating")
        if active:
            state = "running"
        elif exit_f.exists() and mtime(exit_f) >= parse_time(m.get("start", "")) - 1:
            code = exit_f.read_text().strip()
            state = "done" if code == "0" else "failed (exit 137: killed, out of memory?)" if code == "137" \
                else f"failed (exit {code})"
        else:   # no exit file: the unit was killed (OOM, stop) before the command returned
            state = "failed (killed)"
        silent = time.time() - mtime(log) if log.exists() else None
        end = mtime(exit_f) if exit_f.exists() and not active else None
        start = parse_time(m.get("start", ""))
        out.append({"name": m["name"], "state": state, "command": m.get("command"), "project": m.get("project"),
                    "start": m.get("start"), "end": now_iso(end) if end else None, "mem": m.get("mem"),
                    "log": str(log),
                    "runtime_s": round((end or time.time()) - start) if start else None,
                    "silent_s": round(silent) if silent is not None else None,
                    "last_line": (tail_lines(log, 1) or [""])[-1][-200:],
                    "stalled": active and silent is not None and silent > JOB_SILENT_S})
    running = [j for j in out if j["state"] == "running"]
    rest = sorted([j for j in out if j["state"] != "running"], key=lambda j: j.get("start") or "", reverse=True)
    return running + rest[:10]


# ---------------------------------------------------------------- machine


def llm_running():
    try:
        with urllib.request.urlopen(cfg.get("STUDIO_LLAMA_URL", "") + "/running", timeout=2) as r:
            return [{"model": m.get("model"), "state": m.get("state")} for m in json.load(r).get("running", [])]
    except (OSError, ValueError):
        return None


def gpus():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    out = []
    for line in r.stdout.splitlines():
        f = [x.strip() for x in line.split(",")]
        if len(f) == 5:
            out.append({"index": int(f[0]), "name": f[1].replace("NVIDIA GeForce ", ""),
                        "mem_used_mb": int(f[2]), "mem_total_mb": int(f[3]), "util": int(f[4])})
    return out


def units_state(names):
    info = systemd_show(names, ["ActiveState"])
    return {n.removesuffix(".service"): info.get(n, {}).get("ActiveState", "unknown") for n in names}


# ---------------------------------------------------------------- usage (Local share)


def local_models():
    """Model names served by llama-swap (top-level keys under `models:`), plus the configured lists."""
    names = set()
    for k in ("STUDIO_GPU_MODELS", "STUDIO_SMALL_MODELS", "STUDIO_LOCAL_MODEL", "STUDIO_LOCAL_SMALL_MODEL"):
        names |= {x.strip() for x in cfg.get(k, "").split(",") if x.strip()}
    try:
        in_models = False
        for line in LLAMA_SWAP_CONFIG.read_text().splitlines():
            if re.match(r"^\S", line):
                in_models = line.startswith("models:")
            elif in_models:
                m = re.match(r"^  ([A-Za-z0-9_.:-]+):\s*$", line) or re.match(r'^  "([^"]+)":\s*$', line)
                if m:
                    names.add(m.group(1))
    except OSError:
        pass
    return names


def classify(model, local):
    if model in local:
        return "local"
    if model and model.startswith("claude-"):
        return "online"
    return "unclassified"


class Usage:
    """Output tokens per (project, day, model) from ~/.claude/projects/**/*.jsonl, read incrementally.

    A local worker's session runs in the project dir (its `cwd`), so it counts for that project. A Claude message
    counts for every registered project its tool calls touch (by path), split evenly. Lines of one message share
    `message.id` and repeat the usage, so a message is counted once, at its highest output_tokens."""

    VERSION = 2

    def __init__(self, projects):
        self.projects = sorted((str(p) for p in projects), key=len, reverse=True)
        c = read_json(CACHE, {})
        if c.get("version") != self.VERSION or sorted(c.get("projects", [])) != sorted(self.projects):
            c = {"version": self.VERSION, "projects": self.projects, "files": {}}
        self.c = c

    def project_of_cwd(self, cwd):
        for p in self.projects:
            if cwd and (cwd == p or cwd.startswith(p + "/")):
                return p
        return None

    def projects_in(self, text):
        return sorted({p for p in self.projects if p in text})

    def scan(self):
        files = self.c["files"]
        live = set()
        for f in TRANSCRIPTS.rglob("*.jsonl"):
            key = str(f)
            live.add(key)
            try:
                st = f.stat()
            except OSError:
                continue
            ent = files.get(key)
            if ent and (ent["ino"] != st.st_ino or st.st_size < ent["off"]):
                ent = None
            if not ent:
                ent = files[key] = {"ino": st.st_ino, "off": 0, "buckets": {}, "msg": None, "sessions": {}}
            if st.st_size > ent["off"]:
                self.read_new(f, ent)
        for k in set(files) - live:
            del files[k]
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.c))
        tmp.replace(CACHE)

    def read_new(self, f, ent):
        with open(f, "rb") as fh:
            fh.seek(ent["off"])
            data = fh.read()
        end = data.rfind(b"\n") + 1      # a half-written last line waits for the next poll
        for raw in data[:end].splitlines():
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            if d.get("type") != "assistant":
                continue
            m = d.get("message") or {}
            mid, model = m.get("id") or d.get("uuid"), m.get("model")
            if not model or model == "<synthetic>":
                continue
            out_tok = (m.get("usage") or {}).get("output_tokens") or 0
            touched = self.projects_in(json.dumps([c.get("input") for c in m.get("content", [])
                                                   if c.get("type") == "tool_use"]))
            cur = ent["msg"]
            if cur and cur["id"] == mid:
                cur["tok"] = max(cur["tok"], out_tok)
                cur["proj"] = sorted(set(cur["proj"]) | set(touched))
            else:
                self.commit(ent)
                ts = parse_time(d.get("timestamp", "")) or time.time()
                ent["msg"] = {"id": mid, "model": model, "tok": out_tok, "proj": touched,
                              "cwd_proj": self.project_of_cwd(d.get("cwd")),
                              "day": datetime.date.fromtimestamp(ts).isoformat(), "ts": ts,
                              "session": d.get("sessionId") or f.stem}
        ent["off"] += end

    def commit(self, ent):
        msg = ent.get("msg")
        if not msg:
            return
        ent["msg"] = None
        self.add(ent, msg)

    def add(self, ent, msg):
        # a local model's session counts for its working dir; Claude's messages for the projects they touch
        tg = msg["proj"] if msg["model"].startswith("claude-") or not msg.get("cwd_proj") else [msg["cwd_proj"]]
        share = msg["tok"] / len(tg) if tg else msg["tok"]
        for p in (tg or [""]):
            k = f"{p}|{msg['day']}|{msg['model']}"
            b = ent["buckets"].setdefault(k, [0, 0])
            b[0] += share
            b[1] += 1
            s = ent["sessions"].setdefault(f"{p}|{msg['day']}|{msg['model']}", [msg["ts"], msg["ts"]])
            s[0], s[1] = min(s[0], msg["ts"]), max(s[1], msg["ts"])

    def totals(self, project=None, day=None):
        """{model: {tokens, messages, sessions, minutes}} for one project (path), one day, or all projects."""
        out = {}
        for ent in self.c["files"].values():
            entries = list(ent["buckets"].items())
            pend = {}
            if ent.get("msg"):
                tmp = {"buckets": {}, "sessions": {}}
                self.add(tmp, ent["msg"])
                entries += list(tmp["buckets"].items())
                pend = tmp["sessions"]
            spans = dict(ent["sessions"])
            for k, v in pend.items():
                s = spans.get(k)
                spans[k] = [min(s[0], v[0]), max(s[1], v[1])] if s else v
            for k, (tok, n) in entries:
                p, d, model = k.split("|", 2)
                if not p or (project and p != project) or (day and d != day):
                    continue
                o = out.setdefault(model, {"tokens": 0.0, "messages": 0, "sessions": 0, "minutes": 0.0})
                o["tokens"] += tok
                o["messages"] += n
            for k, (a, b) in spans.items():
                p, d, model = k.split("|", 2)
                if not p or (project and p != project) or (day and d != day) or model not in out:
                    continue
                out[model]["sessions"] += 1
                out[model]["minutes"] += (b - a) / 60
        return out


def share_view(totals, local_set):
    """Donut slices: one per model, <1% merged into 'other local' / 'other online'; fixed shade index per model."""
    total = sum(v["tokens"] for v in totals.values())
    if not total:
        return {"total_tokens": 0, "local_pct": None, "slices": []}
    rows = []
    for model, v in totals.items():
        rows.append({"model": model, "group": classify(model, local_set), "tokens": round(v["tokens"]),
                     "messages": v["messages"], "attempts": v["sessions"], "minutes": round(v["minutes"]),
                     "pct": 100 * v["tokens"] / total})
    merged, small = [], {}
    for r in rows:
        if r["pct"] < 1 and r["group"] != "unclassified":
            o = small.setdefault(r["group"], {"model": f"other {r['group']}", "group": r["group"], "tokens": 0,
                                              "messages": 0, "attempts": 0, "minutes": 0, "pct": 0.0,
                                              "other": True})
            for k in ("tokens", "messages", "attempts", "minutes", "pct"):
                o[k] += r[k]
        else:
            merged.append(r)
    merged += small.values()
    local_order = sorted(local_set)
    for r in merged:   # shade = stable position of the model in its group (alphabetical), not its rank today
        if r["group"] == "local" and not r.get("other"):
            r["shade"] = local_order.index(r["model"]) % 6
        elif r["group"] == "online" and not r.get("other"):
            r["shade"] = sum(ord(c) for c in r["model"]) % 6
        else:
            r["shade"] = 9
        r["pct"] = round(r["pct"], 2)
    merged.sort(key=lambda r: -r["tokens"])
    local_pct = sum(r["pct"] for r in merged if r["group"] == "local")
    return {"total_tokens": round(total), "local_pct": round(local_pct, 1), "slices": merged}


# ---------------------------------------------------------------- feed


def feed(projects, job_list, limit=60):
    ev = []
    for v in projects:
        p = pathlib.Path(v["path"])
        for line in tail_lines(p / ".studio/dispatch.log", 15):
            t = line[:19]
            msg = line[20:]
            kind = "escalated" if "ESCALATED" in msg else "fail" if "FAIL" in msg else \
                "pass" if "PASS" in msg else "info"
            ev.append({"time": t, "project": p.name, "kind": kind, "text": msg})
        for r in read_jsonl(p / ".studio/ledger.jsonl")[-15:]:
            if r.get("owner") == "local" and r.get("outcome") is None and r.get("kind") is None:
                text = f"step {r['step']} attempt {r.get('attempt')} ({r.get('model')}) finished in " \
                       f"{round((r.get('seconds') or 0) / 60)} min, exit {r.get('exit')}"
                kind = "info"
            elif r.get("kind") == "verdict":
                text, kind = f"step {r['step']} verdict {r['outcome']}: {r.get('note', '')}", r["outcome"]
            elif r.get("owner") == "claude":
                text, kind = f"step {r['step']} done by the director: {r.get('note', '')}", "director"
            else:
                continue   # dispatcher lines duplicate dispatch.log
            ev.append({"time": r.get("time"), "project": p.name, "kind": kind, "text": text[:220]})
        for r in v["gpu_recent"][-4:]:
            ev.append({"time": r["time"], "project": p.name, "kind": "fail" if r["exit"] else "gpu",
                       "text": f"GPU {r['action']} {' '.join(r['args'])} exit {r['exit']}"
                               + (f" ({round(r['seconds'])} s)" if r.get("seconds") else "")})
    for j in job_list:
        ev.append({"time": j["start"], "project": j.get("project") and pathlib.Path(j["project"]).name,
                   "kind": "info", "text": f"job {j['name']} started"})
        if j["state"] != "running" and j.get("end"):
            ev.append({"time": j["end"], "project": j.get("project") and pathlib.Path(j["project"]).name,
                       "kind": "pass" if j["state"] == "done" else "fail", "text": f"job {j['name']} {j['state']}"})
    ev = [e for e in ev if e.get("time")]
    ev.sort(key=lambda e: e["time"], reverse=True)
    return ev[:limit]


# ---------------------------------------------------------------- assemble


def stalls(projects, job_list):
    out = []
    for v in projects:
        busy_gpu = bool(v["gpu_pending"])
        for w in v["workers"]:
            if w["elapsed_s"] > w["timeout_s"] + STALL_GRACE_S:
                out.append({"project": v["name"], "what": f"step {w['step']} attempt {w['attempt']}",
                            "why": f"{round(w['elapsed_s'] / 60)} min, past its {w['timeout_s'] // 60} min timeout"})
            elif w["silent_s"] and w["silent_s"] > WORKER_SILENT_S and not busy_gpu:
                out.append({"project": v["name"], "what": f"step {w['step']} attempt {w['attempt']}",
                            "why": f"worker silent for {round(w['silent_s'] / 60)} min"})
    for j in job_list:
        if j["stalled"]:
            out.append({"project": j.get("project") and pathlib.Path(j["project"]).name, "what": f"job {j['name']}",
                        "why": f"log silent for {round(j['silent_s'] / 60)} min"})
        elif j["state"].startswith("failed") and j["runtime_s"] is not None and \
                time.time() - (parse_time(j["start"]) or 0) - j["runtime_s"] < 6 * 3600:
            out.append({"project": j.get("project") and pathlib.Path(j["project"]).name, "what": f"job {j['name']}",
                        "why": j["state"]})
    return out


def alerts(projects, job_list, stall_list, feed_list, window_h=6):
    """Things worth a notification and the title badge: stalls, escalations, finished runs and jobs (recent)."""
    cutoff = time.time() - window_h * 3600
    out = [{"key": f"stall|{x['project']}|{x['what']}", "level": "red", "title": f"{x['project'] or ''}: "
            f"{x['what']} stalled".strip(": "), "detail": x["why"], "time": now_iso()} for x in stall_list]
    for e in feed_list:
        if (parse_time(e["time"]) or 0) < cutoff:
            continue
        if e["kind"] == "escalated":
            out.append({"key": f"esc|{e['project']}|{e['time']}", "level": "red",
                        "title": f"{e['project']}: {e['text'].split(' after')[0]}", "detail": e["text"],
                        "time": e["time"]})
        elif e["text"].startswith("dispatch stopped"):
            out.append({"key": f"stop|{e['project']}|{e['time']}", "level": "info",
                        "title": f"{e['project']}: run finished", "detail": e["text"], "time": e["time"]})
    for j in job_list:
        if j.get("end") and (parse_time(j["end"]) or 0) >= cutoff:
            bad = j["state"] != "done"
            out.append({"key": f"job|{j['name']}|{j['end']}", "level": "red" if bad else "info",
                        "title": f"job {j['name']} {j['state']}", "detail": j["last_line"][:160],
                        "time": j["end"]})
    out.sort(key=lambda a: (a["level"] != "red", a["time"]), reverse=False)
    return out


def queue():
    q = read_json(QUEUE, {"items": []})
    items = q.get("items", [])
    open_items = [i for i in items if i.get("status") not in ("done", "dropped")]
    hours = sum(float(i.get("estimate_h") or 0) for i in open_items)
    return {"items": items, "open": len(open_items), "estimate_h": round(hours, 1),
            "needs_user": sum(1 for i in open_items if i.get("needs_user")), "updated": q.get("updated")}


def collect(usage_scan=True, range_=None):
    procs = processes()
    projs = registered_projects()
    views = [project_view(p, procs) for p in projs]
    views.sort(key=lambda v: (not v["active"], -(parse_time(v["last_activity"] or "") or 0)))
    active = views[0] if views else None
    job_list = jobs()
    eval_pause = cfg_path("STUDIO_EVAL_HOME") / "runs/PAUSE"
    u = Usage(projs)
    if usage_scan:
        u.scan()
    local_set = local_models()
    today = datetime.date.today().isoformat()
    share = {"project": share_view(u.totals(project=active["path"]), local_set) if active else None,
             "today": share_view(u.totals(day=today), local_set),
             "all": share_view(u.totals(), local_set)}
    if active:
        share["project"]["steps_line"] = active["steps_line"]
        share["project"]["name"] = active["name"]
    st = stalls(views, job_list)
    fd = feed(views, job_list)
    return {
        "version": 1, "time": now_iso(),
        "active_project": active["name"] if active else None,
        "projects": views,
        "jobs": job_list,
        "eval_pause": {"paused": eval_pause.exists(), "path": str(eval_pause)},
        "machine": {"gpus": gpus(), "llm": llm_running(),
                    "services": units_state(["studio-broker.service", "llama-swap.service",
                                             "studio-status.service"])},
        "queue": queue(),
        "share": share,
        "stalls": st,
        "alerts": alerts(views, job_list, st, fd),
        "feed": fd,
    }


def fmt_min(m):
    m = round(m)
    return f"{m // 60}h{m % 60:02d}" if m >= 60 else f"{m}m"


def project_line(v):
    if v["board"]:
        c = v["counts"]
        s = f"{v['name']} {c.get('pass', 0)}/{len(v['board'])}"
        if c.get("escalated"):
            s += f" ({c['escalated']} esc)"
    else:
        s = f"{v['name']} {v['steps_line']['done']} steps"
    for w in v["workers"]:
        s += f" · {w['step']} a{w['attempt']} {w['model'].split('-')[0]} {fmt_min(w['elapsed_s'] / 60)}"
    if v["gpu_pending"]:
        s += f" · GPU {v['gpu_pending'][0]['action']}"
    if v["eta"]:
        s += f" · ETA {v['eta']['done'][11:16]}" + (" (worst {})".format(v["eta"]["worst"][11:16]))
    if v["paused"]:
        s += " · PAUSED"
    return s


def status_line(s):
    """One line for the Claude Code status line."""
    parts = [project_line(v) for v in s["projects"] if v["active"]]
    parts += [f"job {j['name']} {fmt_min(j['runtime_s'] / 60)}" for j in s["jobs"] if j["state"] == "running"]
    if s["stalls"]:
        parts.insert(0, f"⚠ {len(s['stalls'])} stalled")
    return " | ".join(parts) or "studio idle"


def text_summary(s):
    L = [f"studio status {s['time'][11:16]}"]
    if s["stalls"]:
        L += [f"  ⚠ STALLED {x['project'] or ''} {x['what']}: {x['why']}" for x in s["stalls"]]
    act = [v for v in s["projects"] if v["active"]]
    L.append("now: " + (", ".join(project_line(v) for v in act) if act else "no worker, dispatcher or GPU job"))
    for j in s["jobs"]:
        if j["state"] == "running":
            L.append(f"  job {j['name']}: running {fmt_min(j['runtime_s'] / 60)}, last: {j['last_line'][:90]}")
    m = s["machine"]
    llm = ", ".join(x["model"] for x in (m["llm"] or [])) or ("none" if m["llm"] is not None else "llama-swap down")
    L.append("machine: " + " · ".join(f"{g['name']} {g['mem_used_mb'] / 1024:.1f}/{g['mem_total_mb'] / 1024:.0f} GB"
                                      f" {g['util']}%" for g in m["gpus"]) + f" · LLM {llm}")
    sh = s["share"]["project"]
    if sh and sh["local_pct"] is not None:
        L.append(f"local share ({sh['name']}): {sh['local_pct']}% of {sh['total_tokens']:,} output tokens; "
                 f"{sh['steps_line']['text']}")
    q = s["queue"]
    L.append(f"queue: {q['open']} open, ~{q['estimate_h']} h, {q['needs_user']} need you")
    for i in [i for i in q["items"] if i.get("status") not in ("done", "dropped")][:5]:
        L.append(f"  - {i['item']} ({i.get('status')}, ~{i.get('estimate_h', '?')} h)")
    L.append("recent:")
    L += [f"  {e['time'][5:16].replace('T', ' ')} {e['project'] or '':16} {e['text'][:100]}" for e in s["feed"][:6]]
    return "\n".join(L)
