"""Game-ready cleanup of a generated mesh (Blender, headless).

blender -b -P cleanup.py -- <in.glb|.obj> <out.glb> [max_tris=10000] [up=+y]

up is the generator's up axis in glTF coordinates (TripoSR: +z, TRELLIS.2: +y); the output is always glTF +y up.

Joins all meshes, merges near-duplicate vertices, drops floater specks (islands < 2 % of the object's size), recalculates
normals outwards, decimates to max_tris (prefer the generator's own decimation: Blender's collapse shatters
thin non-manifold parts of TRELLIS.2 meshes), puts the origin at the bottom centre and exports a GLB with materials kept."""
import sys

import bmesh
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, out = args[:2]
max_tris = int(args[2]) if len(args) > 2 else 10000
up = args[3] if len(args) > 3 else "+y"
bpy.ops.wm.read_factory_settings(use_empty=True)
if src.endswith(".obj"):
    bpy.ops.wm.obj_import(filepath=src)
else:
    bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in bpy.context.scene.objects:
    o.select_set(o in meshes)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
gltf_to_blender = {"x": Vector((1, 0, 0)), "y": Vector((0, 0, 1)), "z": Vector((0, -1, 0))}
up_vec = gltf_to_blender[up[-1]] * (-1 if up[0] == "-" else 1)
obj.data.transform(up_vec.rotation_difference(Vector((0, 0, 1))).to_matrix().to_4x4())

bm = bmesh.new(); bm.from_mesh(obj.data)
diag = (Vector(obj.dimensions)).length
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4 * diag)
bm.faces.ensure_lookup_table()
islands, seen = [], set()
for f in bm.faces:
    if f.index in seen:
        continue
    stack, isl = [f], []
    seen.add(f.index)
    while stack:
        g = stack.pop(); isl.append(g)
        for e in g.edges:
            for h in e.link_faces:
                if h.index not in seen:
                    seen.add(h.index); stack.append(h)
    islands.append(isl)
total = len(bm.faces)


def isl_diag(isl):
    vs = {v for f in isl for v in f.verts}
    lo = Vector((min(v.co.x for v in vs), min(v.co.y for v in vs), min(v.co.z for v in vs)))
    hi = Vector((max(v.co.x for v in vs), max(v.co.y for v in vs), max(v.co.z for v in vs)))
    return (hi - lo).length


# floaters = specks (< 2 % of the object's size); counting faces instead deletes real thin parts (wires, handles)
drop = [f for isl in islands if isl_diag(isl) < 0.02 * diag for f in isl]
bmesh.ops.delete(bm, geom=drop, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(obj.data); bm.free()

tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
if tris > max_tris:
    mod = obj.modifiers.new("dec", "DECIMATE"); mod.ratio = max_tris / tris
    bpy.ops.object.modifier_apply(modifier=mod.name)

bpy.context.view_layer.update()
pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
obj.data.transform(__import__("mathutils").Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))
obj.location = (0, 0, 0)
bpy.ops.export_scene.gltf(filepath=out, use_selection=False, export_format="GLB")
print(f"CLEANUP islands={len(islands)} dropped_faces={len(drop)} tris_in={tris} "
      f"tris_out={sum(len(p.vertices) - 2 for p in obj.data.polygons)}")
