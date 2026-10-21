"""Blender batch helper for studio-assets (one Blender process for many files).

blender -b --factory-startup -P asset_blender.py -- <in.json> <out.json>

in.json: {"mode": "measure" | "thumbs" | "fix", "files": [...], "thumbs": dir or null, "fixes": {file: {...}}}
  measure  per file: dims_m [x, y, z] in glTF axes (y up), tris, origin offset (bbox bottom-centre minus origin,
           in metres; [0, 0, 0] = origin at the bottom centre), meshes
  thumbs   measure + a 256 px thumbnail (transparent background) for files without one in the thumbs dir
  fix      apply {"scale": s, "origin": "bottom-centre"} to each file and re-export it in place (glTF keeps its
           external textures); a generated, logged step, never a hand edit
out.json: {file: {...} or {"error": "..."}}
"""
import json
import math
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
job = json.load(open(args[0]))
out = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path):
    reset()
    bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def bounds(meshes):
    pts = []
    for o in meshes:
        m = o.matrix_world
        pts += [m @ v.co for v in o.data.vertices]
    if not pts:
        return None, None
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def measure(meshes):
    lo, hi = bounds(meshes)
    if lo is None:
        return {"error": "no geometry"}
    d = hi - lo
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
    off = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))  # Blender z-up; origin is (0, 0, 0)
    # report in glTF axes (x, y up, z = -Blender y)
    return {"dims_m": [round(d.x, 4), round(d.z, 4), round(d.y, 4)], "tris": tris, "meshes": len(meshes),
            "origin_offset_m": [round(off.x, 4), round(off.z, 4), round(-off.y, 4)]}


def setup_render(size=256):
    s = bpy.context.scene
    engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    s.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    s.render.resolution_x = s.render.resolution_y = size
    s.render.film_transparent = True
    s.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.6, 0.62, 0.65, 1)
    for rot, e in (((50, 0, 30), 3.0), ((60, 0, 200), 1.2)):
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = e; sun.rotation_euler = [math.radians(a) for a in rot]
        s.collection.objects.link(sun)


def thumb(meshes, path):
    lo, hi = bounds(meshes)
    centre, radius = (lo + hi) / 2, max((hi - lo).length / 2, 1e-4)
    setup_render()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens = 50
    bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
    az, el, dist = math.radians(-35), math.radians(25), radius * 3.4
    cam.location = centre + Vector((dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az),
                                    dist * math.sin(el)))
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = dist * 4
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def fix(path, spec):
    meshes = load(path)
    lo, hi = bounds(meshes)
    s = float(spec.get("scale", 1.0))
    move = Vector((0, 0, 0))
    if spec.get("origin") == "bottom-centre":
        move = -Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    t = Matrix.Scale(s, 4) @ Matrix.Translation(move)
    roots = [o for o in bpy.context.scene.objects if o.parent is None]
    for o in roots:
        o.matrix_world = t @ o.matrix_world
    bpy.context.view_layer.update()
    # bake the scale into the mesh data, so engines see the real size in the mesh AABB, not a node scale
    for o in bpy.context.scene.objects:
        o.select_set(o.type == "MESH" and o.data.users == 1)
    if bpy.context.selected_objects:
        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    fmt = "GLB" if path.lower().endswith(".glb") else "GLTF_SEPARATE"
    bpy.ops.export_scene.gltf(filepath=path, export_format=fmt)
    return measure(load(path))


for f in job["files"]:
    try:
        if job["mode"] == "fix":
            out[f] = fix(f, job["fixes"][f])
            continue
        meshes = load(f)
        m = measure(meshes)
        if job["mode"] == "thumbs" and "error" not in m and job.get("thumbs"):
            p = pathlib.Path(f)
            # thumbs/<source>/<pack>/<file stem>.png, mirroring mirror/<source>/<pack>/...
            parts = p.parts
            i = parts.index("mirror") if "mirror" in parts else len(parts) - 2
            dest = pathlib.Path(job["thumbs"]).joinpath(*parts[i + 1:]).with_suffix(".png")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                thumb(meshes, dest)
            m["thumb"] = str(dest)
        out[f] = m
    except Exception as e:  # noqa: BLE001 - one bad file must not stop the batch
        out[f] = {"error": f"{type(e).__name__}: {e}"}
    if len(out) % 20 == 0:
        json.dump(out, open(args[1], "w"))

json.dump(out, open(args[1], "w"))
