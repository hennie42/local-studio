Read AGENTS.md and PLAN.md first (this is step "rain" of PLAN.md). This is pure Python image processing
(numpy + Pillow; no Unreal). Rendered frames are PNGs named like Main.0000.png ... in a directory.

Write Scripts/rain_comp.py: `python3 Scripts/rain_comp.py <in_dir> <out_dir> [--fps 30] [--seed 11]` that writes, for
every input frame (same names), a composited frame to out_dir:
1. Rain, two depth layers, drawn as anti-aliased line streaks slanted ~8 degrees from vertical (top-right to
   bottom-left), with temporal coherence: each streak has a fixed random x, phase, speed and length (from the seed),
   and its y position advances by speed * frame_index (wrapping around the frame height), so rain falls smoothly
   between frames instead of flickering.
   - far layer: ~1,400 streaks at 1080p (scale counts/lengths with frame height), length 18-35 px, 1 px wide,
     speed 45-70 px/frame, opacity 0.12-0.22;
   - near layer: ~180 streaks, length 70-140 px, 2-3 px wide, speed 120-180 px/frame, opacity 0.25-0.45, with a
     slight blur (Gaussian radius 1.5) on that layer.
   Rain catches the light: a streak's colour is (0.35 * white + 0.65 * the colour of a heavily blurred copy of the
   frame at that spot), brightened x2.2, then the layers are added (screen blend) onto the frame.
2. Letterbox to 2.39:1: black bars top and bottom so the visible image height is round(width / 2.39)
   (1920x1080 -> 803 px tall picture, bars 138 px top and 139 px bottom).
3. Print progress every 50 frames and a final summary (frames, seconds).
Must handle any resolution (the preview is 960x540, the final 1920x1080) and be reasonably fast (vectorised numpy or
PIL ImageDraw on layer images; target < 0.5 s per 1080p frame).
Test it on Renders/preview (if it exists) into Renders/comp_preview, verify: same frame count; the top 138/2 rows at
preview scale are pure black; the picture area differs from the source (rain added); and that streak positions move
between consecutive frames. Then look at two composited frames (read the PNGs) and judge whether the rain reads as
rain. Do not commit. Report the checks.
