"""Shared helpers for UE tasks: set up a studio project in the workspace, run hidden inspections."""
import json
import pathlib
import re
import shutil
import subprocess

STUDIO = pathlib.Path(__file__).resolve().parents[2]
TEMPLATE = STUDIO / "template"
import sys as _sys
_sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
from studio_config import cfg, path as cfg_path  # noqa: E402
UE_ROOT = cfg_path("STUDIO_UE_ROOT") if cfg["STUDIO_UE_ROOT"] else pathlib.Path("/nonexistent-unreal")
UE_CMD = str(UE_ROOT / "Engine/Binaries/Linux/UnrealEditor-Cmd")
UE_BUILD = str(UE_ROOT / "Engine/Build/BatchFiles/Linux/Build.sh")


def setup_project(ws, name="Studio", cpp=False):
    """Copy the studio template (base UE project, or the C++ one) into ws as <name>.uproject."""
    src = TEMPLATE / ("cpp-min" if cpp else "ue-base")
    for item in src.iterdir():
        dst = ws / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)
    if cpp:  # cpp template's module is StudioGame; keep it, but make sure the render hook exists too
        hook = TEMPLATE / "ue-base/Content/Python/init_unreal.py"
        (ws / "Content/Python").mkdir(parents=True, exist_ok=True)
        shutil.copy2(hook, ws / "Content/Python/init_unreal.py")
        up = ws / "StudioGame.uproject"
    else:
        up = ws / f"{name}.uproject"
        (ws / "StudioProject.uproject").rename(up)
    shutil.copy2(TEMPLATE / "AGENTS.md", ws / "AGENTS.md")
    (ws / "CLAUDE.md").write_text("@AGENTS.md\n")
    (ws / ".gitignore").write_text("Binaries/\nIntermediate/\nSaved/\nDerivedDataCache/\n.studio/spool/\n")
    (ws / "Scripts").mkdir(exist_ok=True)
    return up


def inspect(ws, uproject, script_body, timeout=900):
    """Run a hidden Python inspection inside UE (outside the sandbox); the script must
    call emit(dict). Returns the dict, or {"error": ...}."""
    hidden_dir = ws / ".studio/grader"
    hidden_dir.mkdir(parents=True, exist_ok=True)
    script = hidden_dir / "inspect.py"
    script.write_text("import json, unreal\n"
                      "def emit(d):\n    unreal.log('GRADER_JSON ' + json.dumps(d, default=str))\n" + script_body)
    out = run_logged([UE_CMD, str(uproject), "-run=pythonscript", f"-script={script}", "-unattended", "-nop4",
                      "-nosplash", "-NullRHI", "-nocrashreports", "-stdout", "-FullStdOutLogOutput"], ws, hidden_dir / "inspect.log", timeout)
    for line in out.splitlines():  # only real log lines, not tracebacks echoing the emit() source
        m = re.search(r"\]LogPython: GRADER_JSON (.*)$", line)
        if m:
            return json.loads(m.group(1))
    errs = [l for l in out.splitlines() if "LogPython: Error" in l][-3:]
    return {"error": "no grader output; " + " | ".join(e[-160:] for e in errs)}


def build_cpp(ws, uproject, timeout=1800):
    log = ws / ".studio/grader/build.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    out = run_logged([UE_BUILD, f"{uproject.stem}Editor", "Linux", "Development", f"-Project={uproject}", "-WaitMutex"],
                     ws, log, timeout)
    errors = [l.strip() for l in out.splitlines() if "error:" in l][:3]
    return "Result: Succeeded" in out, errors


def run_logged(argv, cwd, log_path, timeout):
    """Run with output to a file, not a pipe: UE forks UnrealTraceServer, which inherits and keeps
    pipes open, so capture_output would hang long after the editor exited."""
    with open(log_path, "w") as f:
        try:
            subprocess.run(argv, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
    return pathlib.Path(log_path).read_text(errors="replace")
