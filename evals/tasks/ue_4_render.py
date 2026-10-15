"""UE: create a render config, render a sequence on the GPU via the broker, encode to mp4."""
import json
import shutil
import subprocess
import _ue
import _media

AREA = "ue"
TITLE = "UE: render config + GPU render via broker + encode mp4"
KIND = "agent"
TIMEOUT = 2400
# The scene the worker renders is built at setup time from basic shapes (no project content ships with the repo).
BUILD_DEMO = r"""
import sys, os
sys.path.insert(0, os.path.join(unreal.Paths.project_dir(), "Scripts"))
import studio_ue as su
su.fresh_level("/Game/Demo/DemoMap")
su.mesh_actor("Plane", (0, 0, 0), scale=(40, 40, 1), label="Floor",
              material=su.color_material("/Game/Demo/M_Floor", (0.03, 0.03, 0.04), roughness=0.15).get_path_name())
colours = [(1, 0.1, 0.6), (0.1, 0.8, 1), (1, 0.6, 0.1), (0.5, 0.2, 1), (0.2, 1, 0.4), (1, 0.2, 0.2)]
for i, c in enumerate(colours):
    m = su.color_material(f"/Game/Demo/M_Glow_{i}", c, emissive=12.0)
    su.mesh_actor("Cube", (300 * (i - 2.5), 0, 60 + 40 * (i % 2)), scale=(0.8, 0.8, 1.2 + 0.4 * (i % 3)),
                  label=f"Glow_{i}", material=m.get_path_name(), movable=True)
su.lighting(sun_pitch=-30, sun_intensity=1.5, sky_intensity=0.3)
su.post_process(exposure_bias=1.0, bloom=1.2)
cam = su.camera("DemoCam", (0, -1400, 400), look_at=(0, 0, 80), focal=30)
seq = su.sequence("/Game/Demo/DemoSeq", seconds=5, fps=30)
b = su.bind(seq, cam)
su.key_transform(b, su.orbit_keys((0, 0, 80), 1400, 400, 150, turns=0.25, start_angle=-90), look_at=(0, 0, 80), frames=150)
su.camera_cut(seq, b, frames=150)
su.save()
emit({"built": True})
"""

PROMPT = """This is an Unreal Engine 5.8 project (Studio.uproject) with a finished scene: map
/Game/Demo/DemoMap and Level Sequence /Game/Demo/DemoSeq (150 frames at 30 fps). Read AGENTS.md first.
1. Write Scripts/make_render_config.py that creates a Movie Render Queue config asset
   /Game/Render/Preview: 960x540, PNG frames, 1 temporal sample, output directory
   {project_dir}/Renders/preview. Run it with `studio ue-python`.
2. Render the sequence with `studio ue-render` using that config.
3. Encode the frames to out/preview.mp4 at 30 fps with `studio encode`.
4. Look at two of the rendered frames and report in one sentence whether they look correct
   (not black, not blown out)."""


def setup(ws):
    up = _ue.setup_project(ws, "Studio")
    res = _ue.inspect(ws, up, BUILD_DEMO, timeout=900)   # hidden: runs outside the worker's sandbox
    if not res.get("built"):
        raise RuntimeError(f"demo scene build failed: {res}")


def grade(ws):
    mp4 = ws / "out/preview.mp4"
    frames = sorted((ws / "Renders/preview").glob("*.png")) if (ws / "Renders/preview").is_dir() else []
    notes, pts = [], 0.0
    if (ws / "Content/Render/Preview.uasset").exists():
        pts += 0.2
    else:
        notes.append("no /Game/Render/Preview asset")
    if len(frames) >= 150:
        pts += 0.3
    else:
        notes.append(f"{len(frames)} frames in Renders/preview")
    if mp4.exists():
        info = _media.probe(mp4)
        v = info.get("video") or {}
        ok_dims = (v.get("width"), v.get("height")) == (960, 540)
        ok_dur = abs(info.get("duration", 0) - 5.0) < 0.25
        pts += 0.2 * ok_dims + 0.2 * ok_dur
        if not ok_dims or not ok_dur:
            notes.append(f"mp4 {v.get('width')}x{v.get('height')} {info.get('duration')}s")
        lum = _media.mean_luma_at(mp4, 2.5)
        if lum is not None and 8 < lum < 200:
            pts += 0.1
        else:
            notes.append(f"mid-frame luma {lum}")
    else:
        notes.append("no out/preview.mp4")
    return {"score": round(pts, 3), "passed": pts > 0.99, "notes": "; ".join(notes) or "all checks pass"}
