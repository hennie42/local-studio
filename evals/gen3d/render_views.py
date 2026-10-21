"""Render a model with Blender (Eevee) for the 3D generation bake-off.

blender -b -P render_views.py -- <model.glb|.gltf> <out.png> input   # one 3/4 view, transparent background, 1024 px
    [azimuth]
blender -b -P render_views.py -- <model.glb|.gltf> <out.png> sheet   # 4 views (front, 3/4, side, back) in a 2x2 sheet
    [align.json]  (from measure.py --save-aligned: shows a generated mesh in its ground truth's orientation)

The model is centred and scaled to fit a unit sphere; +Y forward in glTF terms (Blender's importer turns that into -Y)."""
import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, out, mode = args[:3]
azimuth = float(args[3]) if mode == "input" and len(args) > 3 else -35
align = args[3] if mode == "sheet" and len(args) > 3 else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
if align:
    import json
    from mathutils import Matrix
    y_up_to_z_up = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    m = y_up_to_z_up @ Matrix(json.load(open(align))) @ y_up_to_z_up.inverted()
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.matrix_world = m @ o.matrix_world
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.context.view_layer.update()
pts = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
centre, radius = (lo + hi) / 2, (hi - lo).length / 2
root = bpy.data.objects.new("root", None)
bpy.context.scene.collection.objects.link(root)
for o in bpy.context.scene.objects:
    if o.parent is None and o is not root:
        o.parent = root
root.scale = (1 / radius,) * 3
root.location = -centre / radius

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {
    e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 1024 if mode == "input" else 512
scene.render.film_transparent = mode == "input"
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.57, 0.6, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
for rot, energy in (((50, 0, 30), 3.5), ((60, 0, 200), 1.5)):
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = energy; sun.rotation_euler = [math.radians(a) for a in rot]
    scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 50
scene.collection.objects.link(cam); scene.camera = cam


def shoot(azimuth_deg, elevation_deg, path):
    az, el, dist = math.radians(azimuth_deg), math.radians(elevation_deg), 3.6
    cam.location = (dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el))
    cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


if mode == "input":
    shoot(azimuth, 20, out)
else:
    import os
    tiles = []
    for i, (az, el) in enumerate(((0, 10), (-35, 20), (-90, 10), (180, 10))):
        p = f"{out}.{i}.png"; shoot(az, el, p); tiles.append(bpy.data.images.load(p))
    w = tiles[0].size[0]
    sheet = bpy.data.images.new("sheet", 2 * w, 2 * w)
    px = [0.0] * (4 * w * w * 4)
    for i, t in enumerate(tiles):
        tp, ox, oy = list(t.pixels), (i % 2) * w, (1 - i // 2) * w
        for y in range(w):
            row = tp[y * w * 4:(y + 1) * w * 4]
            s = ((oy + y) * 2 * w + ox) * 4
            px[s:s + w * 4] = row
    sheet.pixels = px
    sheet.filepath_raw = out; sheet.file_format = "PNG"; sheet.save()
    for i in range(4):
        os.remove(f"{out}.{i}.png")
