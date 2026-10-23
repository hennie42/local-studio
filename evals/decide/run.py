"""Ask a model the frame-QA and log-triage questions, either as a decision model (/v1/systemone) or as a chat model
(JSON answer), and record answers, truth and timings.
Usage: run.py --url http://127.0.0.1:8090 --model NAME --mode systemone|chat --set frames|logs [--limit N]"""
import argparse
import base64
import json
import pathlib
import re
import time
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
from studio_config import path as cfg_path  # noqa: E402

DATA = cfg_path("STUDIO_EVAL_HOME") / "decide"

FRAME_Q = {
    "exposure": {"type": "choice", "instructions": "How is this rendered frame exposed?",
                 "criteria": {"underexposed": "too dark: the scene is visible but detail is lost in shadow",
                              "good": "well exposed: highlights and shadows keep their detail",
                              "overexposed": "too bright: large clipped or blown-out white areas"}},
    "black_frame": {"type": "noul", "instructions": "Is the frame essentially entirely black, a render failure?"},
    "defect": {"type": "choice", "instructions": "Does the frame have a rendering defect?",
               "criteria": {"none": "no rendering defect",
                            "missing_texture": "a magenta and black checkerboard patch (a missing material)",
                            "black_band": "a solid black horizontal strip across the image that is not part of the scene"}},
}
FRAME_CHAT = """You are the render QA step of a CG animation pipeline. Judge this rendered frame.
Answer with ONLY a JSON object, no other text:
{"exposure": "underexposed" | "good" | "overexposed", "black_frame": true | false, "defect": "none" | "missing_texture" | "black_band"}
"underexposed" = too dark, the scene is visible but detail is lost in shadow. "overexposed" = large clipped or blown-out
white areas. "black_frame" = essentially entirely black (render failure). "missing_texture" = a magenta and black
checkerboard patch (a missing material). "black_band" = a solid black horizontal strip across the image that is not part
of the scene."""

LOG_CAUSES = {
    "succeeded": "the job worked",
    "code_error": "the project's own code or script is broken: a parse, compile or link error, a Python traceback, a script error",
    "test_failure": "the code runs but behaves wrong: failed tests or assertions, a game that does not reach its goal",
    "timeout": "the job ran out of time or was killed without an error of its own",
    "bad_request": "the job was called wrongly: bad arguments, a wrong file name or type",
    "other": "anything else, such as an engine or environment problem",
}
LOG_Q = {
    "ok": {"type": "noul", "instructions": "Did this job succeed?"},
    "cause": {"type": "choice", "instructions": "What is the outcome of this job?", "criteria": LOG_CAUSES},
}
LOG_CHAT = ("You triage jobs of a game and film pipeline (Godot, Unreal Engine, Blender). From the job and its log excerpt,\n"
            "decide the outcome. Answer with ONLY a JSON object, no other text:\n"
            '{"ok": true | false, "cause": ' + " | ".join(f'"{k}"' for k in LOG_CAUSES) + "}\nThe causes:\n"
            + "\n".join(f"- {k}: {v}" for k, v in LOG_CAUSES.items()))


def post(url, body, timeout=600):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()), time.time() - t


def data_url(path):
    return "data:image/jpeg;base64," + base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def items(which):
    if which == "frames":
        labels = json.loads((DATA / "frames/labels.json").read_text())
        for name, t in labels.items():
            yield name, {"image": DATA / "frames" / name}, t
    else:
        for x in json.loads((DATA / "logs.json").read_text()):
            state = f"Job: {x['action']} {x['args']}\nLog excerpt:\n{x['text']}"
            yield x["id"], {"state": state}, {"ok": x["exit"] == 0, "cause": "succeeded" if x["exit"] == 0 else x["category"],
                                              "engine": x["action"].split("-")[0]}


def ask_systemone(url, model, which, inp):
    body = {"model": model, "questions": FRAME_Q if which == "frames" else LOG_Q}
    if which == "frames":
        body.update(state="A rendered frame from a CG animation or game pipeline.", images=[data_url(inp["image"])])
    else:
        body["state"] = inp["state"]
    r, secs = post(url + "/v1/systemone", body)
    a = r["answers"]
    if which == "frames":
        got = {"exposure": a["exposure"]["choice"], "black_frame": a["black_frame"]["noul"] >= 0.5, "defect": a["defect"]["choice"],
               "conf": {k: a[k].get("confidence", abs(a[k].get("noul", 0.5) - 0.5) * 2) for k in a}}
    else:
        got = {"ok": a["ok"]["noul"] >= 0.5, "p_ok": a["ok"]["noul"], "cause": a["cause"]["choice"], "conf": {"cause": a["cause"]["confidence"]}}
    return got, secs, r.get("usage", {}).get("input_tokens")


def ask_chat(url, model, which, inp, max_tokens):
    if which == "frames":
        content = [{"type": "image_url", "image_url": {"url": data_url(inp["image"])}}, {"type": "text", "text": FRAME_CHAT}]
    else:
        content = [{"type": "text", "text": LOG_CHAT + "\n\n" + inp["state"]}]
    r, secs = post(url + "/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": content}],
                                                  "max_tokens": max_tokens})
    text = r["choices"][0]["message"].get("content") or ""
    m = re.search(r"\{.*\}", text, re.S)
    try:
        got = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        got = {}
    if which == "frames":
        got = {"exposure": got.get("exposure"), "black_frame": bool(got.get("black_frame")), "defect": got.get("defect")}
    else:
        got = {"ok": bool(got.get("ok")), "cause": got.get("cause")}
    return got, secs, r.get("usage", {}).get("prompt_tokens")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--mode", choices=["systemone", "chat"], required=True)
    ap.add_argument("--set", dest="which", choices=["frames", "logs"], required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    out = DATA / "results" / f"{a.which}-{a.model}{a.tag}.jsonl"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w") as f:
        for n, (iid, inp, truth) in enumerate(items(a.which)):
            if a.limit and n >= a.limit:
                break
            try:
                if a.mode == "systemone":
                    got, secs, toks = ask_systemone(a.url, a.model, a.which, inp)
                else:
                    got, secs, toks = ask_chat(a.url, a.model, a.which, inp, a.max_tokens)
                err = None
            except Exception as e:  # keep going: a failed item counts as wrong
                got, secs, toks, err = {}, 0.0, None, str(e)[:300]
            f.write(json.dumps({"id": iid, "truth": truth, "got": got, "seconds": round(secs, 2), "tokens": toks, "error": err}) + "\n")
            f.flush()
    print(out)


if __name__ == "__main__":
    main()
