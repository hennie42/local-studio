"""UE Python: Level Sequence with an orbiting camera and a camera cut track."""
import math
import _ue

AREA = "ue"
TITLE = "UE Python: orbit-camera Level Sequence with camera cut"
KIND = "agent"
TIMEOUT = 1800

PROMPT = """This is an Unreal Engine 5.8 project (Studio.uproject). Read AGENTS.md first.
Write Scripts/build_orbit.py (Unreal Python) that creates or rebuilds and saves:
1. Level /Game/Test/OrbitMap containing a StaticMeshActor labelled Target using /Engine/BasicShapes/Cube
   at the origin, a DirectionalLight, and a CineCameraActor labelled OrbitCam.
2. Level Sequence /Game/Test/Orbit at 30 fps covering frames 0-120 (4 seconds), in which OrbitCam makes
   exactly one full 360-degree orbit around the origin at radius 800 cm and height z = 300, always
   looking at the Target (key the camera's location AND rotation at least every 15 frames).
   Add a camera cut track that uses OrbitCam for the whole range.
Run it with `studio ue-python Studio.uproject Scripts/build_orbit.py` and fix errors until it succeeds."""

INSPECT = """
seq = unreal.load_asset("/Game/Test/Orbit")
if seq is None or not unreal.EditorAssetLibrary.does_asset_exist("/Game/Test/OrbitMap"):
    emit({"error": "sequence or map missing"})
else:
    r = seq.get_display_rate()
    out = {"fps": r.numerator / r.denominator, "start": seq.get_playback_start(), "end": seq.get_playback_end(), "cam": None, "cut": None}
    for b in seq.get_bindings():
        if b.get_display_name() != "OrbitCam":
            continue
        for tr in b.find_tracks_by_exact_type(unreal.MovieScene3DTransformTrack):
            for sec in tr.get_sections():
                ch = sec.get_channels_by_type(unreal.MovieSceneScriptingDoubleChannel)
                keys = []
                for i in (0, 1, 2, 5):  # x, y, z, yaw
                    keys.append([(k.get_time().frame_number.value, k.get_value()) for k in ch[i].get_keys()])
                out["cam"] = keys
    for tr in seq.find_tracks_by_type(unreal.MovieSceneCameraCutTrack):
        for sec in tr.get_sections():
            proxy = seq.resolve_binding_id(sec.get_camera_binding_id())
            out["cut"] = {"start": sec.get_start_frame(), "end": sec.get_end_frame(),
                          "camera": proxy.get_display_name() if proxy and proxy.is_valid() else None}
    emit(out)
"""


def setup(ws):
    _ue.setup_project(ws, "Studio")


def check(info):
    if "error" in info:
        return 0.0, [info["error"]]
    notes, pts, total = [], 0.0, 5
    if abs(info["fps"] - 30) < 0.01 and info["start"] == 0 and info["end"] == 120:
        pts += 1
    else:
        notes.append(f"range/fps {info['fps']} {info['start']}-{info['end']}")
    cut = info.get("cut")
    if cut and cut["camera"] == "OrbitCam" and cut["start"] <= 0 and cut["end"] >= 120:
        pts += 1
    else:
        notes.append(f"camera cut {cut}")
    cam = info.get("cam")
    if not cam:
        return pts / total, notes + ["no OrbitCam transform track"]
    xs, ys, zs, yaws = (dict(k) for k in cam)
    frames = sorted(set(xs) & set(ys))
    gaps = [b - a for a, b in zip(frames, frames[1:])]
    if len(frames) >= 9 and frames[0] <= 0 and frames[-1] >= 120 and max(gaps, default=999) <= 15:
        pts += 1
    else:
        notes.append(f"{len(frames)} location keys, max gap {max(gaps, default=None)}")
    radii = [math.hypot(xs[f], ys[f]) for f in frames]
    heights = [zs.get(f, zs.get(min(zs, key=lambda k: abs(k - f)), 0)) for f in frames] if zs else [0]
    angles = [math.degrees(math.atan2(ys[f], xs[f])) for f in frames]
    unwrapped = [angles[0]]
    for a in angles[1:]:
        d = (a - unwrapped[-1] + 180) % 360 - 180
        unwrapped.append(unwrapped[-1] + d)
    sweep = abs(unwrapped[-1] - unwrapped[0])
    if all(abs(r - 800) < 25 for r in radii) and all(abs(h - 300) < 25 for h in heights) and 340 <= sweep <= 380:
        pts += 1
    else:
        notes.append(f"orbit radius {min(radii):.0f}-{max(radii):.0f}, sweep {sweep:.0f} deg")
    look_ok = 0
    yaw_frames = sorted(yaws)
    for f in frames:
        if not yaw_frames:
            break
        nearest = min(yaw_frames, key=lambda k: abs(k - f))
        if abs(nearest - f) > 1:
            continue
        want = math.degrees(math.atan2(-ys[f], -xs[f]))
        d = (yaws[nearest] - want + 180) % 360 - 180
        look_ok += abs(d) < 10
    if look_ok >= len(frames) - 1:
        pts += 1
    else:
        notes.append(f"look-at yaw ok at {look_ok}/{len(frames)} keys")
    return pts / total, notes


def grade(ws):
    up = ws / "Studio.uproject"
    script = ws / "Scripts/build_orbit.py"
    if not script.exists():
        return {"score": 0.0, "passed": False, "notes": "no Scripts/build_orbit.py"}
    _ue.inspect(ws, up, f"exec(open({str(script)!r}).read(), {{'__name__': '__main__'}})\nemit({{'ran': True}})\n")
    score, notes = check(_ue.inspect(ws, up, INSPECT))
    return {"score": round(score, 3), "passed": score > 0.99, "notes": "; ".join(notes) or "all checks pass"}
