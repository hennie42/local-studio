#!/usr/bin/env bash
# Clone (first run) or pull, then build llama.cpp for llama-swap: the stock tree, plus the PrismML fork when the
# profile uses Bonsai's ternary formats. CUDA architectures: detected from nvidia-smi (override: CUDA_ARCHS="86;120").
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
archs=${CUDA_ARCHS:-$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | tr -d . | sort -u | paste -sd';')}
build() { # dir repo branch
  local dir=$1 repo=$2 branch=$3
  [[ -d $dir ]] || git clone --branch "$branch" "$repo" "$dir"
  echo ">> $dir (CUDA archs $archs)"
  git -C "$dir" pull --ff-only
  cmake -S "$dir" -B "$dir/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DGGML_CUDA=ON -DGGML_NATIVE=ON -DCMAKE_CUDA_ARCHITECTURES="$archs" -DLLAMA_CURL=OFF
  cmake --build "$dir/build" --target llama-server llama-cli llama-bench
}
build "$HOME/opt/llama.cpp" https://github.com/ggml-org/llama.cpp master
if [[ ${1:-} == --prism ]] || grep -q '"server": "prism"' "$here/catalog.json" && [[ ${1:-} != --no-prism ]]; then
  build "$HOME/opt/llama.cpp-prism" https://github.com/PrismML-Eng/llama.cpp prism
fi
if systemctl --user is-active -q llama-swap; then
  systemctl --user restart llama-swap
fi
