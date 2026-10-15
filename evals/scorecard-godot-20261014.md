# Godot capability suite: godot-20261014

One run per task, Claude Code harness, same prompts/time limits; GPU jobs on the RTX 2060 (worker LLM never unloaded), headless game runs available. Score 0..1 (pass = 1.0).

| model | port 3->4 | race logic | platformer+export | Movie Maker clip | mean | passed | worker min |
|---|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | **1.00** (2m) | 0.96 (27m) | 0.35 (52m) | 0.70 (20m) | 0.75 | 1/4 | 101 |
| gemma4-26b-a4b | **1.00** (3m) | **1.00** (11m) | **1.00** (11m) | **1.00** (7m) | 1.00 | 4/4 | 32 |
| mellum2.1-12b | 0.00 (3m) | 0.00 (1m) | 0.25 (1m) | 0.15 (0m) | 0.10 | 0/4 | 6 |
| bonsai2-27b | **1.00** (31m) | **1.00** (23m) | **1.00** (22m) | **1.00** (19m) | 1.00 | 4/4 | 95 |
| qwen3.8-27b-q3 | **1.00** (11m) | 0.00 (12m) | 0.25 (13m) | 0.15 (9m) | 0.35 | 1/4 | 45 |

## How they worked (tool use per run)

| model | task | turns | peak ctx | cookbook | api | demos | docs | checks | headless runs | GPU runs | renders | exports | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | port 3->4 | 12 | 43123 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | check clean (godot-lint: 7 file(s), 0 Godot 3 idiom(s) - clean; GODOT_CHECK 6 script(s), 0 failed); tests 9/9 |
| qwen3.6-35b-a3b | race logic | 62 | 94292 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | check clean; tests 20/21; no_countdown_while_racing:  |
| qwen3.6-35b-a3b | platformer+export | - | 98032 | 7 | 18 | 0 | 0 | 7 | 26 | 0 | 0 | 0 | check clean; inputs ok; exports linux=NO web=NO; project (no export): start=True finish=NO coins 2/5 |
| qwen3.6-35b-a3b | Movie Maker clip | 91 | 101780 | 2 | 17 | 0 | 0 | 4 | 0 | 0 | 11 | 0 | check clean; Movie Maker frames 30; mp4 1920x1080 30 frames; means [11, 18, 18], motion 11.3, highlights 0.023, colour 16 |
| gemma4-26b-a4b | port 3->4 | 13 | 43038 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | check clean (godot-lint: 7 file(s), 0 Godot 3 idiom(s) - clean; GODOT_CHECK 6 script(s), 0 failed); tests 9/9 |
| gemma4-26b-a4b | race logic | 25 | 67625 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | check clean; tests 21/21 |
| gemma4-26b-a4b | platformer+export | 32 | 51416 | 0 | 0 | 0 | 0 | 4 | 3 | 2 | 0 | 2 | check clean; inputs ok; exports linux=yes web=yes; exported build: start=True finish=t=5.9 coins 5/5 |
| gemma4-26b-a4b | Movie Maker clip | 29 | 44524 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 4 | 0 | check clean; Movie Maker frames 90; mp4 1920x1080 90 frames; means [71, 106, 91], motion 82.8, highlights 0.307, colour 123 |
| mellum2.1-12b | port 3->4 | 2 | 34469 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check NOT clean (godot-lint: 7 file(s), 13 Godot 3 idiom(s) - fix them; GODOT_CHECK 6 script(s), 4 failed); tests 0/9 |
| mellum2.1-12b | race logic | 2 | 26956 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | scripts/race_logic.gd missing |
| mellum2.1-12b | platformer+export | 6 | 34442 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean; inputs ok; exports linux=NO web=NO; project (no export): start=False finish=t=1.0 coins 0/5 |
| mellum2.1-12b | Movie Maker clip | 3 | 25538 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean; Movie Maker frames 0; out/clip.mp4 missing |
| bonsai2-27b | port 3->4 | 1 | 114397 | 0 | 2 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | check clean (godot-lint: 7 file(s), 0 Godot 3 idiom(s) - clean; GODOT_CHECK 6 script(s), 0 failed); tests 9/9 |
| bonsai2-27b | race logic | 52 | 108788 | 4 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | check clean; tests 21/21 |
| bonsai2-27b | platformer+export | 44 | 80774 | 5 | 3 | 0 | 0 | 3 | 1 | 1 | 0 | 2 | check clean; inputs ok; exports linux=yes web=yes; exported build: start=True finish=t=5.9 coins 5/5 |
| bonsai2-27b | Movie Maker clip | 66 | 111935 | 3 | 19 | 4 | 0 | 6 | 0 | 0 | 2 | 0 | check clean; Movie Maker frames 90; mp4 1920x1080 90 frames; means [53, 74, 74], motion 39.3, highlights 0.150, colour 45 |
| qwen3.8-27b-q3 | port 3->4 | 18 | 27393 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean (godot-lint: 7 file(s), 0 Godot 3 idiom(s) - clean; GODOT_CHECK 6 script(s), 0 failed); tests 9/9 |
| qwen3.8-27b-q3 | race logic | 2 | 20592 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | scripts/race_logic.gd missing |
| qwen3.8-27b-q3 | platformer+export | 14 | 26341 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean; inputs ok; exports linux=NO web=NO; project (no export): start=False finish=t=1.0 coins 0/5 |
| qwen3.8-27b-q3 | Movie Maker clip | 13 | 23164 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean; Movie Maker frames 0; out/clip.mp4 missing |

Clip frames (first/middle/last per model): /home/user/StudioProjects/evals/runs/godot-20261014/clips_contact_sheet.jpg
