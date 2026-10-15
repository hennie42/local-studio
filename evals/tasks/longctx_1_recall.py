"""Long context: recall 3 facts placed at 15/50/85 % depth in source code, answer in strict JSON.

Tested at ~24K, ~90K and ~180K tokens (lengths beyond the model's context are skipped).
"""
import json
import pathlib
import re

AREA = "longctx"
TITLE = "Long context: 3-fact recall + strict JSON at 24K/90K/180K tokens"
KIND = "direct"
TIMEOUT = 3600
SRC = pathlib.Path.home() / "opt/llama.cpp"
TARGETS = [24_000, 90_000, 180_000]
CHARS_PER_TOKEN = 3.1  # C/C++ source with llama-style tokenizers; corrected per model after the first call
FACTS = [
    ("// CONFIG NOTE: the render farm listens on port 48213.\n", "port", 48213),
    ("// CONFIG NOTE: nightly backups go to the bucket named heron-archive-7.\n", "bucket", "heron-archive-7"),
    ("// CONFIG NOTE: the maintenance window starts at 03:40 UTC.\n", "window", "03:40 UTC"),
]
QUESTION = """\n\nThree CONFIG NOTE comments are hidden in the code above. Answer with ONLY this JSON object and nothing else:
{"port": <integer>, "bucket": "<string>", "window": "<string, e.g. 12:00 UTC>"}"""


def corpus():
    files = sorted(list((SRC / "src").rglob("*.cpp")) + list((SRC / "ggml/src").rglob("*.c")))
    return "".join(f"// FILE {p.name}\n{p.read_text(errors='ignore')}\n" for p in files)


def build(text, n_chars):
    body = text[:n_chars]
    for (fact, _, _), depth in zip(FACTS, (0.15, 0.50, 0.85)):
        cut = body.rfind("\n", 0, int(len(body) * depth)) + 1
        body = body[:cut] + fact + body[cut:]
    return body + QUESTION


def run_direct(model, api):
    import harness  # MODEL_CTX
    ctx = harness.MODEL_CTX.get(model, 32768)
    text = corpus()
    cpt = CHARS_PER_TOKEN
    results, notes, tested = {}, [], 0
    for target in TARGETS:
        if target + 4000 > ctx:
            notes.append(f"{target // 1000}K skipped (ctx {ctx // 1000}K)")
            continue
        prompt = build(text, int(target * cpt))
        r = api.chat([{"type": "text", "text": prompt}], max_tokens=4000, timeout=3600)
        real = r["usage"].get("prompt_tokens") or target
        cpt = cpt * target / real  # calibrate for the next length
        m = re.search(r"\{.*\}", r["text"], re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
            strict = r["text"].strip().startswith("{") and r["text"].strip().endswith("}")
        except json.JSONDecodeError:
            got, strict = {}, False
        right = sum(1 for _, k, v in FACTS if str(got.get(k, "")).strip() == str(v))
        results[f"{real // 1000}K"] = {"facts": right, "strict_json": strict, "prefill_tps": r["timings"].get("prompt_per_second"),
                                       "seconds": r["seconds"]}
        notes.append(f"{real // 1000}K: {right}/3{'' if strict else ' (extra text)'} in {r['seconds']:.0f}s")
        tested += 1
    if not tested:
        return {"score": 0.0, "passed": False, "notes": "no length fits the context", "by_length": results}
    score = sum((v["facts"] / 3) * (0.9 + 0.1 * v["strict_json"]) for v in results.values()) / tested
    return {"score": round(score, 3), "passed": all(v["facts"] == 3 for v in results.values()),
            "notes": "; ".join(notes), "by_length": results}
