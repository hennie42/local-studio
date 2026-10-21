#!/usr/bin/env bash
# TRELLIS.2 on this machine: uv venv (Python 3.12), torch cu130 (system nvcc is 13.x), xformers instead of
# flash-attn (no multi-hour compile). Extensions built for the 2060 (7.5) and the 5070 Ti (12.0).
set -euo pipefail
G=${GEN3D:-/home/user/StudioProjects/evals/gen3d}
export PATH=$HOME/.local/bin:/opt/cuda/bin:$PATH UV_CACHE_DIR=$G/.uv-cache CUDA_HOME=/opt/cuda
export TORCH_CUDA_ARCH_LIST="7.5;12.0" MAX_JOBS=${MAX_JOBS:-8}
PY=$G/venv-trellis/bin/python
pip() { uv pip install -p "$PY" "$@"; }
cd "$G"
[ -d venv-trellis ] || uv venv -p 3.12 venv-trellis
pip torch torchvision xformers --index-url https://download.pytorch.org/whl/cu130
pip setuptools wheel ninja imageio imageio-ffmpeg tqdm easydict opencv-python-headless trimesh "transformers<5" \
    pandas lpips zstandard kornia timm einops pillow huggingface_hub scipy
pip git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8
mkdir -p ext && cd ext
[ -d nvdiffrast ] || git clone -q -b v0.4.0 https://github.com/NVlabs/nvdiffrast.git
[ -d nvdiffrec ] || git clone -q -b renderutils https://github.com/JeffreyXiang/nvdiffrec.git
[ -d CuMesh ] || git clone -q --recursive https://github.com/JeffreyXiang/CuMesh.git
[ -d FlexGEMM ] || git clone -q --recursive https://github.com/JeffreyXiang/FlexGEMM.git
# torch >= 2.10 headers need C++20; the extensions pin C++17
sed -i 's/c++17/c++20/g' CuMesh/setup.py FlexGEMM/setup.py ../TRELLIS.2/o-voxel/setup.py
for e in nvdiffrast nvdiffrec CuMesh FlexGEMM ../TRELLIS.2/o-voxel; do
    # --no-deps: o-voxel lists CuMesh/FlexGEMM as git deps, which would rebuild them unpatched
    echo "== $e"; pip --no-build-isolation --no-deps "./$e" || { echo "FAILED: $e"; exit 1; }
done
