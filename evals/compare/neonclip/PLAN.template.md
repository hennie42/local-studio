# {NAME}: production plan (model comparison clip)

**Brief (user):** Blade Runner-ish. Slow flight, the city, lights, atmosphere, commercials. Rain, always rain. Reflections.
**Deliverable:** `out/{NAME}.mp4`: 10.0 s, 1920x1080 (2.39:1 letterbox inside 16:9), 30 fps, with a stereo score.
**Timing:** 72 BPM, 4/4: 1 bar = 3.333 s = 100 frames; 3 bars = 300 frames. Every cut lands on a bar line.
**Who:** every step below is done by the local worker; the same plan and prompts go to a second project made by a
different model, for a side-by-side comparison. The final render/encode/mux is run mechanically by the director.

## Look
Night, permanent rain, dense blue-grey fog with coloured light shafts. Dark glossy towers with thousands of warm
and cold lit windows. Giant animated commercials on facades (Japanese/Chinese text, neon reds, magentas, cyans) that
spill coloured light into fog and onto wet surfaces. Wet streets that mirror the neon. Flying cars ("spinners") with
headlights cross the frame. Far away: a giant stepped pyramid with flame flares (the reveal). Grade: teal shadows,
warm highlights, film grain, slight chromatic aberration, letterbox.

## Shots (sequence /Game/Cine/Main, 300 frames)
| # | frames | bar | shot | camera |
|---|---|---|---|---|
| 1 | 0-100 | 1 | **Establishing**: aerial glide over the city at ~250 m, towers sliding beneath, fog, a spinner crossing | slow forward push + slight descent, 28 mm |
| 2 | 100-200 | 2 | **Commercial**: lateral dolly past a giant vertical billboard on a tower at ~90 m, its light flooding the fog | sideways track, 35 mm |
| 3 | 200-300 | 3 | **Reveal**: rise in the avenue from ~30 m to ~220 m, tilting up as the pyramid with flame flares appears | crane up + tilt, 35 mm |

## World scale (cm)
Towers 3,000-16,000 tall, footprints 1,500-4,000; a 6,000-wide avenue along the x axis (|y| < 3,000); city
~120,000 x 120,000 around the origin; pyramid ~40,000 base / 15,000 tall at x = +160,000 (beyond the city edge).

## Steps (each has a mechanical acceptance check; one automatic retry with the check output)
| id | what | files | check |
|---|---|---|---|
| tex | procedural textures: 3 window atlases, 8 commercials with CJK text, puddle map | Scripts/make_textures.py, assets/tex/*.png | 12 PNGs with the right sizes |
| towers | Blender: 8 tower variants + stepped pyramid with 4 chimneys | Scripts/make_towers.py, assets/models/*.glb | 9 GLBs; bases at z=0; sizes in range |
| import | import assets; window/commercial/wet/flare/light/hull materials | Scripts/import_assets.py | meshes, textures, 17 materials exist |
| city | level /Game/Maps/City: ground, tower grid, hero billboard, 12 billboards, pyramid + flares, night atmosphere | Scripts/build_city.py | counts, tower heights, panels upright on their facades, pyramid placed |
| seq | sequence /Game/Cine/Main: 3 cameras, cuts at 0/100/200/300, spinners, Preview/Final render configs | Scripts/build_sequence.py | 300 frames, 3 cut sections, cameras exist |
| lookdev | render previews, look at them, tune fog/exposure/lights/materials to the Look | Scripts/lookdev.py, Renders/preview | 300 preview frames, not black, not blown out |
| rain | rain comp (numpy/PIL): 2 depth layers lit by the frame + 2.39:1 letterbox | Scripts/rain_comp.py | same frame count, bars black, rain added |
| score | score + sound design (studio_audio), 10.0 s | Scripts/score.py, audio/score.wav | 10.0 s, 48 kHz stereo, peak <= -1 dBFS |
| final | director (mechanical): Final render (1920x1080, 8 samples) -> rain comp -> encode -> mux | out/{NAME}.mp4 | ffprobe |
