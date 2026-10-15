# Studio project guide (read this first)

You are working in a sandboxed project directory. You can read/write files and run ordinary
commands here (python3, git, ffmpeg with CPU codecs, cmake, g++). **Never write outputs or test results to /tmp**:
it is private to your sandbox and discarded, so nobody can see them; use the project (e.g. `Renders/`, `out/`).
You CANNOT run Unreal Engine,
Blender or GPU tools directly; ask the studio broker with the `studio` command instead.
`studio help` lists the actions. Every job writes its full log to `.studio/logs/` and prints a
filtered summary (errors + script output). Read the full log only when the summary isn't enough.

| Need | Command |
|---|---|
| Run an Unreal Python script (headless, no GPU) | `studio ue-python <X>.uproject Scripts/<script>.py` |
| Render a Level Sequence (GPU) | `studio ue-render <X>.uproject /Game/.../RenderConfig /Game/.../Sequence /Game/.../Map` |
| Compile C++ (editor target) | `studio ue-build <X>.uproject` |
| Package a Linux build | `studio ue-package <X>.uproject` |
| Run a Blender Python script | `studio blender Scripts/<script>.py [-- args]` |
| PNG/EXR frames to video | `studio encode <frames-dir> <fps> <out.mp4> [--prores]` |

**Use `Scripts/studio_ue.py` first.** It has tested helpers for the fiddly UE 5.8 Python parts: idempotent
levels (`fresh_level`), meshes, cameras, lighting/post-process, simple materials, Level Sequences with transform
keys and orbits, camera cuts, render configs and `save()`. Read its docstring and import it:
```python
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studio_ue as su
```
Only fall back to raw `unreal.*` calls (rules below) for things it doesn't cover. Level scripts must be
**re-runnable**: running them twice must give the same level (no duplicate actors); `su.fresh_level` does that.

To check a render, open a few frames with your file-reading tool (you can see images): look for
black frames, blown-out highlights, wrong framing. Commit working states with git often.

## Unreal Engine 5.8 Python: rules that save hours
- Print progress with `unreal.log("MYTAG ...")`; the `studio` summary shows `LogPython:` lines.
  An uncaught exception shows as `LogPython: Error: Traceback ...` and the job exits non-zero.
- Python property names are snake_case of the C++ name **without the `b` prefix**:
  `bEnableVolumetricFog` -> `enable_volumetric_fog`. If unsure, check first:
  `unreal.get_default_object(unreal.ExponentialHeightFogComponent).get_editor_property("x")` raises if missing.
- Struct properties (e.g. `settings`, `filmback`, `focus_settings`) are copies: get, modify, set back.
- Levels: `les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)`.
  `les.new_level("/Game/Path/Map")` FAILS if the asset exists; then `les.load_level(path)` and destroy
  its actors instead. Always `les.save_current_level()` at the end and check it returned True.
- Actors: `eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)`;
  `eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x,y,z), unreal.Rotator(roll, pitch, yaw))`.
  Note Rotator argument order is (roll, pitch, yaw). `actor.set_actor_label("Name")`.
  Mesh: `actor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))`
  (also Sphere, Cylinder, Cone, Plane; Cube/Sphere are 100 cm). Animated actors need
  `component.set_mobility(unreal.ComponentMobility.MOVABLE)`.
- Look-at rotation: `unreal.MathLibrary.find_look_at_rotation(from_vec, to_vec)`.
- Image panels (billboards, signs, screens): always `su.wall_panel(centre, normal, width_cm, height_cm, material)`;
  position them with `su.face_point(actor, "-y", offset_cm, height_frac)`. Don't hand-craft Plane rotations: the
  basic Plane is 100 cm and its normal/texture orientation are easy to get wrong (sideways or mirrored text).
- Assets: `tools = unreal.AssetToolsHelpers.get_asset_tools()`;
  `tools.create_asset(name, "/Game/Dir", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())`.
  Delete first if it exists (`unreal.EditorAssetLibrary.does_asset_exist/delete_asset`). Save with
  `unreal.EditorAssetLibrary.save_loaded_asset(asset)`.
- Materials: `unreal.MaterialEditingLibrary` (`create_material_expression`, `connect_material_expressions`,
  `connect_material_property(expr, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)`, `recompile_material`).

## Level Sequences
```python
seq.set_display_rate(unreal.FrameRate(30, 1)); seq.set_playback_start(0); seq.set_playback_end(150)
binding = seq.add_possessable(actor)
track = binding.add_track(unreal.MovieScene3DTransformTrack)
section = track.add_section(); section.set_range(0, 150)
ch = section.get_channels_by_type(unreal.MovieSceneScriptingDoubleChannel)
# 9 channels: loc x,y,z, rot roll,pitch,yaw, scale x,y,z. Times are in display-rate frames.
ch[0].add_key(unreal.FrameNumber(0), 100.0)
for c, v in zip(ch, [x, y, z, 0, 0, 0, 1, 1, 1]): c.set_default(v)   # unkeyed channels otherwise default to 0 (scale 0 = invisible!)
cut_track = seq.add_track(unreal.MovieSceneCameraCutTrack)
cut = cut_track.add_section(); cut.set_range(0, 150)
cut.set_camera_binding_id(seq.get_binding_id(camera_binding))
```
- **Never animate camera properties (e.g. focal length) via `MovieSceneFloatTrack` +
  `set_property_name_and_path("CurrentFocalLength", "CameraComponent.CurrentFocalLength")`**:
  it corrupts memory and crashes the render in `APlayerCameraManager::UpdateViewTarget`.
  Set a fixed `cine_camera_component.set_editor_property("current_focal_length", 28.0)` instead.

## Rendering (Movie Render Queue)
Create the render config with Python, writing output **inside the project** using `{project_dir}`:
```python
cfg = tools.create_asset("RenderPreview", "/Game/Render", unreal.MoviePipelinePrimaryConfig,
                         unreal.MoviePipelinePrimaryConfigFactory())
out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.set_editor_property("output_directory", unreal.DirectoryPath("{project_dir}/Renders/preview"))
out.set_editor_property("output_resolution", unreal.IntPoint(960, 540))
out.set_editor_property("file_name_format", "{sequence_name}.{frame_number}")
cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.set_editor_property("temporal_sample_count", 1)  # 8 for finals (motion blur); preview = 1
aa.set_editor_property("engine_warm_up_count", 32)
unreal.EditorAssetLibrary.save_loaded_asset(cfg)
```
Then `studio ue-render X.uproject /Game/Render/RenderPreview /Game/.../Seq /Game/.../Map`.
- Exposure: use a PostProcessVolume (`unbound=True`) with `auto_exposure_method = AEM_MANUAL` and
  tune `auto_exposure_bias` by looking at preview frames (night/neon scenes: ~6-8).
- Preview at 960x540 with 1 sample first; render finals only when the preview looks right.
- The project config already enables SM6 + hardware ray tracing + skin cache; don't remove
  `r.SkinCache.CompileShaders=True` (ray tracing crashes without it).

## C++ gameplay
Source lives in `Source/<Module>/`. Use `UCLASS()`, `GENERATED_BODY()`, `UPROPERTY(EditAnywhere, ...)`,
include `"<Name>.generated.h"` last in headers. Build with `studio ue-build X.uproject`; read the
first `error:` lines in the summary. The first build takes ~1.5 min.
Rules that otherwise crash the editor at module load or exit (the build still succeeds!):
- Never call NewObject<...>() in a constructor (asserts when the class default object is built). In constructors use
  CreateDefaultSubobject; create runtime objects (input actions, mapping contexts, modifiers) in BeginPlay or a lazy
  EnsureX() helper.
- Clear timers in EndPlay (world exists), never in BeginDestroy (also runs on the CDO, without a world).
- Constructors must not use GetWorld(), LoadObject on maps, or other actors; use ConstructorHelpers::FObjectFinder
  for assets, or load at BeginPlay.
- After a C++ change, also run any `studio ue-python` script once: a crash at load shows up there, not in the build.
- Actors (incl. GameModes) only Tick with `PrimaryActorTick.bCanEverTick = true;` in the constructor.
- Overlaps fire only if BOTH components have SetGenerateOverlapEvents(true). In an OnComponentBeginOverlap handler,
  `OverlappedComponent` is yours and `OtherComp` belongs to the other actor.
- Enhanced Input: Config/DefaultInput.ini must set DefaultPlayerInputClass/DefaultInputComponentClass (the template
  does); use Cast<UEnhancedInputComponent> + error log, never CastChecked.
- Assets loaded only by string path (LoadObject) are not cooked: list their folders under
  +DirectoriesToAlwaysCook in Config/DefaultGame.ini.
- Games: give every playable an `-autopilot` mode that plays itself and logs `GAME_` markers plus a 1 s position
  line; `studio ue-play` / `studio run-packaged` then test it end to end. The full log is .studio/logs/*-ue-play.log.
  Packages are Shipping builds, which compile UE_LOG out: emit markers with GAME_EVENT(TEXT("GAME_..."), ...) from
  Source/<Module>/GameEvent.h (also prints to stdout in Shipping).

## Blender (headless, Python)
`studio blender Scripts/make_x.py -- --out assets/x.glb`: inside the script, read args after `--`
(`sys.argv[sys.argv.index("--") + 1:]`), start from an empty scene
(`bpy.ops.wm.read_factory_settings(use_empty=True)`), build with `bpy.ops.mesh.primitive_*` or
`bmesh`, assign materials (Principled BSDF `Base Color`), export with
`bpy.ops.export_scene.gltf(filepath=..., export_format="GLB")`. Blender units: 1 = 1 m.

## Audio (procedural, Python)
Use `Scripts/studio_audio.py` (numpy, 48 kHz): chords/progressions, pads, bass, plucks, kick/snare/hat,
riser/impact/whoosh for transitions, reverb, and a `Timeline` that places clips in seconds and writes a stereo
WAV with peak normalisation and fades. Its docstring has a complete example. Time music to the shot list
(`sa.bars()`, `sa.beat_times()`): cuts on bar lines, impacts on reveals. Keep peaks below -1 dBFS. Mux to video
with ffmpeg: `ffmpeg -i video.mp4 -i audio/score.wav -c:v copy -c:a aac -b:a 192k -shortest out.mp4`.
