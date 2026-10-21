"""studio_ue: tested helpers for Unreal Engine 5.8 Python scripts in studio projects.

Use from any project script run with `studio ue-python X.uproject Scripts/<script>.py`:

    import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import studio_ue as su
    su.fresh_level("/Game/Maps/Main")                 # idempotent: create, or load and clear
    pos, n = su.face_point(tower, "-y", offset_cm=50, height_frac=0.7)
    su.wall_panel(pos, n, 3000, 6000, material="/Game/M_Ad.M_Ad", label="Ad")   # upright, faces n
    cube = su.mesh_actor("Cube", (0, 0, 50), label="Hero", scale=(1, 1, 1), movable=True)
    cam = su.camera("ShotCam", (-800, 0, 300), look_at=(0, 0, 50), focal=35)
    seq = su.sequence("/Game/Cinematics/Shot01", seconds=5, fps=30)
    b = su.bind(seq, cam)
    su.key_transform(b, [(0, (-800, 0, 300)), (150, (0, -800, 300))], look_at=(0, 0, 50), frames=150)
    su.camera_cut(seq, b, frames=150)
    su.render_config("/Game/Render/Preview", "{project_dir}/Renders/preview", (960, 540), samples=1)
    su.save()                                         # saves the level and all dirty assets
Every function logs "STUDIO_UE ..." lines that show up in the `studio` summary.
"""
import math

import unreal

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

BASIC = {"Cube": "/Engine/BasicShapes/Cube", "Sphere": "/Engine/BasicShapes/Sphere",
         "Cylinder": "/Engine/BasicShapes/Cylinder", "Cone": "/Engine/BasicShapes/Cone", "Plane": "/Engine/BasicShapes/Plane"}


def log(msg):
    unreal.log("STUDIO_UE " + msg)


def _split(path):
    d, name = path.rsplit("/", 1)
    return d, name


def fresh_asset(path, cls, factory):
    """Create the asset at path, deleting any existing one first (re-runnable scripts)."""
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    d, name = _split(path)
    return tools.create_asset(name, d, cls, factory)


# ------------------------------------------------------------------ importing files
def import_file(file_path, dest_dir, name=None):
    """Import a texture (png/jpg/exr), model (glb/gltf/fbx) or sound (wav) into dest_dir (/Game/...).
    Re-importing replaces the existing asset. Returns the imported asset object paths.
    Models import as ONE combined mesh per file (static, or skeletal per skeleton): by default Interchange makes
    one mesh per glTF node (a Kenney ship = 16 meshes, a KayKit character = 7-9 skeletal parts)."""
    if str(file_path).lower().endswith((".glb", ".gltf", ".fbx")):
        pipeline = unreal.InterchangeGenericAssetsPipeline()
        mp = pipeline.mesh_pipeline
        mp.set_editor_property("combine_static_meshes_behavior", unreal.InterchangeCombineStaticMeshesBehavior.ALL)
        mp.set_editor_property("combine_skeletal_meshes_behavior",
                               unreal.InterchangeCombineSkeletalMeshesBehavior.BY_SKELETON)
        params = unreal.ImportAssetParameters()
        params.is_automated = True
        params.replace_existing = True
        if name:
            params.destination_name = name
        params.override_pipelines.append(unreal.SoftObjectPath(pipeline.get_path_name()))  # AssetImportTask can't
        source = unreal.InterchangeManager.create_source_data(str(file_path))
        result = unreal.InterchangeManager.get_interchange_manager_scripted().import_asset(dest_dir, source, params)
        if not result:
            raise RuntimeError(f"import failed: {file_path}")
        for p in find_assets(dest_dir, "SkeletalMesh"):      # renders can't add material usages at run time
            for slot in unreal.load_asset(p).get_editor_property("materials"):
                mi = slot.get_editor_property("material_interface")
                m = mi.get_base_material() if mi else None
                if m and not m.get_editor_property("used_with_skeletal_mesh"):
                    m.set_editor_property("used_with_skeletal_mesh", True)
                    mel.recompile_material(m)
        eal.save_directory(dest_dir, only_if_is_dirty=False, recursive=True)   # import_asset doesn't save
        paths = [str(p).split("'")[1] if "'" in str(p) else str(p) for p in result]
        log(f"imported {file_path} -> {', '.join(paths)}")
        return paths
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(file_path))
    task.set_editor_property("destination_path", dest_dir)
    if name:
        task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    tools.import_asset_tasks([task])
    paths = list(task.get_editor_property("imported_object_paths"))
    if not paths:
        raise RuntimeError(f"import failed: {file_path}")
    log(f"imported {file_path} -> {', '.join(paths)}")
    return paths


def import_dir(dir_path, dest_dir, patterns=("*.png", "*.jpg", "*.glb")):
    """Import every matching file in a project directory; returns {file name: [object paths]}."""
    import glob, os
    out = {}
    for pat in patterns:
        for f in sorted(glob.glob(os.path.join(dir_path, pat))):
            out[os.path.basename(f)] = import_file(f, dest_dir)
    return out


def find_assets(dir_path, cls_name=None):
    """Asset paths under a /Game directory, optionally filtered by class name (e.g. 'StaticMesh', 'Texture2D')."""
    paths = eal.list_assets(dir_path, recursive=True, include_folder=False)
    if cls_name:
        paths = [p for p in paths if eal.find_asset_data(p).asset_class_path.asset_name == cls_name]
    return sorted(paths)


# ------------------------------------------------------------------ levels and actors
def fresh_level(path):
    """Idempotent: create the level, or load it and destroy all its actors. Scripts that call this can run twice."""
    if eal.does_asset_exist(path):
        if not levels.load_level(path):
            raise RuntimeError("could not load " + path)
        for a in actors.get_all_level_actors():
            actors.destroy_actor(a)
    elif not levels.new_level(path):
        raise RuntimeError("could not create " + path)
    log("level " + path)


def spawn(cls, loc=(0, 0, 0), rot=(0, 0, 0), label=None):
    """rot is (roll, pitch, yaw) in degrees: unreal.Rotator's argument order."""
    a = actors.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    if label:
        a.set_actor_label(label)
    return a


def mesh_actor(mesh, loc=(0, 0, 0), rot=(0, 0, 0), label=None, scale=(1, 1, 1), material=None, movable=False):
    """mesh: a BASIC name ('Cube', 'Sphere', ...) or an asset path. Basic Cube/Sphere are 100 cm."""
    a = spawn(unreal.StaticMeshActor, loc, rot, label)
    mc = a.static_mesh_component
    if movable:
        mc.set_mobility(unreal.ComponentMobility.MOVABLE)
    mc.set_static_mesh(unreal.load_asset(BASIC.get(mesh, mesh)))
    a.set_actor_scale3d(unreal.Vector(*scale))
    if material:
        mc.set_material(0, unreal.load_asset(material) if isinstance(material, str) else material)
    return a


def wall_panel(center, normal, width_cm, height_cm, material=None, label=None, movable=False):
    """Upright image panel (billboard, sign, screen) facing `normal` (horizontal vector, e.g. (0, -1, 0)).
    The texture reads upright and unmirrored for a viewer in front of it (verified by render: the Plane's normal is
    its local +Z, and its local Y must point world-down). width/height in cm (the basic Plane is 100 x 100 cm)."""
    n = unreal.Vector(*normal)
    rot = unreal.MathLibrary.make_rot_from_zy(n, unreal.Vector(0, 0, -1))
    a = mesh_actor("Plane", center, label=label, scale=(width_cm / 100.0, height_cm / 100.0, 1), material=material,
                   movable=movable)
    a.set_actor_rotation(rot, False)
    return a


def face_point(actor, direction, offset_cm=0.0, height_frac=0.5):
    """Point on the outside of an actor's world bounding box face pointing in `direction` ('+x','-x','+y','-y'),
    offset_cm in front of it, at height_frac of the actor's height. Returns ((x, y, z), normal)."""
    o, e = actor.get_actor_bounds(False)
    axis, sign = direction[1], 1 if direction[0] == "+" else -1
    x, y = o.x, o.y
    if axis == "x":
        x = o.x + sign * (e.x + offset_cm)
        normal = (sign, 0, 0)
    else:
        y = o.y + sign * (e.y + offset_cm)
        normal = (0, sign, 0)
    z = (o.z - e.z) + 2 * e.z * height_frac
    return (x, y, z), normal


def look_at_rotation(src, dst):
    r = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*src), unreal.Vector(*dst))
    return (r.roll, r.pitch, r.yaw)


def camera(label, loc, look_at=(0, 0, 0), focal=35.0, aperture=5.6, focus_distance=None):
    """CineCameraActor with a 16:9 filmback. Focal length is fixed: never animate it via a property track
    (crashes renders in UE 5.8)."""
    cam = spawn(unreal.CineCameraActor, loc, look_at_rotation(loc, look_at), label)
    cc = cam.get_cine_camera_component()
    fb = cc.get_editor_property("filmback")
    fb.set_editor_property("sensor_width", 36.0)
    fb.set_editor_property("sensor_height", 20.25)
    cc.set_editor_property("filmback", fb)
    fs = cc.get_editor_property("focus_settings")
    fs.set_editor_property("focus_method", unreal.CameraFocusMethod.MANUAL)
    dist = focus_distance or math.dist(loc, look_at)
    fs.set_editor_property("manual_focus_distance", float(dist))
    cc.set_editor_property("focus_settings", fs)
    cc.set_editor_property("current_aperture", float(aperture))
    cc.set_editor_property("current_focal_length", float(focal))
    return cam


def lighting(sun_pitch=-35.0, sun_yaw=40.0, sun_intensity=6.0, sun_color=(255, 240, 220), sky_intensity=1.0,
             fog_density=0.02, volumetric=True, exposure_bias=None, bloom=1.0):
    """Sun + sky atmosphere + sky light + height fog (+ an unbound post-process volume if exposure_bias is set,
    manual exposure: tune exposure_bias by looking at preview frames)."""
    sun = spawn(unreal.DirectionalLight, rot=(0, sun_pitch, sun_yaw), label="Sun")
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    lc.set_editor_property("intensity", sun_intensity)
    lc.set_editor_property("light_color", unreal.Color(r=sun_color[0], g=sun_color[1], b=sun_color[2], a=255))
    lc.set_editor_property("atmosphere_sun_light", True)
    spawn(unreal.SkyAtmosphere, label="SkyAtmosphere")
    sky = spawn(unreal.SkyLight, label="SkyLight")
    sc = sky.get_component_by_class(unreal.SkyLightComponent)
    sc.set_editor_property("real_time_capture", True)
    sc.set_editor_property("intensity", sky_intensity)
    fog = spawn(unreal.ExponentialHeightFog, label="Fog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", fog_density)
    fc.set_editor_property("enable_volumetric_fog", volumetric)
    if exposure_bias is not None:
        post_process(exposure_bias=exposure_bias, bloom=bloom)
    return sun


def post_process(exposure_bias=0.0, bloom=1.0, vignette=0.4, grain=0.0):
    ppv = spawn(unreal.PostProcessVolume, label="PostProcess")
    ppv.set_editor_property("unbound", True)
    s = ppv.get_editor_property("settings")
    for prop, val in [("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                      ("override_auto_exposure_bias", True), ("auto_exposure_bias", float(exposure_bias)),
                      ("override_bloom_intensity", True), ("bloom_intensity", float(bloom)),
                      ("override_vignette_intensity", True), ("vignette_intensity", float(vignette)),
                      ("override_film_grain_intensity", True), ("film_grain_intensity", float(grain)),
                      # manual exposure must ignore the camera's f-stop, else f/8 under a normal sun renders black
                      ("override_auto_exposure_apply_physical_camera_exposure", True),
                      ("auto_exposure_apply_physical_camera_exposure", False)]:
        s.set_editor_property(prop, val)
    ppv.set_editor_property("settings", s)
    return ppv


# ------------------------------------------------------------------ materials
def color_material(path, rgb, roughness=0.5, metallic=0.0, emissive=0.0):
    """Simple opaque material: base colour, roughness, metallic, optional emissive strength (x base colour)."""
    m = fresh_asset(path, unreal.Material, unreal.MaterialFactoryNew())
    base = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, 0)
    base.set_editor_property("constant", unreal.LinearColor(*rgb, 1.0))
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for val, prop, y in ((roughness, unreal.MaterialProperty.MP_ROUGHNESS, 200), (metallic, unreal.MaterialProperty.MP_METALLIC, 300)):
        c = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, y)
        c.set_editor_property("r", float(val))
        mel.connect_material_property(c, "", prop)
    if emissive:
        k = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -600, 100)
        k.set_editor_property("r", float(emissive))
        mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -200, 100)
        mel.connect_material_expressions(base, "", mul, "A")
        mel.connect_material_expressions(k, "", mul, "B")
        mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    m.set_editor_property("used_with_nanite", True)  # else -game/packaged builds show default grey on Nanite meshes
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


def texture_material(path, texture, tiling=1.0, emissive=0.0, tint=(1, 1, 1), base_dark=0.02, roughness=0.3,
                     flicker_hz=0.0, pan=(0.0, 0.0), world_aligned_cm=None):
    """Material driven by a texture: base colour (darkened) + emissive = texture * tint * emissive.
    tiling: UV multiplier; world_aligned_cm: if set, UVs come from world position (X/Z and Y/Z faces) with
    that size in cm per texture repeat, so scaled meshes don't stretch the pattern (good for window grids).
    flicker_hz > 0: emissive pulses (0.75..1.0) at that rate (neon signs); pan: UV scroll speed per second."""
    m = fresh_asset(path, unreal.Material, unreal.MaterialFactoryNew())
    tex = unreal.load_asset(texture) if isinstance(texture, str) else texture
    ts = mel.create_material_expression(m, unreal.MaterialExpressionTextureSample, -900, 0)
    ts.set_editor_property("texture", tex)
    if world_aligned_cm:
        wp = mel.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -1700, 0)
        mask_xz = mel.create_material_expression(m, unreal.MaterialExpressionComponentMask, -1500, -100)
        mask_yz = mel.create_material_expression(m, unreal.MaterialExpressionComponentMask, -1500, 100)
        for msk, chans in ((mask_xz, (True, False, True)), (mask_yz, (False, True, True))):
            for ch, on in zip(("r", "g", "b", "a"), chans + (False,)):
                msk.set_editor_property(ch, on)
            mel.connect_material_expressions(wp, "", msk, "")
        nrm = mel.create_material_expression(m, unreal.MaterialExpressionVertexNormalWS, -1700, 300)
        nx = mel.create_material_expression(m, unreal.MaterialExpressionComponentMask, -1500, 300)
        for ch, on in zip(("r", "g", "b", "a"), (True, False, False, False)):
            nx.set_editor_property(ch, on)
        mel.connect_material_expressions(nrm, "", nx, "")
        absx = mel.create_material_expression(m, unreal.MaterialExpressionAbs, -1350, 300)
        mel.connect_material_expressions(nx, "", absx, "")
        lerp = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -1200, 0)
        mel.connect_material_expressions(mask_xz, "", lerp, "A")   # faces facing Y use X/Z
        mel.connect_material_expressions(mask_yz, "", lerp, "B")   # faces facing X use Y/Z
        mel.connect_material_expressions(absx, "", lerp, "Alpha")
        div = mel.create_material_expression(m, unreal.MaterialExpressionDivide, -1050, 0)
        k = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -1200, 200)
        k.set_editor_property("r", float(world_aligned_cm))
        mel.connect_material_expressions(lerp, "", div, "A")
        mel.connect_material_expressions(k, "", div, "B")
        uv_out = div
    else:
        tc = mel.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -1300, 0)
        tc.set_editor_property("u_tiling", float(tiling))
        tc.set_editor_property("v_tiling", float(tiling))
        uv_out = tc
    if pan != (0.0, 0.0):
        pn = mel.create_material_expression(m, unreal.MaterialExpressionPanner, -1000, 150)
        pn.set_editor_property("speed_x", float(pan[0]))
        pn.set_editor_property("speed_y", float(pan[1]))
        mel.connect_material_expressions(uv_out, "", pn, "Coordinate")
        uv_out = pn
    mel.connect_material_expressions(uv_out, "", ts, "UVs")
    tint_c = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -900, 250)
    tint_c.set_editor_property("constant", unreal.LinearColor(*tint, 1.0))
    col = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -650, 100)
    mel.connect_material_expressions(ts, "RGB", col, "A")
    mel.connect_material_expressions(tint_c, "", col, "B")
    dark = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -450, -100)
    kd = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -650, -150)
    kd.set_editor_property("r", float(base_dark))
    mel.connect_material_expressions(col, "", dark, "A")
    mel.connect_material_expressions(kd, "", dark, "B")
    mel.connect_material_property(dark, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -450, 50)
    rough.set_editor_property("r", float(roughness))
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    if emissive:
        ke = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -650, 300)
        ke.set_editor_property("r", float(emissive))
        em = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -450, 250)
        mel.connect_material_expressions(col, "", em, "A")
        mel.connect_material_expressions(ke, "", em, "B")
        out = em
        if flicker_hz:
            tm = mel.create_material_expression(m, unreal.MaterialExpressionTime, -900, 450)
            sn = mel.create_material_expression(m, unreal.MaterialExpressionSine, -750, 450)
            sn.set_editor_property("period", 1.0 / float(flicker_hz))
            mel.connect_material_expressions(tm, "", sn, "")
            fl = mel.create_material_expression(m, unreal.MaterialExpressionLinearInterpolate, -600, 450)
            fl.set_editor_property("const_a", 0.75)
            fl.set_editor_property("const_b", 1.0)
            sc = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -700, 550)
            half = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -850, 600)
            half.set_editor_property("r", 0.5)
            add = mel.create_material_expression(m, unreal.MaterialExpressionAdd, -650, 600)
            mel.connect_material_expressions(sn, "", sc, "A")
            mel.connect_material_expressions(half, "", sc, "B")
            mel.connect_material_expressions(sc, "", add, "A")
            mel.connect_material_expressions(half, "", add, "B")       # sine -1..1 -> 0..1
            mel.connect_material_expressions(add, "", fl, "Alpha")
            em2 = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 350)
            mel.connect_material_expressions(em, "", em2, "A")
            mel.connect_material_expressions(fl, "", em2, "B")
            out = em2
        mel.connect_material_property(out, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    m.set_editor_property("used_with_nanite", True)  # else -game/packaged builds show default grey on Nanite meshes
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    log(f"texture material {path}")
    return m


# ------------------------------------------------------------------ sequences
def sequence(path, seconds=5.0, fps=30):
    seq = fresh_asset(path, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(int(fps), 1))
    seq.set_playback_start(0)
    seq.set_playback_end(int(round(seconds * fps)))
    log(f"sequence {path} {seconds}s @{fps}")
    return seq


def bind(seq, actor):
    return seq.add_possessable(actor)


def key_transform(binding, keys, look_at=None, frames=None, scale=(1, 1, 1)):
    """keys: [(frame, (x, y, z)) or (frame, (x, y, z), (roll, pitch, yaw))]. With look_at, rotation is computed so
    the actor faces that point at every key. Unkeyed channels get defaults (scale 1, not 0)."""
    track = binding.add_track(unreal.MovieScene3DTransformTrack)
    section = track.add_section()
    last = frames if frames is not None else max(k[0] for k in keys)
    section.set_range(0, int(last))
    ch = section.get_channels_by_type(unreal.MovieSceneScriptingDoubleChannel)
    first = keys[0]
    rot0 = first[2] if len(first) > 2 else (look_at_rotation(first[1], look_at) if look_at else (0, 0, 0))
    for c, v in zip(ch, list(first[1]) + list(rot0) + list(scale)):
        c.set_default(float(v))
    for k in keys:
        f, loc = int(k[0]), k[1]
        rot = k[2] if len(k) > 2 else (look_at_rotation(loc, look_at) if look_at else None)
        for i, v in enumerate(loc):
            ch[i].add_key(unreal.FrameNumber(f), float(v))
        if rot is not None:
            for i, v in enumerate(rot):
                ch[3 + i].add_key(unreal.FrameNumber(f), float(v))
    return section


def orbit_keys(center, radius, height, frames, step=10, start_angle=0.0, turns=1.0):
    """Keys for a circular orbit (use with key_transform(..., look_at=center))."""
    out = []
    for f in range(0, int(frames) + 1, step):
        a = math.radians(start_angle) + 2 * math.pi * turns * f / frames
        out.append((f, (center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), height)))
    if out[-1][0] != frames:
        a = math.radians(start_angle) + 2 * math.pi * turns
        out.append((int(frames), (center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), height)))
    return out


def camera_cut(seq, camera_binding, frames=None, start=0):
    track = seq.add_track(unreal.MovieSceneCameraCutTrack)
    cut = track.add_section()
    cut.set_range(int(start), int(frames if frames is not None else seq.get_playback_end()))
    cut.set_camera_binding_id(seq.get_binding_id(camera_binding))
    return cut


def camera_cuts(seq, shots):
    """Multi-shot edit: shots = [(camera_binding, start_frame, end_frame), ...] in order, contiguous."""
    track = seq.add_track(unreal.MovieSceneCameraCutTrack)
    for binding, start, end in shots:
        cut = track.add_section()
        cut.set_range(int(start), int(end))
        cut.set_camera_binding_id(seq.get_binding_id(binding))
    log(f"camera cuts: {[(int(s), int(e)) for _, s, e in shots]}")
    return track


# ------------------------------------------------------------------ rendering
def render_config(path, output_dir="{project_dir}/Renders/preview", resolution=(960, 540), samples=1, png=True,
                  warmup=(32, 16)):
    """Movie Render Queue config. samples=1 for previews; 8 for finals (real motion blur, clean AA)."""
    cfg = fresh_asset(path, unreal.MoviePipelinePrimaryConfig, unreal.MoviePipelinePrimaryConfigFactory())
    out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    out.set_editor_property("output_directory", unreal.DirectoryPath(output_dir))
    out.set_editor_property("output_resolution", unreal.IntPoint(*resolution))
    out.set_editor_property("file_name_format", "{sequence_name}.{frame_number}")
    out.set_editor_property("zero_pad_frame_numbers", 4)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG if png else unreal.MoviePipelineImageSequenceOutput_EXR)
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.set_editor_property("spatial_sample_count", 1)
    aa.set_editor_property("temporal_sample_count", int(samples))
    if samples > 1:
        aa.set_editor_property("override_anti_aliasing", True)
        aa.set_editor_property("anti_aliasing_method", unreal.AntiAliasingMethod.AAM_NONE)
    aa.set_editor_property("engine_warm_up_count", int(warmup[0]))
    aa.set_editor_property("render_warm_up_count", int(warmup[1]))
    eal.save_loaded_asset(cfg)
    log(f"render config {path} -> {output_dir} {resolution[0]}x{resolution[1]} x{samples}")
    return cfg


def save():
    """Save the current level and every dirty asset. Raises if the level can't be saved."""
    if not levels.save_current_level():
        raise RuntimeError("could not save the current level")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log("saved")
