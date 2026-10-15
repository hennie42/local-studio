Read AGENTS.md and PLAN.md first (this is step "seq" of PLAN.md). Use Scripts/studio_ue.py (`su`): sequence, bind,
key_transform, camera, camera_cuts, render_config, mesh_actor, look_at_rotation, save. The level /Game/Maps/City exists
(built by Scripts/build_city.py). Units cm, 30 fps, 300 frames.

Write Scripts/build_sequence.py (re-runnable). It must load the level with
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Maps/City"), first destroy any actors
whose label starts with "Cam_" or "Spinner" (from earlier runs), then:

1. Find the billboard: the actor labelled "HeroAd"; let A = its location (x, y, z) (it faces -y).
2. Three cameras (su.camera, which takes look_at and focal):
   - Cam_1 (frames 0-100, focal 28): aerial establishing. Keys: frame 0 at (-50000, -45000, 26000) looking at
     (20000, 20000, 4000); frame 100 at (-40000, -36500, 24500) looking at (25000, 25000, 4000).
   - Cam_2 (frames 100-200, focal 35): lateral dolly past the billboard. Keys: frame 100 at A + (-5500, -5475, -800),
     frame 200 at A + (1500, -5475, -200), both looking at A.
   - Cam_3 (frames 200-300, focal 35): crane up in the avenue to reveal the pyramid (at x = 160000). Keys: frame 200
     at (40000, -1000, 3000) looking at (90000, 0, 1500); frame 260 at (44000, -1000, 15000) looking at
     (160000, 0, 6000); frame 300 at (46000, -1000, 22000) looking at (160000, 0, 9000).
   Key each camera with su.key_transform using per-key rotations from su.look_at_rotation(position, target), i.e.
   keys of the form (frame, position, rotation); bind each camera with su.bind.
3. Sequence /Game/Cine/Main (su.sequence, 10 s @ 30 fps = 300 frames) with su.camera_cuts:
   [(Cam_1, 0, 100), (Cam_2, 100, 200), (Cam_3, 200, 300)].
4. Three spinners (flying cars). Each = a body: su.mesh_actor("Cube", scale=(4, 1.8, 1.0), material
   "/Game/City/Materials/M_Hull.M_Hull", movable=True, label Spinner_<n>) with children attached via
   child.attach_to_actor(body, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
   unreal.AttachmentRule.KEEP_WORLD, False): two headlights (Sphere scale 0.4, M_Light_White) at the front corners,
   one tail light (Sphere scale 0.4, M_Light_Red) at the back, and a PointLight (white, intensity 60000, attenuation
   4000) in front; set every child's root component mobility to MOVABLE. Animate only the body (children follow);
   yaw = direction of travel. Paths (straight lines, keys at the start and end frame):
   - Spinner_1: frames 0-100, crossing below Cam_1 at z 16000, from (-20000, -30000, 16000) to (-20000, 10000, 16000).
   - Spinner_2: frames 100-200, between Cam_2 and the billboard, from A + (-6000, -2500, -500) to
     A + (4000, -2500, -500).
   - Spinner_3: frames 200-300, from (50000, 3000, 9000) to (120000, 0, 12000), towards the pyramid.
   Bind each body and key its transform with su.key_transform.
5. Render configs: su.render_config("/Game/Render/Preview", "{project_dir}/Renders/preview", (960, 540), samples=1)
   and su.render_config("/Game/Render/Final", "{project_dir}/Renders/final", (1920, 1080), samples=8, warmup=(64, 32)).
6. su.save(); su.log a summary (cameras, spinners, cut sections).
Run with `studio ue-python {NAME}.uproject Scripts/build_sequence.py` until it succeeds; run it twice (re-runnable).
Do not render (the next step renders). Do not commit. Report the summary.
