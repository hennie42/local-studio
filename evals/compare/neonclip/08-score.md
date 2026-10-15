Read AGENTS.md and PLAN.md first (this is step "score" of PLAN.md). Use Scripts/studio_audio.py (`sa`; read its
docstring and functions first).

Write Scripts/score.py (python3) that renders audio/score.wav: exactly 10.0 s, 48 kHz stereo, peak -1.5 dBFS,
fade-in 1.0 s, fade-out 1.5 s, in the style of a slow 1980s analog-synth film score (Vangelis-like: warm detuned
saw "brass" pads with slow attacks and long reverb, sparse, melancholic). 72 BPM, 4/4: one bar = 3.333 s; the film
cuts on bar lines at 3.333 s and 6.667 s.
- Harmony, one chord per bar: bar 1 Am, bar 2 F, bar 3 C (the reveal: brighter, louder, add the octave; let it ring
  into the fade). Pads via sa.pad with long attack (~0.8 s) and release, brightness ~1500 Hz, plus
  sa.reverb(..., seconds 3.5, mix 0.45).
- A low bass note per bar (chord root, one octave below the pad).
- A sparse melody: 3-4 long notes in the A minor scale over bars 1-3 (sa.pluck through reverb, or a soft pad note).
- Rain bed for the whole length: band-limited noise (e.g. sa.lowpass of white noise at ~6 kHz), stereo-wide
  (different noise per channel via two Timeline.add calls panned -0.8/+0.8), quiet.
- Sound design synced to the cuts: distant thunder (low sa.impact, heavily low-passed) at 1.2 s; spinner pass
  (sa.whoosh panned left to right) starting at 3.1 s; a riser from 4.67 s into an impact exactly at 6.667 s (the
  reveal).
Run it, then verify with python3 (wave module) duration 10.0 s, 2 channels, 48000 Hz, peak <= -1.4 dBFS, and print
the times (s) of every placed event. Do not commit. Report the event list.
