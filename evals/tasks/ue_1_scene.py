"""UE Python: build a level from a precise spec, run it through the studio broker."""
import math
import _ue

AREA = "ue"
TITLE = "UE Python: build a level from a spec via studio ue-python"
KIND = "agent"
TIMEOUT = 1800

PROMPT = """This is an Unreal Engine 5.8 project (Studio.uproject). Read AGENTS.md first.
Write Scripts/build_scene.py, an Unreal Python script that creates (or rebuilds) the level
/Game/Test/TestMap and saves it, containing exactly:
1. 8 StaticMeshActors using /Engine/BasicShapes/Sphere, labelled Orb_0 ... Orb_7, evenly spaced on a
   circle of radius 500 cm around the origin, at z = 100 (Orb_0 at angle 0, i.e. at x=500, y=0).
2. One PointLight labelled CenterLight at (0, 0, 300) with intensity 5000.
3. One CineCameraActor labelled MainCam at (-1200, 0, 400), rotated so it looks at the origin.
Run it with `studio ue-python Studio.uproject Scripts/build_scene.py` and fix any errors until it
succeeds. The script must be re-runnable (running it twice still gives exactly this content)."""

INSPECT = """
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not unreal.EditorAssetLibrary.does_asset_exist("/Game/Test/TestMap"):
    emit({"error": "map missing"})
else:
    les.load_level("/Game/Test/TestMap")
    out = []
    for a in eas.get_all_level_actors():
        d = {"label": a.get_actor_label(), "class": a.get_class().get_name()}
        loc, rot = a.get_actor_location(), a.get_actor_rotation()
        d["loc"] = [loc.x, loc.y, loc.z]
        d["fwd"] = [v for v in (lambda f: [f.x, f.y, f.z])(a.get_actor_forward_vector())]
        if isinstance(a, unreal.StaticMeshActor):
            m = a.static_mesh_component.static_mesh
            d["mesh"] = m.get_path_name() if m else None
        if isinstance(a, unreal.PointLight):
            d["intensity"] = a.get_component_by_class(unreal.PointLightComponent).intensity
        out.append(d)
    emit({"actors": out})
"""


def setup(ws):
    _ue.setup_project(ws, "Studio")


def check(info):
    if "error" in info:
        return 0.0, [info["error"]]
    acts = info["actors"]
    notes, pts, total = [], 0, 0
    orbs = {a["label"]: a for a in acts if a["label"].startswith("Orb_")}
    total += 1
    if len(orbs) == 8 and all(a["class"] == "StaticMeshActor" for a in orbs.values()):
        pts += 1
    else:
        notes.append(f"{len(orbs)} orbs")
    total += 1
    if all(a.get("mesh", "").startswith("/Engine/BasicShapes/Sphere") for a in orbs.values()) and orbs:
        pts += 1
    else:
        notes.append("orb mesh wrong")
    total += 1
    good_pos = 0
    for i in range(8):
        a = orbs.get(f"Orb_{i}")
        if not a:
            continue
        ang = 2 * math.pi * i / 8
        ex = (500 * math.cos(ang), 500 * math.sin(ang), 100)
        if all(abs(a["loc"][k] - ex[k]) < 5 for k in range(3)):
            good_pos += 1
    pts += good_pos / 8
    if good_pos < 8:
        notes.append(f"orb positions {good_pos}/8")
    lights = [a for a in acts if a["label"] == "CenterLight"]
    total += 1
    if len(lights) == 1 and lights[0]["class"] == "PointLight" and all(abs(lights[0]["loc"][k] - v) < 5 for k, v in enumerate((0, 0, 300))) \
            and abs(lights[0].get("intensity", 0) - 5000) < 1:
        pts += 1
    else:
        notes.append("light wrong")
    cams = [a for a in acts if a["label"] == "MainCam"]
    total += 1
    if len(cams) == 1 and cams[0]["class"] == "CineCameraActor":
        c = cams[0]
        to = [-c["loc"][0], -c["loc"][1], -c["loc"][2]]
        n = sum(v * v for v in to) ** 0.5
        dot = sum(f * t / n for f, t in zip(c["fwd"], to))
        at = all(abs(c["loc"][k] - v) < 5 for k, v in enumerate((-1200, 0, 400)))
        pts += 0.5 * at + 0.5 * (dot > 0.98)
        if not at or dot <= 0.98:
            notes.append(f"camera pos ok={at} look dot={dot:.3f}")
    else:
        notes.append("camera missing")
    extra = [a for a in acts if a["label"].startswith(("Orb_", "CenterLight", "MainCam"))]
    total += 1
    if len(extra) == 10:
        pts += 1
    else:
        notes.append(f"{len(extra)} labelled actors (duplicates?)")
    return pts / total, notes


def grade(ws):
    up = ws / "Studio.uproject"
    script = ws / "Scripts/build_scene.py"
    if not script.exists():
        return {"score": 0.0, "passed": False, "notes": "no Scripts/build_scene.py"}
    # Re-run the agent's script twice (re-runnability), then inspect.
    for _ in range(2):
        _ue.inspect(ws, up, f"exec(open({str(script)!r}).read(), {{'__name__': '__main__'}})\nemit({{'ran': True}})\n")
    info = _ue.inspect(ws, up, INSPECT)
    score, notes = check(info)
    return {"score": round(score, 3), "passed": score > 0.99, "notes": "; ".join(notes) or "all checks pass"}
