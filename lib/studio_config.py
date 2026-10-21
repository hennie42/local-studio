#!/usr/bin/env python3
"""Machine configuration for the studio, in one place.

Values come from (highest first): environment variables, ~/.config/studio/studio.env (KEY=VALUE lines, written by
install.sh; $STUDIO_CONFIG points elsewhere), then the defaults below. Python: `from studio_config import cfg, path`.
Shell: `eval "$(python3 <studio>/lib/studio_config.py --shell)"` exports every key.

GPU indices: CUDA/nvidia-smi numbering (with CUDA_DEVICE_ORDER=PCI_BUS_ID) and Vulkan numbering can DIFFER on
multi-GPU machines; STUDIO_GODOT_GPU is a Vulkan index (run `godot --verbose` to see the device list).
"""
import os
import pathlib
import shlex
import sys

HOME = pathlib.Path.home()
STUDIO = pathlib.Path(__file__).resolve().parents[1]
CONFIG_FILE = pathlib.Path(os.environ.get("STUDIO_CONFIG", HOME / ".config/studio/studio.env"))

DEFAULTS = {
    # where things live
    "STUDIO_PROJECTS_UE": str(HOME / "StudioProjects/unreal"),     # Unreal projects (studio-new)
    "STUDIO_PROJECTS_GODOT": str(HOME / "StudioProjects/godot"),   # Godot projects (studio-new --godot)
    "STUDIO_EVAL_HOME": str(HOME / "StudioProjects/evals"),        # eval runs (runs/) and comparison prompts
    "STUDIO_MODELS_DIR": str(HOME / "llm-models"),                 # GGUF files for llama-swap
    "STUDIO_UE_ROOT": "",                                          # Unreal Engine install; empty = not installed
    "STUDIO_GODOT_HOME": str(HOME / ".local/share/studio/godot"),  # godot-refresh: engines + reference bundles
    "STUDIO_ASSET_HOME": str(HOME / "StudioProjects/assets"),      # studio-assets: CC0 library index + mirror
    # models
    "STUDIO_LLAMA_URL": "http://127.0.0.1:8080",                   # llama-swap (local models); unused online-only
    "STUDIO_GPU_POLICY": "timeshare",                              # timeshare | coresident
    "STUDIO_GPU_MODELS": "",       # comma list: llama-swap models on the render GPU (unloaded for GPU jobs)
    "STUDIO_SMALL_MODELS": "",     # comma list: models on a second, small GPU (unloaded for Godot jobs there)
    # GPUs
    "STUDIO_WORKER_GPU": "0",      # CUDA index of the GPU that runs the worker LLM
    "STUDIO_UE_ADAPTER": "0",      # Unreal -graphicsadapter (render GPU)
    "STUDIO_GODOT_GPU": "0",       # Godot --gpu-index (VULKAN index)
    "STUDIO_GODOT_ON_SMALL_GPU": "0",  # 1 = Godot renders on the second GPU, so the worker LLM is never unloaded
}


def _read_file(p):
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().removeprefix("export ").strip()
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            out[k] = os.path.expandvars(os.path.expanduser(v))
    return out


def load():
    c = dict(DEFAULTS)
    c.update(_read_file(CONFIG_FILE))
    for k in list(c):
        if k in os.environ:
            c[k] = os.environ[k]
    c["STUDIO_HOME"] = str(STUDIO)
    return c


cfg = load()


def path(key):
    return pathlib.Path(cfg[key]).expanduser()


def items(key):
    return [x.strip() for x in cfg.get(key, "").split(",") if x.strip()]


if __name__ == "__main__":
    if "--shell" in sys.argv:
        for k, v in cfg.items():
            print(f"export {k}={shlex.quote(v)}")
    else:
        w = max(map(len, cfg))
        print(f"# config file: {CONFIG_FILE} ({'found' if CONFIG_FILE.exists() else 'missing: defaults'})")
        for k, v in cfg.items():
            print(f"{k:<{w}} = {v}")
