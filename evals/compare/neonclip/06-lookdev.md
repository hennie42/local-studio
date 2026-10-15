Read AGENTS.md and PLAN.md first (this is step "lookdev" of PLAN.md: you are the cinematographer now). The level
/Game/Maps/City and the sequence /Game/Cine/Main exist (Scripts/build_city.py, Scripts/build_sequence.py). Your job:
make the clip look like the "Look" section of PLAN.md, by rendering previews, LOOKING at them, and tuning.

Loop (at most 4 rounds; each preview render takes a few minutes):
1. Render the preview: `studio ue-render {NAME}.uproject /Game/Render/Preview /Game/Cine/Main /Game/Maps/City`
   (frames land in Renders/preview as Main.0000.png ... Main.0299.png; delete old frames first).
2. Look at frames from every shot with your image-reading tool, at least Main.0030.png, Main.0090.png (shot 1),
   Main.0150.png (shot 2), Main.0230.png, Main.0290.png (shot 3). Judge: exposure (too dark / blown out?), fog
   (visible, coloured by the lights?), are the commercials readable and glowing, wet reflections, are the pyramid
   and its flames visible in the reveal, do the spinners read, anything broken (black frames, checkerboard
   textures, camera inside geometry).
3. Tune in Scripts/lookdev.py (Unreal Python, `studio ue-python {NAME}.uproject Scripts/lookdev.py`): it loads the
   level, adjusts existing actors and settings, and saves. Things you may change: post-process exposure bias, bloom,
   vignette, grain, colour grading (e.g. teal shadows / warm highlights via the settings' color_gain/offset
   overrides); fog density, height falloff, inscattering colour, volumetric fog distance and scattering; light
   intensities, colours and radii; commercial/window emissive strength (create NEW material assets under
   /Game/City/LookDev with su.texture_material / su.color_material and assign them to the actors; never re-create a
   material the level already uses: that orphans the panels); the pyramid's scale (keep its base at z = 0 and move
   the flares with it). Do NOT move or re-key cameras, and do not change the sequence or its timing.
Facts from earlier work in this setup (use them as starting points, not rules): night scenes with manual exposure
need exposure_bias around 6-8; height fog needs a fairly bright inscattering colour (e.g. 0.2-0.4) and a long
volumetric_fog_distance (~100,000 cm) to read at city scale; emissive above ~10 on large panels can blow out the
frame; a bigger pyramid (scale ~1.5) reads better from 50 km away.
Finish with a preview render of your final state (all 300 frames in Renders/preview), and leave the level saved in
that state: the final 1080p render will be made from it exactly as you leave it. Do not commit. Report what you
changed in each round and why (what you saw in the frames).
