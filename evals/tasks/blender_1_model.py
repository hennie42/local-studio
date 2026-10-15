"""Blender: procedural low-poly asset to spec, exported as glTF via the broker."""
import json
import subprocess

AREA = "blender_media"
TITLE = "Blender bpy: low-poly tree to spec, export GLB"
KIND = "agent"
TIMEOUT = 1500

PROMPT = """Read AGENTS.md. Write Scripts/make_tree.py, a Blender Python script that builds a stylized
low-poly tree and exports it to the path given after `--out` (glTF binary). Spec:
- Trunk: a cylinder with 8 sides, radius 0.2 m, height 1.8 m, base at z = 0, object named "Trunk",
  with a material named "Bark" whose base colour is brown (e.g. 0.35, 0.2, 0.08).
- Foliage: 3 cones stacked on top of the trunk, each smaller than the one below (bottom cone radius
  1.4 m), objects named "Foliage_0".."Foliage_2", sharing a material named "Leaves" with a green base colour.
- Total tree height between 4.5 and 5.5 m; whole model under 1500 triangles; centred on x = y = 0.
Run it with `studio blender Scripts/make_tree.py -- --out assets/tree.glb` and fix errors until
assets/tree.glb exists."""

INSPECT = r'''
import bpy, json, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=sys.argv[sys.argv.index("--") + 1])
dg = bpy.context.evaluated_depsgraph_get()
objs, tris, lo, hi, mats = [], 0, [1e9] * 3, [-1e9] * 3, {}
for o in bpy.context.scene.objects:
    if o.type != "MESH":
        continue
    m = o.evaluated_get(dg).to_mesh()
    m.calc_loop_triangles()
    tris += len(m.loop_triangles)
    for v in m.vertices:
        w = o.matrix_world @ v.co
        for k in range(3):
            lo[k] = min(lo[k], w[k]); hi[k] = max(hi[k], w[k])
    objs.append(o.name)
    for slot in o.material_slots:
        if slot.material and slot.material.use_nodes:
            bsdf = next((n for n in slot.material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                mats[slot.material.name] = list(bsdf.inputs["Base Color"].default_value)[:3]
print("GRADER_JSON " + json.dumps({"objects": objs, "tris": tris, "lo": lo, "hi": hi, "mats": mats}))
'''


def setup(ws):
    import shutil, pathlib
    shutil.copy2(pathlib.Path(__file__).resolve().parents[2] / "template/AGENTS.md", ws / "AGENTS.md")
    (ws / "CLAUDE.md").write_text("@AGENTS.md\n")
    (ws / "Scripts").mkdir()
    (ws / "assets").mkdir()


def grade(ws):
    glb = ws / "assets/tree.glb"
    if not glb.exists():
        return {"score": 0.0, "passed": False, "notes": "no assets/tree.glb"}
    script = ws / ".studio/grader_blender.py"
    script.parent.mkdir(exist_ok=True)
    script.write_text(INSPECT)
    log = ws / ".studio/grader_blender.log"
    with open(log, "w") as f:
        subprocess.run(["blender", "-b", "--factory-startup", "--python", str(script), "--", str(glb)],
                       stdout=f, stderr=subprocess.STDOUT, timeout=300)
    line = next((l for l in log.read_text().splitlines() if l.startswith("GRADER_JSON ")), None)
    if not line:
        return {"score": 0.05, "passed": False, "notes": "glb could not be imported"}
    d = json.loads(line[12:])
    checks = {}
    names = set(d["objects"])
    checks["names"] = "Trunk" in names and {"Foliage_0", "Foliage_1", "Foliage_2"} <= names
    height = d["hi"][2] - d["lo"][2]
    checks["height"] = 4.5 <= height <= 5.5
    checks["base_at_zero"] = abs(d["lo"][2]) < 0.05
    checks["centred"] = all(abs((d["lo"][k] + d["hi"][k]) / 2) < 0.1 for k in (0, 1))
    checks["width"] = 2.5 <= d["hi"][0] - d["lo"][0] <= 3.0  # bottom cone radius 1.4 m
    checks["tris"] = 0 < d["tris"] < 1500
    bark, leaves = d["mats"].get("Bark"), d["mats"].get("Leaves")
    checks["bark_brown"] = bool(bark) and bark[0] > bark[1] > bark[2]
    checks["leaves_green"] = bool(leaves) and leaves[1] > leaves[0] and leaves[1] > leaves[2]
    score = sum(checks.values()) / len(checks)
    failed = [k for k, v in checks.items() if not v]
    return {"score": round(score, 3), "passed": not failed,
            "notes": f"h={height:.2f} tris={d['tris']} objs={len(names)}" + (f"; failed: {', '.join(failed)}" if failed else "")}
