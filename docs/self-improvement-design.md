# Self-improvement: learning from every clip and game

**Status: v1 built** (approved by the user the same day; first retro: Don't Panic Island).

**Goal:** every mistake in a clip or game makes the studio better at the next one, measurably. The principle:
**turn a mistake into a guard, not a note.** A lesson in prose helps only if someone reads it at the right moment;
a lint rule, a tested recipe, a template file or a routing setting fires on its own. (The pilot fixed the same Godot
anchoring pitfall twice in different files because nothing caught it.)

## The loop: capture, classify, guard, measure

| step | what | where |
|---|---|---|
| **Capture** | one line per problem: what went wrong, the root cause, who caught it, the cost, the fix, the guard. The director adds a line with every fix; the user's playtest findings go in too. Attempt data (model, minutes, exit, check output) is already in the dispatcher's state. | `retros/<Project>/findings.jsonl` in this repo (the studio is what learns, across projects) |
| **Classify** | a fixed set of causes, so they can be counted (below) | the `cause` field |
| **Guard** | each recurring or costly cause gets a guard that fires by itself: a lint rule, a tested recipe or helper, a template file, a ticket-writing checklist item, a worker pitfall in the ticket preamble, a routing setting | `guard` field: `{kind, ref, status: done|todo|none}` |
| **Measure** | `studio-retro <project>` adds it all up: problems per cause and their cost, the **escape rate** (problems the user found that no check caught), first-try rate per model, open guards. The next project's retro is compared with this one. | `retros/<Project>/retro-<date>.md` |

**Causes:** `spec` (the director's ticket or art spec was wrong or missing), `test` (the director's check was
wrong), `engine-api` (an engine API misused: Godot 3 idioms, Control-only methods on 3D nodes, defaults like
`mouse_filter`), `spatial` (positions, scales, origins, angles), `logic` (game logic or state), `timeout` (a ticket
too big for its time box), `tooling` (studio tools: dispatcher, broker, clones, LFS), `environment` (machine, GPU
memory, browsers, window manager), `art` (looks, style, readability), `audio`, `process` (how the director works).

**Caught by:** `check` (an acceptance check or test), `probe` (a real-input or screenshot probe), `director`
(review, screenshots, logs), `measurement` (numbers, e.g. contrast or the onset grid), `user` (playtest). The
escape rate is `user / all`; the aim is to push findings left: user -> director -> probe/check.

## Finding format (one JSON object per line)

```json
{"id": "F09", "phase": "playtest", "what": "clicks did nothing",
 "cause": "engine-api", "why": "the HUD's full-screen root Control kept the default mouse_filter STOP",
 "caught_by": "user", "cost_min": 30, "fix": "c151e12",
 "guard": {"kind": "lint", "ref": "godot-lint full-rect-mouse", "status": "done"}}
```

`guard.kind`: `lint`, `helper` (a tested helper or cookbook recipe), `template` (a file every new project gets),
`checklist` (the director's ticket-writing checklist in the skill), `pitfall` (the worker pitfalls in
template/AGENTS-godot.md, read with every ticket), `routing`, `tool`, `test` (a project test), `none` (one-off).

## When

- During a project: the director appends a finding with every fix (a minute each).
- At the end of every clip or game: `studio-retro <project>`, then the director turns the open guards into real
  ones (or marks them `none` with a reason). About 15 minutes plus the guards' own work.
- The next project starts by reading the last retro's "what to do differently" section.

## Later

- A "Lessons" panel in the progress dashboard (escape rate and cost per cause across projects).
- The worker pitfalls list stays short (top ~10 by frequency), because it is read with every ticket.
