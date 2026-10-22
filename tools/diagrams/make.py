"""make.py OUT_DIR: write the docs/diagrams/*.drawio sources (one style for all). Then:
   DRAWIO=~/opt/drawio/drawio.AppImage tools/diagrams/export.sh OUT_DIR && cp OUT_DIR/*.drawio.svg docs/diagrams/
Small edits can also be made directly in draw.io on docs/diagrams/*.drawio.svg (the diagram is embedded); then this
script is out of date for that diagram."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib import D
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
B = lambda t, s="": f"<b>{t}</b>" + (f"<br><font style='font-size:11px'>{s}</font>" if s else "")
LEG = [("you", "you", False), ("claude", "Claude (frontier model)", False), ("local", "local model / worker", False),
       ("broker", "broker + engines", False), ("check", "checks / graders", False), ("file", "files in the project", False),
       ("gpu", "GPU", False), ("plain", "planned, not built yet", True)]

# 1 -------------------------------------------------------------- architecture: who talks to whom
d = D("architecture", 1260, 820)
you = d.actor(40, 215, "You")
api = d.box(150, 30, 220, 70, B("Anthropic API", "Claude models: the director;<br>optionally online workers"), "claude",
            shape="ellipse;")
dirr = d.box(150, 190, 220, 120, B("Director", "Claude Code + /studio skill<br>plans · delegates · reviews ·<br>retries · takes over"), "claude")
led = d.doc(150, 360, 220, 70, B("Ledger + git", "every attempt, verdict, commit"), "file")
sb = d.box(430, 150, 330, 300, "<b>Sandbox</b>: the project folder only, no network<br>except the model endpoint, no GPUs, no engines",
           "check", extra="verticalAlign=bottom;spacingBottom=6;fillColor=#fff8f8;", planned=True, fs=12)
wk = d.box(465, 175, 260, 90, B("Worker", "Claude Code on a local or online model<br>one step / ticket at a time"), "local")
prj = d.doc(465, 300, 260, 80, B("Project repo", "PLAN.md · code · assets ·<br>AGENTS.md · godot-ref/ · .studio/spool"), "file")
br = d.box(830, 150, 170, 210, B("studio-broker", "user service<br>vetted actions only"), "broker")
eng = {}
for i, (k, s) in enumerate([("Godot 4.7", "check · play · movie · export"), ("Unreal 5.8", "Python · render · build"),
                            ("Blender", "models · renders"), ("ffmpeg + audio", "edit · encode · synth")]):
    eng[k] = d.box(1060, 150 + i * 55, 170, 45, B(k, s), "broker", fs=12)
ls = d.box(465, 510, 260, 70, B("llama-swap :8080", "OpenAI + Anthropic API, loads models on demand"), "local")
g1 = d.box(330, 640, 290, 80, B("RTX 5070 Ti 16 GB", "Gemma 4 26B-A4B (worker) · Bonsai 2 27B (retry)<br>Unreal renders (LLM unloaded)"), "gpu")
g2 = d.box(760, 640, 290, 80, B("RTX 2060 6 GB", "small model (triage, pre-screen)<br>Godot rendering"), "gpu")
d.edge(you, dirr, "brief,<br>interview answers")
d.edge(dirr, api, "", dashed=True, both=True)
d.edge(dirr, wk, "ticket prompt", exit=(1, 0.3), entry=(0, 0.4))
d.edge(wk, dirr, "result + claims", exit=(0, 0.75), entry=(1, 0.65), dashed=True)
d.edge(dirr, led, "verdict, commit")
d.edge(dirr, prj, "review: run checks,<br>read diff, view frames", exit=(1, 0.95), entry=(0, 0.5), color="#b85450")
d.edge(wk, prj, "edits")
d.edge(wk, br, "studio &lt;action&gt;<br>(request in spool)", exit=(1, 0.5), entry=(0, 0.17))
for i, k in enumerate(eng):
    d.edge(br, eng[k], "", exit=(1, round((22.5 + i * 55) / 210, 3)), entry=(0, 0.5))
d.edge(wk, ls, "", exit=(0, 0.85), entry=(0, 0.5), pts=[(445, 251), (445, 545)])
d.text(452, 470, 120, 20, "local model", fs=12)
d.edge(wk, api, "online model (optional)", dashed=True, exit=(0.5, 0), entry=(1, 0.5), pts=[(595, 65)])
d.edge(ls, g1, "", exit=(0.2, 1), entry=(0.65, 0))
d.edge(ls, g2, "", exit=(0.8, 1), entry=(0.2, 0), pts=[(673, 600), (818, 600)])
d.edge(br, g2, "Godot jobs", exit=(0.75, 1), entry=(0.7, 0), dashed=True)
d.edge(br, g1, "UE renders: unload the LLM first", exit=(0.25, 1), entry=(0.85, 0), dashed=True, pts=[(872, 625), (576, 625)])
d.legend(40, 745, [LEG[i] for i in (0, 1, 2, 3, 5, 6)], per_row=6, step=200)
(OUT / "architecture.drawio").write_text(d.xml())

# 2 -------------------------------------------------------------- production process (swimlanes)
d = D("production-process", 1500, 760)
lanes = [("You", "you"), ("Director (Claude)", "claude"), ("Dispatcher (script)", "plain"), ("Workers (local)", "local"),
         ("Checks (broker + graders)", "check")]
LH, LX, LW = 130, 20, 1460
for i, (n, r) in enumerate(lanes):
    d.box(LX, 20 + i * LH, LW, LH, "", r, shape="rounded=0;", extra="opacity=35;", planned=(r == "plain"))
    d.box(LX, 20 + i * LH, 40, LH, f"<b>{n}</b>", r, shape="rounded=0;", extra="horizontal=0;", fs=12, planned=(r == "plain"))
y = lambda i, h=70: 20 + i * LH + (LH - h) / 2
idea = d.box(80, y(0), 120, 70, B("Idea", "one line"), "you")
gr = d.box(250, y(0, 80), 170, 80, B("/grill-me interview", "rounds of numbered questions,<br>each with a recommendation"), "you")
ok = d.box(470, y(0), 130, 70, B("Approve brief"), "you")
yn = d.box(650, y(0), 170, 70, B("Yes / no per asset set", "local review page"), "you", planned=True)
ap = d.box(455, y(1, 80), 150, 80, B("Asset pass", "CC0 sets that fit the<br>brief, style lock"), "claude", planned=True)
watch = d.box(1300, y(0), 150, 70, B("Watch / play", "the deliverable"), "you")
brief = d.doc(250, y(1, 80), 170, 80, B("BRIEF.md", "every decision settled,<br>nothing assumed"), "file")
plan = d.box(650, y(1, 90), 170, 90, B("Task graph", "small tickets: files, helpers,<br>acceptance checks, deps"), "claude")
rev = d.box(1065, y(1, 80), 170, 80, B("Milestone review", "frames, playtest,<br>creative calls"), "claude")
dlv = d.box(1300, y(1), 150, 70, B("Deliver", "mp4 / build + report"), "claude")
esc = d.box(880, y(1, 80), 140, 80, B("Escalation", "sharper retry, other<br>model, or take over"), "claude")
run = d.box(650, y(2), 190, 70, B("Run ready tickets", "dependency order"), "plain", planned=True)
bon = d.box(880, y(2), 140, 70, B("Best-of-N", "2-3 attempts"), "plain", planned=True)
wkk = d.box(650, y(3, 80), 190, 80, B("Do the ticket", "edit, then studio check /<br>render / play"), "local")
chk = d.box(880, y(4, 80), 140, 80, B("Acceptance checks", "tests · godot-check ·<br>autopilot · frame stats"), "check")
com = d.box(1080, y(4), 140, 70, B("Commit", "+ ledger entry"), "file")
d.edge(idea, gr); d.edge(gr, brief, "answers"); d.edge(brief, ok, "", exit=(1, 0.3), entry=(0, 0.5), pts=[(437, 199), (437, 65)])
d.edge(ok, ap, "go"); d.edge(ap, yn, "", exit=(1, 0.3), entry=(0, 0.5), dashed=True)
d.edge(yn, plan, "approved assets", exit=(0.5, 1), entry=(0.5, 0))
d.edge(plan, run, "", exit=(0.5, 1), entry=(0.39, 0)); d.edge(run, wkk, "ticket")
d.edge(wkk, chk, "", exit=(0.5, 1), entry=(0, 0.5), pts=[(745, 585)])
d.edge(chk, com, "pass"); d.edge(chk, bon, "fail", exit=(0.8, 0), entry=(0.8, 1), color="#b85450")
d.edge(bon, wkk, "retry", exit=(0.3, 1), entry=(1, 0.5), pts=[(922, 455)], color="#b85450")
d.edge(bon, esc, "all failed", exit=(0.5, 0), entry=(0.5, 1), color="#b85450")
d.edge(esc, run, "new / fixed<br>ticket", exit=(0, 0.8), entry=(0.95, 0), pts=[(830, 239)], dashed=True)
d.edge(com, rev, "milestone done", exit=(0.5, 0), entry=(0.5, 1))
d.edge(rev, dlv); d.edge(dlv, watch, "", exit=(0.5, 0), entry=(0.5, 1))
d.text(80, 680, 1300, 60, "<b>Today:</b> the director runs the loop itself (plan, delegate one step, review). <b>Planned (dashed):</b> "
       "an asset pass (free CC0 assets you approve per set, docs/assets-design.md) and a plain dispatcher runs the task graph so Claude only plans, handles escalations and reviews milestones; "
       "local tokens are free, so failed tickets are retried before Claude spends any.", fs=12)
(OUT / "production-process.drawio").write_text(d.xml())

# 3 -------------------------------------------------------------- handover sequence for one step
d = D("step-handover", 1200, 900)
cols = [("Director", "claude", 120), ("Worker (sandbox)", "local", 380), ("studio-broker", "broker", 640),
        ("Engine", "broker", 860), ("Project: git + ledger", "file", 1080)]
for n, r, x in cols:
    d.box(x - 90, 20, 180, 50, f"<b>{n}</b>", r)
    d.line(x, 70, x, 860)
X = {n: x for n, _, x in cols}
steps = [
    ("Director", "Worker (sandbox)", "1  ticket prompt: goal, exact files, helpers to use, the check to run", False),
    ("Worker (sandbox)", "Project: git + ledger", "2  edit files (only inside the project)", False),
    ("Worker (sandbox)", "studio-broker", "3  studio godot-check / ue-render / ... (JSON request in .studio/spool)", False),
    ("studio-broker", "Engine", "4  run the vetted action", False),
    ("Engine", "studio-broker", "5  full log to .studio/logs", True),
    ("studio-broker", "Worker (sandbox)", "6  filtered summary (errors with file:line)", True),
    ("Worker (sandbox)", "Director", "7  'done' + its own check output (a claim, not proof)", True),
    ("Director", "studio-broker", "8  re-run the check independently", False),
    ("studio-broker", "Director", "9  result", True),
    ("Director", "Project: git + ledger", "10  read git diff, look at rendered frames", False),
]
yy = 110
for a, b, lab, ret in steps:
    xa, xb = X[a], X[b]
    if xa == xb:
        continue
    d.arrow(xa, yy, xb, yy, "", dashed=ret, color="#b85450" if lab.startswith(("8", "9", "10")) else "#333333")
    d.text(min(xa, xb) + 10, yy - 24, 560, 22, lab, fs=12)
    yy += 52
alt = d.box(40, yy, 1120, 200, "", "plain", shape="rounded=0;", extra="fillColor=none;", fs=12)
d.text(48, yy + 4, 300, 20, "<b>verdict</b>", fs=12)
d.box(60, yy + 34, 340, 70, B("pass", "commit + ledger entry: model, minutes,<br>turns, context, diff stats"), "local")
d.box(420, yy + 34, 340, 70, B("fail, approach fine", "one sharper retry: the exact error,<br>the helper to use"), "check")
d.box(780, yy + 34, 360, 70, B("fail again / wrong approach", "retry on the other model (Bonsai),<br>or the director does the step itself"), "check")
d.arrow(X["Director"], yy + 140, X["Project: git + ledger"], yy + 140, "11  verdict + commit (every attempt is logged, also failures)")
d.text(40, yy + 215, 1120, 50, "The worker never sees the conversation, graders or other projects; the director trusts nothing it "
       "hasn't checked itself. <code>studio-ledger &lt;project&gt; summary</code> reports how much was done locally.", fs=12)
(OUT / "step-handover.drawio").write_text(d.xml())

# 4 -------------------------------------------------------------- routing: which task goes where
d = D("routing", 1200, 700)
tasks = [("Coding, Unreal Python/C++, renders,<br>Blender, ffmpeg, audio", 0), ("Godot (GDScript, scenes, exports)", 0),
         ("Vision pre-screen of frames", 0), ("Retry after a failed approach", 1), ("Huge inputs > 100K tokens", 1),
         ("Unreal log triage", 1), ("Quick first-pass triage", 2), ("Brief, plan, shot design, final visual<br>verdicts, creative calls", 3)]
models = [d.box(560, 40, 280, 110, B("Gemma 4 26B-A4B", "default worker · 19/20 agent runs ·<br>8/8 Godot · vision 1.00 · 68 tok/s"), "local"),
          d.box(560, 200, 280, 110, B("Bonsai 2 27B", "different model family · 19/20 ·<br>188K recall 3/3 · triage 0.88 · ~3x slower"), "local"),
          d.box(560, 360, 280, 90, B("Small model on the 2060", "Spark-X2.5-4B (fast); Gemma 4 E4B<br>best small triage (0.69), not routed"), "local"),
          d.box(560, 500, 280, 90, B("Claude (director)", "never delegated"), "claude")]
for i, (t, m) in enumerate(tasks):
    tid = d.box(40, 30 + i * 72, 330, 56, t, "plain", fs=12)
    d.edge(tid, models[m], "", exit=(1, 0.5), entry=(0, 0.5))
gp1 = d.box(930, 120, 230, 90, B("RTX 5070 Ti 16 GB", "one big model at a time<br>(llama-swap group)"), "gpu")
gp2 = d.box(930, 360, 230, 90, B("RTX 2060 6 GB", "small model, Godot rendering"), "gpu")
gp3 = d.box(930, 500, 230, 90, B("Anthropic API", ""), "claude", shape="ellipse;")
d.edge(models[0], gp1, ""); d.edge(models[1], gp1, ""); d.edge(models[2], gp2, ""); d.edge(models[3], gp3, "")
d.text(40, 620, 1120, 60, "Source: <code>~/.config/studio/routing.json</code>, written from the hardware profile by install.sh; "
       "measured in evals/scorecard-gemma-qwen.md and evals/scorecard-godot.md. Qwen3.6-35B-A3B stays installed as a "
       "fallback worker (16/20).", fs=12)
(OUT / "routing.drawio").write_text(d.xml())

# 5 -------------------------------------------------------------- model evaluation pipeline
d = D("model-evaluation", 1300, 520)
st = [("Scout", "Hugging Face releases (unsloth,<br>bartowski, labs) that fit a GPU slot<br>+ community reports", "claude", False),
      ("Gate", "catalog entry, download,<br>smoke test: loads, calls tools,<br>sees images", "check", False),
      ("Quick screen", "a few cheap tasks, 1 run,<br>vs the slot's current model<br>(~30 min)", "check", False),
      ("Full suite", "2 runs per task, the current<br>model re-run on the same<br>tooling (overnight)", "check", False),
      ("Scorecard", "one table + a<br>recommendation", "file", False),
      ("You decide", "switch or keep", "you", False)]
ids = []
for i, (t, s, r, p) in enumerate(st):
    ids.append((d.doc if r == "file" else d.box)(30 + i * 210, 120, 180, 120, B(t, s), r, planned=p))
for a, b in zip(ids, ids[1:]):
    d.edge(a, b, "")
rt = d.doc(1080, 330, 180, 70, B("routing.json", "profile + docs/models.md"), "file")
d.edge(ids[-1], rt, "switch")
drop = d.box(420, 330, 220, 60, B("Drop", "noted in the catalog, never routed"), "plain")
d.edge(ids[1], drop, "fails", exit=(0.5, 1), entry=(0.2, 0), color="#b85450")
d.edge(ids[2], drop, "far behind", exit=(0.5, 1), entry=(0.8, 0), color="#b85450")
prod = d.box(30, 330, 260, 90, B("Real productions", "lessons (spatial maths, autopilots,<br>reloads) become new eval tasks"), "claude")
d.edge(prod, ids[3], "new tasks", exit=(1, 0.8), entry=(0.5, 1), dashed=True, pts=[(720, 402)])
d.text(30, 20, 1240, 80, "<b>Public benchmarks pick the candidates; our own suite picks the winner.</b> Graders are validated "
       "against reference solutions before any model runs. You read one page at the end; the scout and screens run unattended.", fs=13)
(OUT / "model-evaluation.drawio").write_text(d.xml())
print("ok")
