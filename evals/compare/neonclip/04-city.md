Read AGENTS.md and PLAN.md first (this is step "city" of PLAN.md). Use Scripts/studio_ue.py (`su`; read its
docstring and the signatures of fresh_level, mesh_actor, spawn, face_point, wall_panel, post_process first). Assets
already exist: meshes under /Game/City/Meshes (su.find_assets("/Game/City/Meshes", "StaticMesh"): SM_Tower_01..08 and
SM_Pyramid; towers are 100 m = 10,000 cm tall, base at z = 0; the pyramid is 400 x 400 x 150 m) and materials in
/Game/City/Materials (M_Win_A/B/C, M_Ad_01..08, M_Pyramid, M_Wet, M_Flare, M_Light_White, M_Light_Red, M_Hull).

Write Scripts/build_city.py (re-runnable: su.fresh_level) building level /Game/Maps/City, with random.seed(7) so it
is deterministic, then su.save(). Contents (units cm):
1. Ground: one Plane ('Plane' basic shape, 100 x 100 cm) at z = 0, scale (4000, 4000, 1) = 4 km x 4 km, material M_Wet,
   label Ground.
2. Towers on a grid: block centres x, y in range(-60000, 60001, 6000); skip blocks whose centre has |y| < 3000
   (keeps a wide avenue along the x axis) and skip blocks with |x - 12000| < 6000 and |y - 9000| < 6000 (a clearing
   for the hero tower). For each block place one random SM_Tower_0N at the block centre (random offset +-500),
   yaw random in {0, 90, 180, 270}, scale (s, s, h) with s in [0.8, 1.2] and height factor
   h = clamp(1.7 - dist/50000 + uniform(-0.2, 0.2), 0.4, 1.6) (dist = distance of the block centre from the origin),
   movable=True, material random among M_Win_A/B/C. Label towers Tower_<i>. Scale factors are plain multipliers of
   the 100 m mesh: h = 1.6 means a 160 m tower. Do NOT multiply scales by 100.
3. Hero tower: SM_Tower_01 at (12000, 9000, 0), scale (1.3, 1.3, 1.5), M_Win_B, movable, label HeroTower.
   Giant billboard on its face towards the avenue (-y): pos, n = su.face_point(hero, "-y", offset_cm=50); then set the
   panel centre to (pos[0], pos[1], 9000) and call su.wall_panel(centre, n, 3000, 6000, material=M_Ad_01,
   label="HeroAd"). PointLight 1,500 cm in front of the panel (centre + n * 1500): colour (255, 40, 120),
   intensity 400000, attenuation radius 9000, label HeroAdGlow.
4. 12 more billboards: random.sample 12 towers within 30,000 cm of the origin (not the hero). For each choose a face:
   the one towards the avenue ("-y" if the tower's y > 0 else "+y") with probability 1/2, otherwise "+x" or "-x".
   pos, n = su.face_point(tower, face, offset_cm=60, height_frac=uniform(0.5, 0.8)); su.wall_panel(pos, n, w, h, ...)
   with (w, h) = (2000, 4000) or (4000, 2000), random M_Ad_02..08, label Ad_<k>. PointLight at pos + n * 1200,
   intensity 150000, attenuation 6000, colour picked from magenta (255,40,200), cyan (40,200,255), red (255,50,50),
   orange (255,160,40), electric blue (60,80,255); label AdGlow_<k>.
5. Pyramid: SM_Pyramid at (160000, 0, 0), scale (1, 1, 1), material M_Pyramid, movable, label Pyramid. Flame flares on
   the 4 chimney tops at (160000 +- 11000, +-11000, 12000): a Sphere scaled 4 with M_Flare (label Flare_<n>) plus a
   PointLight colour (255, 120, 40), intensity 2,000,000, attenuation 30000 (label FlareLight_<n>).
6. Atmosphere (night, no sun): su.spawn(unreal.SkyLight) with real_time_capture True and intensity 0.25 (see how
   su.lighting does it); an ExponentialHeightFog (label Fog) with fog_density 0.06, fog_height_falloff 0.15,
   enable_volumetric_fog True, fog_inscattering_luminance (0.02, 0.025, 0.035); su.post_process(exposure_bias=7.0,
   bloom=1.6, vignette=0.6, grain=0.35); in that volume's settings also set override_scene_fringe_intensity True and
   scene_fringe_intensity 1.2 (get settings, set, set back).
   PointLight colours are unreal.Color with 0-255 integers (or unreal.LinearColor with 0-1 floats); never mix them up.
7. Verify inside the script and su.log the results; raise RuntimeError if any check fails:
   - every panel (HeroAd, Ad_*): actor up vector equals its facing normal n (+-0.01) (wall_panel guarantees this if
     used), its bounds are thin (smallest extent < 20 cm), and its centre lies within 100 cm of its tower's face
     (tower bounds origin + n * extent along that axis);
   - tallest tower (bounds extent z * 2) between 5,000 and 20,000 cm.
   su.log a summary: number of towers, billboards, lights, tallest tower in m.
Run with `studio ue-python {NAME}.uproject Scripts/build_city.py`, fix errors until it succeeds, then run it a second
time to prove it is re-runnable (same counts). Do not commit. Report the summary line from both runs.
