# Retro: DontPanicIsland

53 findings, 1185 minutes lost in total. Format and loop: docs/self-improvement-design.md.

## Who caught the problems

| caught by | findings | share |
|---|---|---|
| user | 25 | 47% |
| director | 19 | 36% |
| probe | 4 | 8% |
| measurement | 3 | 6% |
| check | 2 | 4% |

**Escape rate: 47%** (25 of 53 found by the user, no check caught them). Lower is better; compare with the next project.

## Causes

| cause | findings | minutes | by the user | examples |
|---|---|---|---|---|
| logic | 7 | 195 | 5 | garbled text at the top; camera turns and zooms snapped back after the intro |
| engine-api | 10 | 160 | 6 | clicks did nothing (only the wheel zoomed); clicking water would crash the click handler |
| process | 3 | 135 | 0 | a commit went in with a failing check; a cleanup command killed its own shell (twice) |
| spec | 5 | 130 | 3 | numbers unreadable (squashed shapes); palms covered the numbers |
| tooling | 8 | 125 | 0 | a dispatcher dry run marked two tickets escalated in the real project; dry-run clones failed to create |
| environment | 6 | 125 | 5 | black screen and noise when the user started the game; black bars around the game |
| test | 4 | 110 | 0 | an input probe failed once; T16 attempt 1 failed though it was correct |
| spatial | 4 | 105 | 3 | the alien floated beside the UFO; UFO above the frame and the island cropped in 16:9 |
| art | 4 | 60 | 2 | a large white square above the UFO; the towel looked like the Dutch flag |
| audio | 1 | 40 | 1 | music: one chord every ~2 s, then silence |
| timeout | 1 | 0 | 0 | T05, T09, T14 needed the retry model |

## Workers (dispatcher attempts)

| model | attempt | attempts | passed | rate | minutes |
|---|---|---|---|---|---|
| gemma4-26b-a4b | first | 18 | 12 | 67% | 443 |
| bonsai2-27b | retry | 6 | 6 | 100% | 214 |
| gemma4-26b-a4b | followup | 3 | 0 | 0% | 123 |

19 tickets passed, 0 escalated.

## Guards

### In place (47)

- **checklist**: art specs are checked in a screenshot from the gameplay camera (F07)
- **checklist**: screenshots in a wide and a tall window for anything framed (F18)
- **checklist**: art specs: check flags/symbols against real-world meanings (F20)
- **checklist**: every refused player action gives feedback; tools say what they did (F24)
- **checklist**: validate every new test against a reference or a dry implementation (passable), not only that it fails cleanly (F29)
- **checklist**: chain checks and commit with &&, never ; (F30)
- **checklist**: stop processes by PID or systemd unit (F31)
- **checklist**: screenshots from in-game probes (viewport texture), not Movie Maker (F37)
- **checklist**: tickets over ~15 min of expected work get split (F38)
- **checklist**: a ticket names every code path that triggers its behaviour (player input, autopilot, tools) and the data each one passes (F42)
- **checklist**: run probes on several islands/seeds before relying on them; effects add children with readable unique names; sample motion at 3+ points (F44)
- **checklist**: bots never work around a state the rules can't reach: fail loudly, test the rules (F45)
- **checklist**: rules tests cover the ends: game over mid-move, win after a loss, win and lose in one move (F46)
- **helper**: studio_audio: beats() helper + a measured loop check (onset grid, loop flag) (F21)
- **lint**: godot-lint fullrect-mouse (F09)
- **lint**: godot-lint null-cast (F10)
- **lint**: godot-lint label3d-theme (F11)
- **lint**: godot-lint anchor-grow (F12, F13)
- **lint**: godot-lint trig-degrees; AGENTS-godot.md 8: facing atan2(dir.x, dir.z) (F50)
- **lint**: godot-lint substr-prefix; AGENTS-godot.md 11: no in-range sentinels (F51)
- **lint**: godot-lint fileaccess-null (F52)
- **pitfall**: is_instance_valid before freeing in timers (F27)
- **pitfall**: typed variables from Variants; typed arrays; Control-only methods (F39)
- **pitfall**: AGENTS-godot.md 9: mark input you act on as handled; ProbeBase.press/hold for menu probes (F47)
- **pitfall**: AGENTS-godot.md 10: Input polling sees keys while a LineEdit has focus (F48)
- **pitfall**: AGENTS-godot.md 7: skippable sequences: node-owned tweens, one per property, one exit (F49)
- **routing**: routing godot.attempts.order: Gemma, Bonsai fresh, Bonsai follow-up (F36)
- **template**: template project.godot: stretch aspect expand (F15)
- **template**: probe base waits for the game state, never a fixed time (F28)
- **template**: GameEvent: blocked-3D check and message on the web (F34)
- **template**: template ProbeBase.click: motion to the target before press and release (F53)
- **test**: tests/test_playtest_rules.gd (F23)
- **test**: tests/play_input (turn/zoom after the intro) (F26)
- **tool**: dry runs in a registered scratch clone (F01)
- **tool**: --no-hardlinks, clones on the data disk (F02)
- **tool**: dry-run clones are registered for their run (F03)
- **tool**: every failed attempt saved as .studio/attempts/<id>-<n>.patch (F04)
- **tool**: clones copy the LFS objects (F05)
- **tool**: records 'no changes' (F06)
- **tool**: studio-play frees the small GPU first (F08)
- **tool**: studio-assets check: Godot projects are also measured in Godot as instanced (lib/godot/studio_measure.gd, stored as measured_godot); a warning when the origin lies outside the mesh, also for origin: keep and skinned models (F17)
- **tool**: measure contrast/saturation/sharpness before and after visual changes (F32)
- **tool**: studio-serve (https, LAN certificate) (F33)
- **tool**: tests/look.gd in the game: polish variants of one view in one run, for studio-shotdiff (measured: board detail within 1 % of polish-off at home/far zoom, +3-4 % close up; the near blur has no measurable effect, so it stays); skill checklist: measure look changes on one view in one run (F40)
- **tool**: new lint rules start as warnings (GODOT_LINT_PITFALLS_FATAL), fatal once the projects are clean (F41)
- **tool**: bin/studio-play: display GPU detection (sysfs connector -> PCI bus -> nvidia-smi index); skill: measure performance on the display GPU, not via the broker's Godot GPU (F43)

### One-offs (6)

- **none**: one-off (tip queue) (F14)
- **none**: one-off (F16, F19, F22, F25)
- **none**: parked by the user (F35)

