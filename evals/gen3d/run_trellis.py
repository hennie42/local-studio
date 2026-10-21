"""TRELLIS.2 image-to-3D for the bake-off (run with venv-trellis, ATTN_BACKEND=xformers, from the TRELLIS.2 checkout).

python run_trellis.py <weights dir> <out dir> <pipeline type: 512|1024|1024_cascade> <image.png>...

Writes <out dir>/<image stem>.glb (textured, decimated to $DECIMATE faces (200k), 2048 px textures) and prints one JSON line per
image: seconds for generation and GLB export, peak allocated VRAM. Uses a local copy of pipeline.json with the
background remover switched from briaai/RMBG-2.0 (gated, CC BY-NC) to ZhengPeng7/BiRefNet (MIT); the inputs have
alpha, so it is never called. DINOv3 (facebook/dinov3-vitl16-pretrain-lvd1689m) is gated: accept its licence on
Hugging Face and log in (hf auth login) first."""
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())  # run from the TRELLIS.2 checkout
os.environ.setdefault("ATTN_BACKEND", "xformers")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import o_voxel  # noqa: E402
from trellis2.pipelines import Trellis2ImageTo3DPipeline  # noqa: E402

weights, out_dir, ptype, images = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
PRE_SIMPLIFY = int(os.environ.get("PRE_SIMPLIFY", 1_000_000))
DECIMATE = int(os.environ.get("DECIMATE", 200_000))  # face budget, applied by CuMesh before texture baking
REMESH = os.environ.get("REMESH", "1") == "1"  # dual-contouring remesh in the GLB export; 0 if it OOMs
cfg = json.load(open(os.path.join(weights, "pipeline.json")))
cfg["args"]["rembg_model"]["args"]["model_name"] = "ZhengPeng7/BiRefNet"
json.dump(cfg, open(os.path.join(weights, "pipeline.local.json"), "w"), indent=1)

t0 = time.time()
pipe = Trellis2ImageTo3DPipeline.from_pretrained(weights, config_file="pipeline.local.json")
pipe.cuda()
print(json.dumps({"load_s": round(time.time() - t0, 1)}), flush=True)
os.makedirs(out_dir, exist_ok=True)
for path in images:
    name = os.path.splitext(os.path.basename(path))[0]
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    mesh = pipe.run(Image.open(path), pipeline_type=ptype, seed=0)[0]
    faces_raw = int(mesh.faces.shape[0])
    mesh.simplify(PRE_SIMPLIFY)  # upstream uses 16.7M (nvdiffrast's limit); CuMesh's export OOMs above ~1M on 16 GB
    t_gen = time.time() - t0
    pipe.cpu(); torch.cuda.empty_cache()  # GLB export (CuMesh simplify) OOMs on 16 GB with the models resident
    t0 = time.time()
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs, coords=mesh.coords,
        attr_layout=mesh.layout, voxel_size=mesh.voxel_size, aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=DECIMATE, texture_size=2048, remesh=REMESH, remesh_band=1, remesh_project=0, verbose=False)
    glb.export(os.path.join(out_dir, f"{name}.glb"))
    print(json.dumps({"image": name, "pipeline": ptype, "gen_s": round(t_gen, 1),
                      "export_s": round(time.time() - t0, 1), "remesh": REMESH, "decimate": DECIMATE, "faces_raw": faces_raw,
                      "peak_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2)}), flush=True)
    del mesh, glb
    torch.cuda.empty_cache()
    pipe.cuda()
