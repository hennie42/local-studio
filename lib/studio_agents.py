"""How workers are launched (shared by evals/harness.py and bin/studio-worker).

Worker models: a llama-swap model id (local, via `claude-local`) or an Anthropic model id starting with "claude-"
(online: plain `claude --model ...` with the user's own login/API key). Both run with the same sandbox.

Both agents are confined to the project directory:
- claude-local: Claude Code's own Bash sandbox (bubblewrap + socat), no network, writes only in the project.
- opencode: the whole process inside bin/studio-sandbox (bubblewrap: only /usr,/etc + the project visible,
  own network namespace with only the local LLM bridged in); `--standalone` so its tools run inside the
  sandbox (the default background service would run them outside it).
- claude-local: additionally denyRead ~/ and /data (except project + studio tools) and blockReadsOutside-
  WorkingDirectories for the Read tool, so workers can't read other projects, graders or personal files.
GPU/engine work goes through `studio` (the broker), which is on PATH for workers.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from studio_config import cfg, items, path  # noqa: E402

HOME = pathlib.Path.home()
STUDIO = pathlib.Path(__file__).resolve().parents[1]
STUDIO_BIN = STUDIO / "bin"
# local models: context size (must match llama-swap -c) and vision. The installed profile's effective values
# (after its overrides) live in ~/.config/studio/models.json; the repo catalog is the fallback.
CATALOGS = [HOME / ".config/studio/models.json", STUDIO / "models/catalog.json"]


def _catalog():
    for c in CATALOGS:
        try:
            return json.loads(c.read_text())["models"]
        except (OSError, ValueError, KeyError):
            continue
    return {}


MODEL_CTX = {m: v.get("ctx", 32768) for m, v in _catalog().items()}
VISION_MODELS = {m for m, v in _catalog().items() if v.get("vision")} | {"claude"}   # online Claude models see images


def is_online(model):
    return model.startswith("claude-")


def has_vision(model):
    return is_online(model) or model in VISION_MODELS


def sandbox_deny_read():
    """Folders a worker must not read: home, every studio folder (other projects, graders, models), extras."""
    dirs = ["~/"] + [cfg[k] for k in ("STUDIO_PROJECTS_UE", "STUDIO_PROJECTS_GODOT", "STUDIO_EVAL_HOME",
                                      "STUDIO_MODELS_DIR", "STUDIO_GODOT_HOME") if cfg.get(k)]
    return sorted(set(dirs + items("STUDIO_SANDBOX_DENY")))


def claude_cmd(ws, model, prompt, resume=None, small_model=None):
    settings = {
        "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False,
                    "failIfUnavailable": True,
                    "filesystem": {"allowWrite": [str(ws)],
                                   # no home directory, no other projects/graders/models, except what's needed
                                   "denyRead": sandbox_deny_read(),
                                   "allowRead": [str(ws), str(STUDIO_BIN), str(STUDIO_BIN.parent / "lib")]},
                    "network": {"allowedDomains": []}},
        "permissions": {"deny": ["Bash(git push:*)", "Bash(sudo:*)", "WebFetch", "WebSearch"],
                        "blockReadsOutsideWorkingDirectories": True},
    }
    if is_online(model):   # Anthropic API with the user's own login / ANTHROPIC_API_KEY
        env = {}
        argv = ["claude", "--model", model, "-p", prompt, "--output-format", "stream-json", "--verbose",
                "--permission-mode", "acceptEdits", "--settings", json.dumps(settings),
                "--strict-mcp-config", "--mcp-config", json.dumps({"mcpServers": {}})]
        if resume:
            argv += ["--resume", resume]
        return argv, env
    env = {"LOCAL_LLM_MODEL": model, "LOCAL_LLM_SMALL_MODEL": small_model or model,
           "LOCAL_LLM_CTX": str(MODEL_CTX.get(model, 32768)), "LOCAL_LLM_URL": cfg["STUDIO_LLAMA_URL"]}
    argv = [str(HOME / ".local/bin/claude-local"), "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--permission-mode", "acceptEdits", "--settings", json.dumps(settings),
            # no MCP servers from the user's config: they run outside the sandbox (e.g. a photo app with ~/Pictures
            # access) and their ~100 tool definitions bloat every request
            "--strict-mcp-config", "--mcp-config", json.dumps({"mcpServers": {}})]
    if resume:
        argv += ["--resume", resume]
    return argv, env


def opencode_cmd(ws, model, prompt, resume=None, small_model=None):
    """opencode inside bin/studio-sandbox: no home, no /data beyond the project, no network but the LLM."""
    (ws / "opencode.json").write_text(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "permission": {"*": "allow", "external_directory": "deny", "webfetch": "deny", "websearch": "deny",
                       "bash": {"*": "allow", "git push *": "deny", "sudo *": "deny"}},
    }, indent=1))
    argv = [str(STUDIO_BIN / "studio-sandbox"), str(ws), "--",
            "opencode", "run", "--standalone", "--auto", "--model", f"local/{model}", "--format", "json"]
    if resume:
        argv += ["--session", resume]
    argv.append(prompt)
    return argv, {}


AGENTS = {"claude": claude_cmd, "opencode": opencode_cmd}


def worker_env(extra):
    return {**os.environ, **extra, "PATH": f"{STUDIO_BIN}:{os.environ['PATH']}"}


def parse_stream(agent, out_path):
    """Metrics + final answer + session id from the agent's JSON event stream."""
    m = {"turns": None, "peak_ctx": 0, "agent_error": None, "result": None, "session_id": None,
         "permission_denials": []}
    for line in pathlib.Path(out_path).read_text(errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if agent == "claude":
            if ev.get("session_id"):
                m["session_id"] = ev["session_id"]
            if ev.get("type") == "assistant":
                u = ev.get("message", {}).get("usage", {})
                ctx = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                m["peak_ctx"] = max(m["peak_ctx"], ctx)
            elif ev.get("type") == "result":
                m["turns"] = ev.get("num_turns")
                m["result"] = ev.get("result")
                m["permission_denials"] = ev.get("permission_denials") or []
                if ev.get("is_error"):
                    m["agent_error"] = str(ev.get("result") or ev.get("subtype"))[:300]
        else:
            sid = ev.get("sessionID") or (ev.get("part") or {}).get("sessionID")
            if sid:
                m["session_id"] = sid
            part = ev.get("part") or {}
            tokens = part.get("tokens") or ev.get("tokens")
            if isinstance(tokens, dict):
                ctx = tokens.get("input", 0) if isinstance(tokens.get("input"), int) else 0
                cache = tokens.get("cache") or {}
                if isinstance(cache, dict):
                    ctx += sum(v for v in cache.values() if isinstance(v, int))
                m["peak_ctx"] = max(m["peak_ctx"], ctx)
            if part.get("type") == "step-finish" or (ev.get("type") or "").endswith("step_finish"):
                m["turns"] = (m["turns"] or 0) + 1
            if part.get("type") == "text" and part.get("text"):
                m["result"] = part["text"]
            if ev.get("type") == "error":
                m["agent_error"] = json.dumps(ev)[:300]
    return m
