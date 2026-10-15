# Godot capability suite: godot-20261014

Scores per run (rep 1, rep 2), mean minutes per run in brackets; Claude Code harness, same prompts/time limits; Godot GPU jobs on a second GPU (worker LLM never unloaded), headless game runs available. Score 0..1 (pass = 1.0).

| model | port 3->4 | race logic | platformer+export | Movie Maker clip | mean | passed | worker min per 4 tasks |
|---|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | **1.00 1.00** (2m) | 0.96 1.00 (18m) | 0.35 0.70 (44m) | 0.70 1.00 (14m) | 0.84 | 4/8 | 77 |
| gemma4-26b-a4b | **1.00 1.00** (3m) | **1.00 1.00** (8m) | **1.00 1.00** (15m) | **1.00 1.00** (5m) | 1.00 | 8/8 | 31 |
| mellum2.1-12b | 0.00 (3m) | 0.00 (1m) | 0.25 (1m) | 0.15 (0m) | 0.10 | 0/4 | 6 |
| bonsai2-27b | **1.00 1.00** (19m) | **1.00 1.00** (26m) | **1.00 1.00** (25m) | **1.00 1.00** (20m) | 1.00 | 8/8 | 91 |
| qwen3.8-27b-q3 | **1.00** (11m) | 0.00 (12m) | 0.25 (13m) | 0.15 (9m) | 0.35 | 1/4 | 45 |

## How they worked (tool use per run)

| model | task | turns | peak ctx | cookbook | api | demos | docs | checks | headless runs | GPU runs | renders | exports | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3.6-35b-a3b | port 3->4 | 13 | 21399 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | check clean (godot-lint: 7 file(s), 0 Godot 3 idiom(s) - clean; GODOT_CHECK 6 script(s), 0 failed); tests 9/9 |
| qwen3.6-35b-a3b | race logic | 32 | 54837 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | check clean; tests 21/21 |
| qwen3.6-35b-a3b | platformer+export | 125 | 97214 | 7 | 18 | 0 | 0 | 7 | 26 | 0 | 0 | 0 | check clean; inputs ok; exports linux=NO web=NO; project (no export): start=True finish=t=6.1 coins 5/5 |
| qwen3.6-35b-a3b | Movie Maker clip | 47 | 56100 | 2 | 17 | 0 | 0 | 4 | 0 | 0 | 11 | 0 | check clean; Movie Maker frames 90; mp4 1920x1080 90 frames; means [66, 68, 68], motion 23.9, highlights 0.052, colour 62 |
| gemma4-26b-a4b | port 3->4 | 11 | 23437 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | check clean (godot-lint: 7 file(s), 0 Godot 3 idiom(s) - clean; GODOT_CHECK 6 script(s), 0 failed); tests 9/9 |
| gemma4-26b-a4b | race logic | 13 | 34119 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | check clean; tests 21/21 |
| gemma4-26b-a4b | platformer+export | 63 | 76536 | 0 | 0 | 0 | 0 | 4 | 3 | 2 | 0 | 2 | check clean; inputs ok; exports linux=yes web=yes; exported build: start=True finish=t=6.1 coins 5/5 |
| gemma4-26b-a4b | Movie Maker clip | 14 | 31018 | 0 | 4 | 0 | 0 | 1 | 0 | 0 | 4 | 0 | check clean; Movie Maker frames 90; mp4 1920x1080 90 frames; means [31, 29, 23], motion 24.7, highlights 0.060, colour 18 |
| mellum2.1-12b | port 3->4 | 2 | 34469 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check NOT clean (godot-lint: 7 file(s), 13 Godot 3 idiom(s) - fix them; GODOT_CHECK 6 script(s), 4 failed); tests 0/9 |
| mellum2.1-12b | race logic | 2 | 26956 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | scripts/race_logic.gd missing |
| mellum2.1-12b | platformer+export | 6 | 34442 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean; inputs ok; exports linux=NO web=NO; project (no export): start=False finish=t=1.0 coins 0/5 |
| mellum2.1-12b | Movie Maker clip | 3 | 25538 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean; Movie Maker frames 0; out/clip.mp4 missing |
| bonsai2-27b | port 3->4 | 23 | 46600 | 0 | 2 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | check clean (godot-lint: 7 file(s), 0 Godot 3 idiom(s) - clean; GODOT_CHECK 6 script(s), 0 failed); tests 9/9 |
| bonsai2-27b | race logic | 77 | 104565 | 4 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | check clean; tests 21/21 |
| bonsai2-27b | platformer+export | 54 | 103602 | 5 | 3 | 0 | 0 | 3 | 1 | 1 | 0 | 2 | check clean; inputs ok; exports linux=yes web=yes; exported build: start=True finish=t=5.9 coins 5/5 |
| bonsai2-27b | Movie Maker clip | 83 | 125347 | 3 | 19 | 4 | 0 | 6 | 0 | 0 | 2 | 0 | check clean; Movie Maker frames 90; mp4 1920x1080 90 frames; means [36, 38, 38], motion 30.0, highlights 0.160, colour 26 |
| qwen3.8-27b-q3 | port 3->4 | 18 | 27393 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean (godot-lint: 7 file(s), 0 Godot 3 idiom(s) - clean; GODOT_CHECK 6 script(s), 0 failed); tests 9/9 |
| qwen3.8-27b-q3 | race logic | 2 | 20592 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | scripts/race_logic.gd missing |
| qwen3.8-27b-q3 | platformer+export | 14 | 26341 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean; inputs ok; exports linux=NO web=NO; project (no export): start=False finish=t=1.0 coins 0/5 |
| qwen3.8-27b-q3 | Movie Maker clip | 13 | 23164 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | check clean; Movie Maker frames 0; out/clip.mp4 missing |

Clip frames (first/middle/last per model): /home/user/StudioProjects/evals/runs/godot-20261014/clips_contact_sheet.jpg
