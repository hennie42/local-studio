#!/usr/bin/env python3
"""NeonClip: model comparison clip (user request: Bonsai vs Qwen3.6; Gemma 4 added later).

Same plan, same prompts, same mechanical checks for each model, in separate projects. The director's (Claude's)
involvement is identical by construction: this script runs every step on the local worker, checks it mechanically,
and on a failed check resumes the worker ONCE with the check output (no hand-written diagnosis, no takeover). Failed
steps stay failed; the pipeline carries on with whatever exists. The final render -> rain comp -> encode -> mux is
mechanical too. Then a side-by-side mp4 with stats.

  neonclip.py run qwen|bonsai      # one model's pipeline (resumable: finished steps are skipped)
  neonclip.py final qwen|bonsai    # mechanical final render/comp/encode/mux
  neonclip.py compare [keys...]    # side-by-side (2 or 3 models) + stats
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
from studio_config import path as cfg_path  # noqa: E402

PROMPTS = pathlib.Path(__file__).resolve().parent / "neonclip"   # PLAN template + step prompts (in the repo)
RUN = cfg_path("STUDIO_EVAL_HOME") / "neonclip-run"
UPROJECTS = cfg_path("STUDIO_PROJECTS_UE")
MODELS = {"qwen": ("qwen3.6-35b-a3b", "NeonClipQwen", "Qwen3.6-35B-A3B"),
          "bonsai": ("bonsai2-27b", "NeonClipBonsai", "Bonsai 2 27B"),
          "gemma": ("gemma4-26b-a4b", "NeonClipGemma", "Gemma 4 26B-A4B")}   # added later
STEPS = [("tex", "01-tex.md"), ("towers", "02-towers.md"), ("import", "03-import.md"), ("city", "04-city.md"),
         ("seq", "05-seq.md"), ("lookdev", "06-lookdev.md"), ("rain", "07-rain.md"), ("score", "08-score.md")]
TIMEOUT = 4500   # per worker attempt, same for both models
FOLLOWUP = """The acceptance check for this step failed. This is the check's output:

{output}

Fix the problem so that this check passes (the director runs the check after you finish, on the files in the
project). Then report what you changed."""
SANDBOX = str(pathlib.Path(__file__).resolve().parents[2] / "bin/studio-sandbox")  # not on PATH
FONT = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/TTF/DejaVuSansMono.ttf"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(RUN / "driver.log", "a") as f:
        f.write(line + "\n")


def sh(cmd, cwd=None, timeout=None, env=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, timeout=timeout, capture_output=True, text=True, env=env)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        return 124, f"timeout after {timeout} s\n{(e.stdout or b'')[-2000:]}"


def state_path(key):
    return RUN / f"{key}.json"


def load_state(key):
    p = state_path(key)
    return json.loads(p.read_text()) if p.exists() else {"model": MODELS[key][0], "steps": {}}


def save_state(key, st):
    state_path(key).write_text(json.dumps(st, indent=1))


# ------------------------------------------------------------------ project setup
def project(key):
    return UPROJECTS / MODELS[key][1]


def setup(key):
    P, name = project(key), MODELS[key][1]
    if not P.exists():
        rc, out = sh(["studio-new", name])
        if rc:
            raise SystemExit(out)
        (P / "PLAN.md").write_text((PROMPTS / "PLAN.template.md").read_text().replace("{NAME}", name))
        if not sh(["git", "config", "user.email"], cwd=P)[1].strip():   # no global identity: a local one
            sh(["git", "config", "user.name", "studio"], cwd=P)
            sh(["git", "config", "user.email", "studio@localhost"], cwd=P)
        sh(["git", "add", "-A"], cwd=P)
        sh(["git", "commit", "-qm", "plan: NeonClip comparison plan (identical for both models)"], cwd=P)
        log(f"{key}: created {P}")
    return P


# ------------------------------------------------------------------ studio helpers
def studio(P, *args, timeout=3600):
    rc, out = sh(["studio", *args], cwd=P, timeout=timeout)
    m = re.search(r"full log: ([^)]+)\)", out)
    full = ""
    if m:
        lp = P / m.group(1)
        if lp.exists():
            full = lp.read_text(errors="replace")
    m2 = re.search(r"finished with exit (-?\d+)", out)
    return (int(m2.group(1)) if m2 else rc), out, full


def run_check_script(P, step, kind, code):
    """Write a check script into the project (fresh each time) and run it with studio ue-python / blender."""
    d = P / ".studio/checks"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"check_{step}.py"
    f.write_text(code)
    rel = str(f.relative_to(P))
    if kind == "ue":
        rc, out, full = studio(P, "ue-python", f"{MODELS_BY_P[P]}.uproject", rel, timeout=1800)
    else:
        rc, out, full = studio(P, "blender", rel, timeout=1800)
    lines = [ln.split("CHECK_", 1)[1] for ln in full.splitlines() if "CHECK_" in ln and "print(" not in ln]
    res = [ln for ln in lines if ln.startswith("RESULT")]
    if not res:
        tail = "\n".join(out.strip().splitlines()[-25:])
        return False, f"check script did not finish (exit {rc}). Tool output:\n{tail}"
    ok = res[-1].startswith("RESULT PASS")
    return ok, "\n".join(lines)


MODELS_BY_P = {}


# ------------------------------------------------------------------ checks (one per step)
def check_tex(P):
    from PIL import Image
    want = {f"T_Windows_{c}.png": (512, 512) for c in "ABC"}
    want.update({f"T_Ad_{i:02d}.png": (1024, 2048) for i in range(1, 7)})
    want.update({"T_Ad_07.png": (2048, 1024), "T_Ad_08.png": (2048, 1024), "T_Puddles.png": (1024, 1024)})
    bad = []
    for n, size in want.items():
        f = P / "assets/tex" / n
        if not f.exists():
            bad.append(f"missing assets/tex/{n}")
        else:
            s = Image.open(f).size
            if s != size:
                bad.append(f"assets/tex/{n} is {s[0]}x{s[1]}, expected {size[0]}x{size[1]}")
    return not bad, ("RESULT PASS 12/12 textures with the right sizes" if not bad else
                     "RESULT FAIL\n" + "\n".join(bad))


CHECK_TOWERS = r'''
import os, bpy
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
names = [f"SM_Tower_{i:02d}" for i in range(1, 9)] + ["SM_Pyramid"]
bad = []
for n in names:
    f = os.path.join(root, "assets/models", n + ".glb")
    if not os.path.exists(f):
        bad.append(f"missing assets/models/{n}.glb"); continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=f)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not objs:
        bad.append(f"{n}: no mesh"); continue
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]; hi = [max(p[i] for p in pts) for i in range(3)]
    sx, sy, sz = (hi[i] - lo[i] for i in range(3))
    tris = sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)
    print(f"CHECK_DETAIL {n}: size {sx:.1f} x {sy:.1f} x {sz:.1f} m, min z {lo[2]:.2f}, tris {tris}, objects {len(objs)}")
    if abs(lo[2]) > 0.05: bad.append(f"{n}: base at z={lo[2]:.2f} m, expected 0")
    if n.startswith("SM_Tower"):
        if not 99 <= sz <= 125: bad.append(f"{n}: height {sz:.1f} m, expected 100 m (+ rooftop clutter up to 125)")
        if not (14.5 <= min(sx, sy) and max(sx, sy) <= 40.5): bad.append(f"{n}: footprint {sx:.1f} x {sy:.1f} m outside 15-40 m")
        if tris > 2000: bad.append(f"{n}: {tris} triangles > 2000")
    else:
        if abs(sx - 400) > 5 or abs(sy - 400) > 5: bad.append(f"{n}: base {sx:.1f} x {sy:.1f} m, expected 400 x 400")
        if abs(sz - 150) > 3: bad.append(f"{n}: height {sz:.1f} m, expected 150")
for b in bad: print("CHECK_FAIL " + b)
print(("CHECK_RESULT PASS 9/9 GLBs in spec" if not bad else f"CHECK_RESULT FAIL {len(bad)} problem(s)"))
'''

CHECK_IMPORT = r'''
import unreal
reg = unreal.AssetRegistryHelpers.get_asset_registry()
reg.search_all_assets(True)
def names(path, cls):
    return sorted(str(a.asset_name) for a in reg.get_assets_by_path(path, recursive=True)
                  if str(a.asset_class_path.asset_name) == cls)
meshes = names("/Game/City/Meshes", "StaticMesh"); tex = names("/Game/City/Textures", "Texture2D")
mats = names("/Game/City/Materials", "Material")
need = ["M_Win_A", "M_Win_B", "M_Win_C"] + [f"M_Ad_{i:02d}" for i in range(1, 9)] + \
       ["M_Pyramid", "M_Wet", "M_Flare", "M_Light_White", "M_Light_Red", "M_Hull"]
missing = [m for m in need if m not in mats]
want_meshes = [f"SM_Tower_{i:02d}" for i in range(1, 9)] + ["SM_Pyramid"]
missing_meshes = [m for m in want_meshes if m not in meshes]
print(f"CHECK_DETAIL meshes {meshes}")
print(f"CHECK_DETAIL textures {len(tex)}: {tex}")
print(f"CHECK_DETAIL materials {mats}")
ok = not missing and not missing_meshes and len(tex) >= 12
print(f"CHECK_RESULT {'PASS' if ok else 'FAIL'} meshes {len(meshes)} (missing {missing_meshes}), textures {len(tex)}/12, "
      f"materials missing {missing}")
'''

CHECK_CITY = r'''
import unreal
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level("/Game/Maps/City"):
    print("CHECK_RESULT FAIL level /Game/Maps/City does not load"); raise SystemExit
allx = actors.get_all_level_actors()
by = {a.get_actor_label(): a for a in allx}
bad = []
towers = [a for a in allx if a.get_actor_label().startswith("Tower_")]
if "HeroTower" in by: towers_all = towers + [by["HeroTower"]]
else: towers_all = towers; bad.append("no actor labelled HeroTower")
if not 300 <= len(towers) <= 460: bad.append(f"{len(towers)} Tower_* actors, expected ~400")
hs = [a.get_actor_bounds(False)[1].z * 2 for a in towers_all]
tallest = max(hs) if hs else 0
if not 5000 <= tallest <= 20000: bad.append(f"tallest tower {tallest / 100:.0f} m, expected 50-200 m")
ads = [a for a in allx if a.get_actor_label().startswith("Ad_")]
if len(ads) != 12: bad.append(f"{len(ads)} Ad_* billboards, expected 12")
panels = ([by["HeroAd"]] if "HeroAd" in by else []) + ads
if "HeroAd" not in by: bad.append("no actor labelled HeroAd")
boxes = [(t, *t.get_actor_bounds(False)) for t in towers_all]
for p in panels:
    o, e = p.get_actor_bounds(False); u = p.get_actor_up_vector(); lab = p.get_actor_label()
    if abs(u.z) > 0.05: bad.append(f"{lab}: not upright (normal {u.x:.2f},{u.y:.2f},{u.z:.2f})")
    if min(e.x, e.y, e.z) > 20: bad.append(f"{lab}: not a thin panel (extent {e.x:.0f},{e.y:.0f},{e.z:.0f})")
    size = 2 * max(e.x, e.y, e.z)
    if not 1500 <= size <= 8000: bad.append(f"{lab}: size {size:.0f} cm, expected 2,000-6,000")
    best = None
    for t, to, te in boxes:
        dx = max(abs(o.x - to.x) - te.x, 0); dy = max(abs(o.y - to.y) - te.y, 0); dz = max(abs(o.z - to.z) - te.z, 0)
        d = (dx * dx + dy * dy + dz * dz) ** 0.5
        if best is None or d < best[0]: best = (d, t, to)
    if best is None: continue
    d, t, to = best
    away = u.x * (o.x - to.x) + u.y * (o.y - to.y)
    if not 1 <= d <= 200: bad.append(f"{lab}: {d:.0f} cm from the nearest tower box ({t.get_actor_label()}), expected 50-80 cm in front of a facade")
    elif away <= 0: bad.append(f"{lab}: faces into its tower {t.get_actor_label()}")
pyr = by.get("Pyramid")
if pyr is None: bad.append("no actor labelled Pyramid")
else:
    o, e = pyr.get_actor_bounds(False)
    if not 150000 <= o.x <= 170000: bad.append(f"Pyramid at x={o.x:.0f}, expected 160000")
    if not 10000 <= 2 * e.z <= 40000: bad.append(f"Pyramid height {2 * e.z / 100:.0f} m, expected ~150 m")
flares = [a for a in allx if a.get_actor_label().startswith("FlareLight_")]
if len(flares) < 4: bad.append(f"{len(flares)} FlareLight_* lights, expected 4")
if not any(isinstance(a, unreal.ExponentialHeightFog) for a in allx): bad.append("no ExponentialHeightFog")
if not any(isinstance(a, unreal.PostProcessVolume) for a in allx): bad.append("no PostProcessVolume")
g = by.get("Ground")
if g is None: bad.append("no actor labelled Ground")
print(f"CHECK_DETAIL towers {len(towers)}, tallest {tallest / 100:.0f} m, billboards {len(panels)}, flare lights {len(flares)}")
for b in bad[:30]: print("CHECK_FAIL " + b)
print("CHECK_RESULT PASS city in spec" if not bad else f"CHECK_RESULT FAIL {len(bad)} problem(s)")
'''

CHECK_SEQ = r'''
import unreal
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bad = []
seq = unreal.load_asset("/Game/Cine/Main")
if seq is None:
    print("CHECK_RESULT FAIL no sequence /Game/Cine/Main"); raise SystemExit
s, e = seq.get_playback_start(), seq.get_playback_end()
fps = seq.get_display_rate().numerator / max(seq.get_display_rate().denominator, 1)
if (s, e) != (0, 300): bad.append(f"playback range {s}-{e}, expected 0-300")
if abs(fps - 30) > 0.01: bad.append(f"display rate {fps}, expected 30")
tracks = []
for fn in ("find_tracks_by_type", "find_master_tracks_by_type"):
    if hasattr(seq, fn):
        tracks = list(getattr(seq, fn)(unreal.MovieSceneCameraCutTrack)); break
if not tracks and hasattr(seq, "get_tracks"):
    tracks = [t for t in seq.get_tracks() if isinstance(t, unreal.MovieSceneCameraCutTrack)]
cuts = sorted((sec.get_start_frame(), sec.get_end_frame()) for t in tracks for sec in t.get_sections())
if cuts != [(0, 100), (100, 200), (200, 300)]: bad.append(f"camera cut sections {cuts}, expected [(0,100),(100,200),(200,300)]")
levels.load_level("/Game/Maps/City")
labels = {a.get_actor_label() for a in actors.get_all_level_actors()}
for c in ("Cam_1", "Cam_2", "Cam_3"):
    if c not in labels: bad.append(f"no actor labelled {c} in /Game/Maps/City")
sp = sorted(l for l in labels if l.startswith("Spinner_"))
if len(sp) < 3: bad.append(f"spinners {sp}, expected Spinner_1..3")
for rc in ("/Game/Render/Preview", "/Game/Render/Final"):
    if unreal.load_asset(rc) is None: bad.append(f"no render config {rc}")
print(f"CHECK_DETAIL range {s}-{e} @{fps:g} fps, cuts {cuts}, spinners {sp}")
for b in bad: print("CHECK_FAIL " + b)
print("CHECK_RESULT PASS sequence in spec" if not bad else f"CHECK_RESULT FAIL {len(bad)} problem(s)")
'''


def frame_stats(f):
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(f).convert("RGB"), dtype=np.float32)
    return float(a.mean())


def check_lookdev(P):
    frames = sorted((P / "Renders/preview").glob("*.png"))
    bad = []
    if not (P / "Scripts/lookdev.py").exists():
        bad.append("Scripts/lookdev.py missing")
    if len(frames) != 300:
        bad.append(f"{len(frames)} frames in Renders/preview, expected 300")
    detail = []
    for i in (30, 90, 150, 230, 290):
        if i < len(frames):
            m = frame_stats(frames[i])
            detail.append(f"{frames[i].name} mean {m:.1f}/255")
            if m < 6:
                bad.append(f"{frames[i].name} is nearly black (mean {m:.1f}/255)")
            if m > 170:
                bad.append(f"{frames[i].name} is blown out (mean {m:.1f}/255)")
    return not bad, ("RESULT PASS preview frames ok: " + "; ".join(detail) if not bad else
                     "RESULT FAIL\n" + "\n".join(bad + detail))


def check_rain(P):
    import numpy as np
    from PIL import Image
    src = sorted((P / "Renders/preview").glob("*.png"))
    if not (P / "Scripts/rain_comp.py").exists():
        return False, "RESULT FAIL Scripts/rain_comp.py missing"
    if not src:
        return False, "RESULT FAIL no preview frames in Renders/preview to test on"
    out = P / "Renders/comp_check"
    shutil.rmtree(out, ignore_errors=True)
    rc, txt = sh([SANDBOX, str(P), "--", "python3", "Scripts/rain_comp.py", "Renders/preview",
                  "Renders/comp_check"], timeout=1800)
    dst = sorted(out.glob("*.png"))
    bad = []
    if rc:
        bad.append(f"`python3 Scripts/rain_comp.py Renders/preview Renders/comp_check` exited {rc}:\n"
                   + "\n".join(txt.strip().splitlines()[-15:]))
    if len(dst) != len(src):
        bad.append(f"{len(dst)} output frames for {len(src)} input frames")
    else:
        a = np.asarray(Image.open(src[150]).convert("RGB"), dtype=np.float32)
        b = np.asarray(Image.open(dst[150]).convert("RGB"), dtype=np.float32)
        h, w = b.shape[:2]
        pic = round(w / 2.39)
        bar = (h - pic) // 2
        if b[: max(bar - 2, 1)].mean() > 2 or b[h - max(bar - 2, 1):].mean() > 2:
            bad.append(f"letterbox bars not black (top mean {b[:bar - 2].mean():.1f})")
        if np.abs(a[bar + 5: h - bar - 5] - b[bar + 5: h - bar - 5]).mean() < 0.5:
            bad.append("picture area unchanged: no rain added")
        c = np.asarray(Image.open(dst[151]).convert("RGB"), dtype=np.float32)
        if np.abs(b - c).mean() < 0.3:
            bad.append("consecutive frames identical: rain does not move")
    return not bad, ("RESULT PASS rain comp: frames, bars, rain ok" if not bad else "RESULT FAIL\n" + "\n".join(bad))


def check_score(P):
    import wave
    import numpy as np
    f = P / "audio/score.wav"
    if not f.exists():
        return False, "RESULT FAIL audio/score.wav missing"
    try:
        w = wave.open(str(f))
        n, sr, ch, sw = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    except Exception as e:  # noqa: BLE001 - report any parse error
        return False, f"RESULT FAIL cannot read audio/score.wav: {e}"
    dt = {2: np.int16, 4: np.int32}.get(sw)
    peak = (np.abs(np.frombuffer(raw, dt)).max() / float(np.iinfo(dt).max)) if dt and n else 0.0
    db = 20 * np.log10(max(peak, 1e-9))
    bad = []
    if abs(n / sr - 10.0) > 0.01:
        bad.append(f"duration {n / sr:.3f} s, expected 10.0")
    if sr != 48000:
        bad.append(f"sample rate {sr}, expected 48000")
    if ch != 2:
        bad.append(f"{ch} channels, expected 2")
    if db > -1.0:
        bad.append(f"peak {db:.2f} dBFS, expected <= -1.0")
    if db < -30:
        bad.append(f"peak {db:.2f} dBFS: nearly silent")
    d = f"{n / sr:.3f} s, {sr} Hz, {ch} ch, peak {db:.2f} dBFS"
    return not bad, ("RESULT PASS " + d if not bad else "RESULT FAIL " + d + "\n" + "\n".join(bad))


def check(key, step):
    P = project(key)
    if step == "tex":
        return check_tex(P)
    if step == "towers":
        return run_check_script(P, step, "blender", CHECK_TOWERS)
    if step in ("import", "city", "seq"):
        code = {"import": CHECK_IMPORT, "city": CHECK_CITY, "seq": CHECK_SEQ}[step]
        return run_check_script(P, step, "ue", code)
    if step == "lookdev":
        return check_lookdev(P)
    if step == "rain":
        return check_rain(P)
    if step == "score":
        return check_score(P)
    raise ValueError(step)


# ------------------------------------------------------------------ pipeline
def worker(key, step, prompt_file, resume=None):
    P = project(key)
    cmd = ["studio-worker", str(P), "--step", step, "--prompt-file", str(prompt_file), "--model", MODELS[key][0],
           "--agent", "claude", "--timeout", str(TIMEOUT)]
    if resume:
        cmd += ["--resume", resume]
    t0 = time.time()
    rc, out = sh(cmd, timeout=TIMEOUT + 900)
    m = re.search(r"\{.*\}", out, re.S)
    try:
        res = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        res = {}
    res.setdefault("seconds", round(time.time() - t0, 1))
    res["driver_rc"] = rc
    return res


def recorded_attempts(P, step):
    """Worker attempts for `step` in the project ledger since its last verdict: lets a crashed driver resume without
    giving the model an extra attempt (the work is already in the project)."""
    f = P / ".studio/ledger.jsonl"
    rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []
    out = []
    for r in rows:
        if r.get("step") != step:
            continue
        if r.get("kind") == "verdict":
            out = []
        elif "attempt" in r and r.get("owner") == "local":
            out.append({"seconds": r.get("seconds"), "exit": r.get("exit"), "turns": r.get("turns"),
                        "session_id": r.get("session_id")})
    return out


def run(key):
    RUN.mkdir(parents=True, exist_ok=True)
    P = setup(key)
    st = load_state(key)
    name = MODELS[key][1]
    pdir = RUN / key / "prompts"
    pdir.mkdir(parents=True, exist_ok=True)
    for step, pf in STEPS:
        if st["steps"].get(step, {}).get("done"):
            continue
        prompt = pdir / pf
        prompt.write_text((PROMPTS / pf).read_text().replace("{NAME}", name))
        rec = {"attempts": []}
        prior = recorded_attempts(P, step)
        if prior:
            r = prior[0]
            log(f"{key}: step {step} attempt 1 recovered from the ledger ({r.get('seconds')} s)")
        else:
            log(f"{key}: step {step} attempt 1")
            r = worker(key, step, prompt)
        ok, out = check(key, step)
        rec["attempts"].append({"seconds": r.get("seconds"), "exit": r.get("exit"), "turns": r.get("turns"),
                                "check_pass": ok, "check": out[-3000:], "session_id": r.get("session_id")})
        log(f"{key}: {step} attempt 1: {r.get('seconds')} s, exit {r.get('exit')}, check {'PASS' if ok else 'FAIL'}")
        if not ok:
            fu = pdir / f"{pf[:-3]}.followup.md"
            text = FOLLOWUP.format(output=out[-4000:])
            sid = r.get("session_id")
            if not sid:   # the first attempt never started a session: fresh run with the full prompt + check output
                text = prompt.read_text() + "\n\n" + text
            fu.write_text(text)
            if len(prior) > 1:
                r2 = prior[1]
                log(f"{key}: step {step} attempt 2 recovered from the ledger")
            else:
                log(f"{key}: step {step} attempt 2 ({'resume' if sid else 'fresh'})")
                r2 = worker(key, step, fu, resume=sid)
            ok, out = check(key, step)
            rec["attempts"].append({"seconds": r2.get("seconds"), "exit": r2.get("exit"), "turns": r2.get("turns"),
                                    "check_pass": ok, "check": out[-3000:], "session_id": r2.get("session_id")})
            log(f"{key}: {step} attempt 2: {r2.get('seconds')} s, exit {r2.get('exit')}, check {'PASS' if ok else 'FAIL'}")
        rec["pass"] = ok
        rec["done"] = True
        st["steps"][step] = rec
        save_state(key, st)
        n = len(rec["attempts"])
        verdict = "pass" if ok else "fail"
        sh(["studio-ledger", str(P), "verdict", "--step", step, "--outcome", verdict, "--note",
            f"mechanical check after {n} attempt(s): " + out.splitlines()[0][:200] if out else ""])
        sh(["git", "add", "-A"], cwd=P)
        sh(["git", "commit", "-qm", f"{step}: {verdict} after {n} attempt(s) ({MODELS[key][2]}, mechanical check)"],
           cwd=P)
    log(f"{key}: pipeline done")


def final(key):
    P = project(key)
    name = MODELS[key][1]
    st = load_state(key)
    fin = {"notes": []}
    t0 = time.time()
    shutil.rmtree(P / "Renders/final", ignore_errors=True)
    rc, out, _ = studio(P, "ue-render", f"{name}.uproject", "/Game/Render/Final", "/Game/Cine/Main", "/Game/Maps/City",
                        timeout=3600)
    frames = sorted((P / "Renders/final").glob("*.png"))
    fin["render_frames"] = len(frames)
    fin["render_s"] = round(time.time() - t0)
    log(f"{key}: final render exit {rc}, {len(frames)} frames, {fin['render_s']} s")
    if not frames:
        fin["notes"].append("final render produced no frames")
        st["final"] = fin
        save_state(key, st)
        return
    src = "Renders/final"
    shutil.rmtree(P / "Renders/comp_final", ignore_errors=True)
    if (P / "Scripts/rain_comp.py").exists():
        rc, out = sh([SANDBOX, str(P), "--", "python3", "Scripts/rain_comp.py", "Renders/final",
                      "Renders/comp_final"], timeout=3600)
        if rc == 0 and len(list((P / "Renders/comp_final").glob("*.png"))) == len(frames):
            src = "Renders/comp_final"
        else:
            fin["notes"].append(f"rain comp failed (exit {rc}); clip without rain/letterbox")
    else:
        fin["notes"].append("no Scripts/rain_comp.py; clip without rain/letterbox")
    (P / "out").mkdir(exist_ok=True)
    rc, out, _ = studio(P, "encode", src, "30", f"out/{name}_video.mp4", timeout=1800)
    video = P / f"out/{name}_video.mp4"
    clip = P / f"out/{name}.mp4"
    ok_audio = check_score(P)[0]
    if ok_audio:
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(P / "audio/score.wav"), "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-shortest", str(clip)])
    else:
        fin["notes"].append("score missing or out of spec; clip has silent audio")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-f", "lavfi", "-i",
            "anullsrc=r=48000:cl=stereo", "-c:v", "copy", "-c:a", "aac", "-shortest", str(clip)])
    fin["clip"] = str(clip) if clip.exists() else None
    fin["seconds"] = round(time.time() - t0)
    st["final"] = fin
    save_state(key, st)
    log(f"{key}: final clip {fin['clip']} notes {fin['notes']}")
    sh(["studio-ledger", str(P), "add", "--step", "final", "--owner", "claude", "--outcome",
        "pass" if fin["clip"] else "fail", "--note", "mechanical (script): Final render -> worker's rain comp -> "
        "encode -> mux; " + "; ".join(fin["notes"])])
    sh(["git", "add", "-A"], cwd=P)
    sh(["git", "commit", "-qm", "final: mechanical render/comp/encode/mux"], cwd=P)


# ------------------------------------------------------------------ comparison output
def stats(key):
    st = load_state(key)
    steps = st["steps"]
    first = sum(1 for s in steps.values() if s["attempts"][0]["check_pass"])
    second = sum(1 for s in steps.values() if s["pass"] and not s["attempts"][0]["check_pass"])
    failed = [k for k, s in steps.items() if not s["pass"]]
    secs = sum((a.get("seconds") or 0) for s in steps.values() for a in s["attempts"])
    return {"first": first, "second": second, "failed": failed, "minutes": secs / 60,
            "attempts": sum(len(s["attempts"]) for s in steps.values()), "steps": steps,
            "final": st.get("final", {})}


def stats_panel(path, keys, top_h):
    """Stats under the clips: one column per model."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1920, 1080 - top_h
    n = len(keys)
    colw = W // n
    im = Image.new("RGB", (W, H), (12, 13, 16))
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(FONT, 30 if n == 2 else 26)
    f = ImageFont.truetype(MONO, 21 if n == 2 else 18)
    small = ImageFont.truetype(MONO, 17 if n == 2 else 15)
    lh = 28 if n == 2 else 25
    for col, key in enumerate(keys):
        x0 = col * colw + 30
        s = stats(key)
        d.text((x0, 18), MODELS[key][2], font=big, fill=(235, 235, 240))
        d.text((x0, 62), f"{s['first']}/8 first try, {s['second']} after retry, {len(s['failed'])} failed",
               font=small, fill=(200, 205, 215))
        d.text((x0, 86), f"worker time {s['minutes']:.0f} min, {s['attempts']} attempts", font=small,
               fill=(200, 205, 215))
        y = 124
        d.text((x0, y), f"{'step':<9}{'result':<14}{'tries':>5}{'min':>6}", font=f, fill=(150, 160, 175))
        y += lh + 2
        for step, _ in STEPS:
            rec = s["steps"].get(step)
            if not rec:
                d.text((x0, y), f"{step:<9}{'not run':<14}", font=f, fill=(120, 120, 120))
                y += lh
                continue
            tries = len(rec["attempts"])
            res = "pass" if rec["attempts"][0]["check_pass"] else ("pass (retry)" if rec["pass"] else "FAIL")
            mins = sum((a.get("seconds") or 0) for a in rec["attempts"]) / 60
            colr = (120, 220, 140) if rec["pass"] and tries == 1 else ((230, 200, 90) if rec["pass"] else (240, 90, 90))
            d.text((x0, y), f"{step:<9}{res:<14}{tries:>5}{mins:>6.0f}", font=f, fill=colr)
            y += lh
        notes = s["final"].get("notes") or []
        fin = ("not run yet" if not s["final"] else "; ".join(notes) if notes else "render + rain + encode + mux ok")
        d.text((x0, y + 8), "final: " + fin,
               font=small, fill=(170, 175, 185))
        if col:
            d.line([(col * colw, 20), (col * colw, H - 50)], fill=(60, 62, 70), width=2)
    d.text((30, H - 40), "Same plan, prompts and checks for every model; director involvement identical (scripted): "
           "one automatic retry with the check output, no fixes, mechanical final render.", font=small,
           fill=(140, 145, 155))
    im.save(path)


def compare(keys=None):
    """Side-by-side of 2 or 3 clips over a stats panel; the audio plays each clip's score in turn (10 s each)."""
    keys = keys or [k for k in MODELS if state_path(k).exists()]
    n = len(keys)
    if n not in (2, 3):
        raise SystemExit(f"compare needs 2 or 3 models, got {keys}")
    out = RUN / "out"
    out.mkdir(parents=True, exist_ok=True)
    cw, ch = 1920 // n, 1080 // n            # 960x540 for two, 640x360 for three
    total = 10 * n
    panel = out / "stats_panel.png"
    stats_panel(panel, keys, ch)
    clips = []
    for key in keys:
        c = stats(key)["final"].get("clip")
        clips.append(c if c and pathlib.Path(c).exists() else None)
    inputs, filt = [], []
    for c in clips:
        if c:
            inputs += ["-i", c]
        else:
            inputs += ["-f", "lavfi", "-t", "10", "-i", "color=c=black:s=1920x1080:r=30,format=yuv420p"]
    inputs += ["-loop", "1", "-t", str(total), "-i", str(panel)]
    for i, key in enumerate(keys):
        label = MODELS[key][2] + ("" if clips[i] else " (no clip)")
        filt.append(f"[{i}:v]scale={cw}:{ch},setsar=1,fps=30,loop=loop={n - 1}:size=300,"
                    f"drawtext=fontfile={FONT}:text='{label}':x=(w-tw)/2:y=16:fontsize={28 if n == 2 else 22}:"
                    f"fontcolor=white[v{i}]")
    notes = ",".join(
        f"drawtext=fontfile={FONT}:text='audio\\: {MODELS[k][2]}':x=w-tw-30:y=h-34:fontsize=20:fontcolor=0xb0b8c8:"
        f"enable='between(t,{10 * i},{10 * i + 10})'" for i, k in enumerate(keys))
    filt.append("".join(f"[v{i}]" for i in range(n)) + f"hstack={n}[top];[{n}:v]scale=1920:{1080 - ch},fps=30[bot];"
                f"[top][bot]vstack=2,{notes}[v]")
    if all(clips):
        filt.append(";".join(f"[{i}:a]atrim=0:10,asetpts=PTS-STARTPTS[a{i}]" for i in range(n)) + ";"
                    + "".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]")
        amap = ["-map", "[a]"]
    else:
        amap = []
    dst = out / "NeonClip_side_by_side.mp4"
    rc, txt = sh(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "[v]",
                  *amap, "-t", str(total), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac",
                  "-b:a", "192k", str(dst)])
    log(f"compare {keys}: {dst} rc {rc} {txt[-500:]}")
    summary = {k: {kk: vv for kk, vv in stats(k).items() if kk != "steps"} for k in keys}
    (out / "stats.json").write_text(json.dumps(summary, indent=1))
    return rc


if __name__ == "__main__":
    RUN.mkdir(parents=True, exist_ok=True)
    for k in MODELS:
        MODELS_BY_P[project(k)] = MODELS[k][1]
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        run(sys.argv[2])
    elif cmd == "final":
        final(sys.argv[2])
    elif cmd == "check":
        print(check(sys.argv[2], sys.argv[3]))
    elif cmd == "compare":
        compare(sys.argv[2:] or None)
    elif cmd == "all":
        keys = sys.argv[2:] or ["qwen", "bonsai", "gemma"]
        for k in keys:
            run(k)
            final(k)
        compare(keys)
    else:
        print(__doc__)
