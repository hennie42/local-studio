"""Easy: find and fix three bugs in a small module, guided by a spec; write tests."""
import subprocess
import textwrap

AREA = "coding"
TITLE = "Fix 3 bugs in textutils.py to match spec, add tests"
KIND = "agent"
TIMEOUT = 900

PROMPT = """textutils.py does not match SPEC.md. Fix the functions so they meet the spec exactly
(keep the signatures), then create test_textutils.py with at least 9 assert-based test_* functions
(3 per function, including edge cases) and an `if __name__ == "__main__":` block that runs them and
prints "N tests passed". Run `python3 test_textutils.py` and make sure it passes. Do not add dependencies."""

SPEC = """# textutils spec
- slugify(s): lowercase; strip leading/trailing whitespace; collapse any run of whitespace into one "-".
- truncate(s, n): if len(s) <= n return s unchanged; otherwise return a string of at most n characters
  ending in "..." (for n < 3 return the first n characters of s, no dots).
- word_count(s): number of words separated by any whitespace (spaces, tabs, newlines); 0 for empty or
  whitespace-only strings.
"""

CODE = """def slugify(s):
    return s.lower().replace(" ", "-")

def truncate(s, n):
    if len(s) <= n:
        return s
    return s[:n] + "..."

def word_count(s):
    return len(s.split(" "))
"""

HIDDEN = r'''
import sys
sys.path.insert(0, ".")
from textutils import slugify, truncate, word_count
checks = [
    slugify("  Hello   World\tFoo\n") == "hello-world-foo",
    slugify("") == "",
    slugify("ABC") == "abc",
    truncate("abcdefghij", 5) == "ab...",
    truncate("abc", 3) == "abc",
    truncate("abcd", 3) == "...",
    truncate("abcdef", 2) == "ab",
    all(len(truncate("x" * 50, n)) <= n for n in range(0, 20)),
    word_count("") == 0,
    word_count(" \t\n ") == 0,
    word_count("a  b\tc\nd") == 4,
    word_count("one") == 1,
]
print(sum(checks), len(checks))
'''


def setup(ws):
    (ws / "SPEC.md").write_text(SPEC)
    (ws / "textutils.py").write_text(CODE)


def grade(ws):
    hidden = subprocess.run(["python3", "-I", "-c", HIDDEN], cwd=ws, capture_output=True, text=True, timeout=60)
    try:
        ok, total = map(int, hidden.stdout.split())
    except ValueError:
        return {"score": 0.0, "passed": False, "notes": f"hidden tests crashed: {hidden.stderr[-200:]}"}
    own = subprocess.run(["python3", "-E", "-s", "test_textutils.py"], cwd=ws, capture_output=True, text=True, timeout=60) \
        if (ws / "test_textutils.py").exists() else None
    own_ok = own is not None and own.returncode == 0
    n_tests = (ws / "test_textutils.py").read_text().count("def test_") if (ws / "test_textutils.py").exists() else 0
    score = 0.7 * ok / total + 0.15 * own_ok + 0.15 * min(n_tests, 9) / 9
    return {"score": round(score, 3), "passed": ok == total and own_ok and n_tests >= 9,
            "notes": f"hidden {ok}/{total}, own tests {'pass' if own_ok else 'FAIL'} ({n_tests} tests)"}
