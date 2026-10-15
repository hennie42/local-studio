"""Shared helpers for Godot tasks: set up a studio Godot project in the workspace, run hidden headless tests."""
import os
import pathlib
import re
import shutil
import subprocess

STUDIO = pathlib.Path(__file__).resolve().parents[2]
TEMPLATE = STUDIO / "template"
GODOT = os.environ.get("GODOT_BIN", str(pathlib.Path.home() / ".local/bin/godot"))
import sys as _sys
_sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
from studio_config import cfg, path as cfg_path  # noqa: E402
REF = pathlib.Path(os.environ.get("GODOT_REF_DIR", str(cfg_path("STUDIO_GODOT_HOME") / "ref-current")))


def setup_project(ws, name="GodotTask"):
    """Copy the Godot template (as studio-new --godot does) into ws."""
    for item in (TEMPLATE / "godot-base").iterdir():
        dst = ws / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)
    for f in ("project.godot", "export_presets.cfg"):
        p = ws / f
        p.write_text(p.read_text().replace("StudioGodot", name))
    shutil.copytree(REF.resolve(), ws / "godot-ref", dirs_exist_ok=True)
    shutil.copy2(TEMPLATE / "AGENTS-godot.md", ws / "AGENTS.md")
    (ws / "CLAUDE.md").write_text("@AGENTS.md\n")
    for d in ("out", "Renders", "assets", "audio", ".studio"):
        (ws / d).mkdir(exist_ok=True)
    for d in ("godot-ref", "out", "Renders"):
        (ws / d / ".gdignore").touch()
    (ws / ".gitignore").write_text(".godot/\nbuild/\ngodot-ref/\nRenders/\nshots/\n.studio/\n")


def run(ws, args, log_name, timeout=300):
    """Run godot (outside the sandbox) in the workspace; returns (exit code, output)."""
    log = ws / ".studio/grader" / log_name
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        p = subprocess.run([GODOT, *args], cwd=ws, capture_output=True, text=True, timeout=timeout)
        out, code = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        code = 124
    log.write_text(out)
    return code, out


def check(ws):
    """The same check workers run (studio godot-check): lint + full compile. Returns (clean, summary lines)."""
    p = subprocess.run([str(STUDIO / "bin/godot-check-all")], cwd=ws, capture_output=True, text=True, timeout=600,
                       env={**os.environ, "GODOT_BIN": GODOT})
    out = p.stdout + p.stderr
    (ws / ".studio/grader").mkdir(parents=True, exist_ok=True)
    (ws / ".studio/grader/check.log").write_text(out)
    lines = [l for l in out.splitlines() if l.strip()]
    return p.returncode == 0, lines


def hidden_test(ws, name, code, timeout=120):
    """Write a hidden SceneTree test script into .studio/grader and run it headless. The script prints
    'TEST <name> PASS|FAIL <detail>' lines. Returns (results dict name->bool, details, raw output)."""
    d = ws / ".studio/grader"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.gd").write_text(code)
    if not (ws / ".godot").exists():
        run(ws, ["--headless", "--path", ".", "--import"], "import.log", timeout=300)
    rc, out = run(ws, ["--headless", "--path", ".", "--script", f"res://.studio/grader/{name}.gd"], f"{name}.log",
                  timeout=timeout)
    res, details = {}, []
    for m in re.finditer(r"^TEST (\S+) (PASS|FAIL) ?(.*)$", out, re.M):
        res[m.group(1)] = m.group(2) == "PASS"
        if m.group(2) == "FAIL":
            details.append(f"{m.group(1)}: {m.group(3)[:120]}")
    errs = [l.strip() for l in out.splitlines() if "SCRIPT ERROR" in l][:3]
    if errs:
        details += errs
    return res, details, out


def markers(out):
    return re.findall(r"^GAME_[A-Z_]+.*$", out, re.M)
