"""Hard-ish: implement two C++ data structures against a header spec; CMake build; hidden tests."""
import shutil
import subprocess
import textwrap

AREA = "coding"
TITLE = "C++17: RingBuffer<T> + LruCache<K,V> to header spec, CMake, own tests"
KIND = "agent"
TIMEOUT = 1800

PROMPT = """Implement the two class templates declared and documented in include/structures.hpp
(RingBuffer and LruCache) so they meet the documented behaviour exactly. Keep the public API unchanged.
Write tests in tests/test_structures.cpp (plain asserts, no frameworks) and make the CMake build and
`ctest --test-dir build --output-on-failure` pass:
  cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure
C++17, standard library only."""

FILES = {
    "CMakeLists.txt": """
        cmake_minimum_required(VERSION 3.20)
        project(structures CXX)
        set(CMAKE_CXX_STANDARD 17)
        set(CMAKE_CXX_STANDARD_REQUIRED ON)
        add_compile_options(-Wall -Wextra -Werror)
        enable_testing()
        add_executable(test_structures tests/test_structures.cpp)
        target_include_directories(test_structures PRIVATE include)
        add_test(NAME structures COMMAND test_structures)
        """,
    "include/structures.hpp": """
        #pragma once
        #include <cstddef>
        #include <optional>
        #include <stdexcept>

        // Fixed-capacity FIFO ring buffer.
        // - capacity is set at construction; capacity 0 throws std::invalid_argument.
        // - push(v): appends; if full, overwrites the OLDEST element (and size stays == capacity).
        // - pop(): removes and returns the oldest element; std::nullopt if empty.
        // - front()/back(): oldest/newest element; throw std::out_of_range if empty.
        // - operator[](i): i-th element counting from the oldest (0 = oldest); throws std::out_of_range if i >= size().
        // - size(), capacity(), empty(), full().
        template <typename T>
        class RingBuffer {
        public:
            explicit RingBuffer(std::size_t capacity);
            void push(const T& value);
            std::optional<T> pop();
            const T& front() const;
            const T& back() const;
            const T& operator[](std::size_t i) const;
            std::size_t size() const;
            std::size_t capacity() const;
            bool empty() const;
            bool full() const;
            // TODO: implement (add private members as needed)
        };

        // Least-recently-used cache with fixed capacity (capacity 0 throws std::invalid_argument).
        // - get(key): returns the value and marks the key as most recently used; std::nullopt if absent.
        // - put(key, value): inserts or updates (and marks most recently used). If inserting a new key
        //   into a full cache, first evicts the least recently used key.
        // - contains(key): true if present; does NOT change recency.
        // - size(), capacity().
        // Operations should be O(1) average.
        template <typename K, typename V>
        class LruCache {
        public:
            explicit LruCache(std::size_t capacity);
            std::optional<V> get(const K& key);
            void put(const K& key, const V& value);
            bool contains(const K& key) const;
            std::size_t size() const;
            std::size_t capacity() const;
            // TODO: implement (add private members as needed)
        };
        """,
    "tests/test_structures.cpp": """
        #include "structures.hpp"
        #include <cassert>

        int main() {
            // TODO: write tests
            return 0;
        }
        """,
}

HIDDEN = r"""
#include "structures.hpp"
#include <cstdio>
#include <string>
static int ok = 0, total = 0;
#define CHECK(c) do { ++total; if (c) ++ok; else std::printf("FAIL %s\n", #c); } while (0)
template <class F> bool throws(F f) { try { f(); } catch (...) { return true; } return false; }
int main() {
    CHECK(throws([] { RingBuffer<int> r(0); }));
    RingBuffer<int> r(3);
    CHECK(r.empty() && !r.full() && r.capacity() == 3);
    CHECK(!r.pop().has_value());
    CHECK(throws([&] { r.front(); }));
    r.push(1); r.push(2); r.push(3);
    CHECK(r.full() && r.size() == 3 && r.front() == 1 && r.back() == 3);
    r.push(4);
    CHECK(r.size() == 3 && r.front() == 2 && r.back() == 4 && r[0] == 2 && r[2] == 4);
    CHECK(throws([&] { r[3]; }));
    auto p = r.pop();
    CHECK(p && *p == 2 && r.size() == 2 && r.front() == 3);
    r.push(5); r.push(6); r.push(7);
    CHECK(r[0] == 5 && r[1] == 6 && r[2] == 7);
    RingBuffer<std::string> rs(2); rs.push("a"); rs.push("b"); rs.push("c");
    CHECK(rs.front() == "b" && rs.back() == "c");

    CHECK(throws([] { LruCache<int, int> c(0); }));
    LruCache<std::string, int> c(2);
    c.put("a", 1); c.put("b", 2);
    CHECK(c.size() == 2 && c.get("a") == std::optional<int>(1));
    c.put("c", 3);  // evicts b (a was used more recently)
    CHECK(!c.contains("b") && c.contains("a") && c.contains("c"));
    CHECK(c.contains("a"));  // contains must not refresh recency
    c.put("d", 4);  // evicts a (c was put after a's get; contains didn't refresh a)
    CHECK(!c.contains("a") && c.contains("c") && c.contains("d"));
    c.put("c", 30);  // update refreshes c
    c.put("e", 5);   // evicts d
    CHECK(!c.contains("d") && c.get("c") == std::optional<int>(30) && c.size() == 2 && c.capacity() == 2);
    CHECK(!c.get("zzz").has_value());
    std::printf("%d %d\n", ok, total);
    return 0;
}
"""


def setup(ws):
    for rel, body in FILES.items():
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip("\n"))


def grade(ws):
    own = subprocess.run("rm -rf _gradebuild && cmake -S . -B _gradebuild >/dev/null && cmake --build _gradebuild >/dev/null "
                         "&& ctest --test-dir _gradebuild --output-on-failure >/dev/null", shell=True, cwd=ws,
                         capture_output=True, text=True, timeout=600)
    own_ok = own.returncode == 0
    own_tests = (ws / "tests/test_structures.cpp").read_text().count("assert(") if (ws / "tests/test_structures.cpp").exists() else 0
    (ws / "_hidden.cpp").write_text(HIDDEN)
    comp = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-Iinclude", "_hidden.cpp", "-o", "_hidden"],
                          cwd=ws, capture_output=True, text=True, timeout=300)
    if comp.returncode != 0:
        shutil.rmtree(ws / "_gradebuild", ignore_errors=True)
        return {"score": round(0.1 * own_ok, 3), "passed": False,
                "notes": f"hidden tests don't compile: {comp.stderr.strip().splitlines()[0][:150] if comp.stderr.strip() else '?'}"}
    run = subprocess.run(["./_hidden"], cwd=ws, capture_output=True, text=True, timeout=60)
    try:
        ok, total = map(int, run.stdout.strip().splitlines()[-1].split())
    except Exception:
        return {"score": 0.1 * own_ok, "passed": False, "notes": f"hidden run crashed (exit {run.returncode})"}
    fails = [l[5:] for l in run.stdout.splitlines() if l.startswith("FAIL ")]
    for f in ("_hidden", "_hidden.cpp"):
        (ws / f).unlink(missing_ok=True)
    shutil.rmtree(ws / "_gradebuild", ignore_errors=True)
    score = 0.75 * ok / total + 0.15 * own_ok + 0.10 * min(own_tests, 10) / 10
    return {"score": round(score, 3), "passed": ok == total and own_ok and own_tests >= 10,
            "notes": f"hidden {ok}/{total}; own build+ctest {'pass' if own_ok else 'FAIL'} ({own_tests} asserts)"
                     + (f"; failed: {fails[0][:80]}" if fails else "")}
