#!/usr/bin/env bash
# install.sh: set up the studio on this machine (Linux, user-level: no sudo).
#
#   ./install.sh                     detect GPUs, suggest a profile, ask before doing anything
#   ./install.sh --profile 16gb      pick a hardware profile (models/profiles/*.json; "online" = no local models)
#   ./install.sh --dry-run           show what would happen
#   options: --yes (no questions) --no-godot --no-models (skip downloads) --no-build (skip llama.cpp build)
#            --assets (first asset-library sync now, ~1 GB, unattended ~1 h)
#            --reconfigure (rewrite ~/.config/studio/studio.env)
#
# Modes: "online" (Claude models do the work; needs a Claude login or ANTHROPIC_API_KEY), or a local profile
# (local models do the work via llama-swap; you can still direct with Claude = "mixed", or run the director on a
# local model too with `claude-local` = fully local).
set -euo pipefail
STUDIO=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
profile="" dry=0 yes=0 godot=1 models=1 build=1 reconf=0 assets=0
while (($#)); do
  case $1 in
    --profile) profile=$2; shift ;;
    --dry-run) dry=1 ;; --yes|-y) yes=1 ;; --no-godot) godot=0 ;; --no-models) models=0 ;; --no-build) build=0 ;; --assets) assets=1 ;;
    --reconfigure) reconf=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown option $1" >&2; exit 1 ;;
  esac; shift
done
say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
run() { if ((dry)); then printf '    [dry-run] %s\n' "$*"; else "$@"; fi; }
ask() { ((yes)) && return 0; read -r -p "$1 [Y/n] " a; [[ -z $a || $a =~ ^[Yy] ]]; }

# ---------------------------------------------------------------- 1. prerequisites
say "Checking prerequisites"
missing=()
need() { command -v "$1" >/dev/null || missing+=("$1 ($2)"); }
need git "version control"; need python3 "3.10+"; need claude "Claude Code: https://claude.com/claude-code"
need bwrap "bubblewrap: the worker sandbox"; need socat "socat: sandbox network bridge"; need ffmpeg "video encode"
need curl "downloads"
command -v blender >/dev/null || echo "    optional: blender (3D models from scripts)"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || missing+=("python3 >= 3.10")
python3 -c 'import numpy, PIL' 2>/dev/null || missing+=("python3 numpy + pillow (audio, textures, graders)")
if ((${#missing[@]})); then
  echo "    missing:"; printf '      - %s\n' "${missing[@]}"
  echo "    Install them with your package manager (e.g. Arch: pacman -S bubblewrap socat ffmpeg python-numpy python-pillow;"
  echo "    Debian/Ubuntu: apt install bubblewrap socat ffmpeg python3-numpy python3-pil), then run ./install.sh again."
  ((dry)) || exit 1
fi

# ---------------------------------------------------------------- 2. GPUs and profile
say "Detecting GPUs"
gpus=()
if command -v nvidia-smi >/dev/null; then
  smi=$(CUDA_DEVICE_ORDER=PCI_BUS_ID nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader,nounits 2>&1) || true
  if grep -q "version mismatch" <<<"$smi"; then
    echo "    NVIDIA driver/library version mismatch: the driver was updated but the old kernel module is still loaded."
    echo "    Reboot, then run ./install.sh again (or pass --profile to skip detection)."
    [[ -n $profile ]] || exit 1
  fi
  mapfile -t gpus < <(grep -E '^[0-9]+, ' <<<"$smi")
fi
big=-1 bigmem=0 small=-1 smallmem=0
for g in "${gpus[@]}"; do
  IFS=, read -r i name mem <<<"$g"; mem=${mem// /}
  echo "    CUDA $i:${name} (${mem} MiB)"
  if ((mem > bigmem)); then small=$big; smallmem=$bigmem; big=$i; bigmem=$mem
  elif ((mem > smallmem)); then small=$i; smallmem=$mem; fi
done
if [[ -z $profile ]]; then
  if ((bigmem >= 22000)); then profile=24gb
  elif ((bigmem >= 15000)); then profile=16gb; ((smallmem >= 5500)) && profile=16gb+6gb-reference
  elif ((bigmem >= 11000)); then profile=12gb
  elif ((bigmem >= 7500)); then profile=8gb
  else profile=online; fi
  echo "    suggested profile: $profile"
fi
[[ -f $STUDIO/models/profiles/$profile.json ]] || { echo "no such profile: $profile (see models/profiles/)"; exit 1; }
python3 "$STUDIO/models/gen-config.py" list | awk -v p="$profile" '$1 == p {print "    " $0}'
local=1; [[ $profile == online ]] && local=0
ask "Install with profile '$profile'?" || exit 0

# Vulkan device order (Godot) can differ from CUDA's: match by name
vk_index() { # gpu name -> Vulkan index
  command -v vulkaninfo >/dev/null || { echo ""; return; }
  vulkaninfo --summary 2>/dev/null | awk -v n="$1" '/^GPU[0-9]+:/{i=substr($1,4)+0} /deviceName/ && index($0, n){print i; exit}'
}
name_of() { for g in "${gpus[@]}"; do IFS=, read -r i name _ <<<"$g"; [[ $i == "$1" ]] && echo "${name# }"; done; }

# ---------------------------------------------------------------- 3. config
CFG=$HOME/.config/studio/studio.env
if [[ ! -f $CFG || $reconf == 1 ]]; then
  say "Writing $CFG"
  godot_on_small=0; godot_gpu=0
  if ((small >= 0)); then godot_on_small=1; v=$(vk_index "$(name_of "$small")"); godot_gpu=${v:-0}
  elif ((big >= 0)); then v=$(vk_index "$(name_of "$big")"); godot_gpu=${v:-0}; fi
  # the local default model = the profile's routing worker if it is local, else its first big model
  first_big=$(python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); w=p["routing"]["worker"]["model"]; print(w if w in p["big"] else (p["big"] or [""])[0])' "$STUDIO/models/profiles/$profile.json")
  first_small=$(python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print((p["small"] or [""])[0])' "$STUDIO/models/profiles/$profile.json")
  big_models=$(python3 -c 'import json,sys; print(",".join(json.load(open(sys.argv[1]))["big"]))' "$STUDIO/models/profiles/$profile.json")
  small_models=$(python3 -c 'import json,sys; print(",".join(json.load(open(sys.argv[1]))["small"]))' "$STUDIO/models/profiles/$profile.json")
  conf="# Studio machine config (install.sh, profile $profile). Edit freely; studio-config shows the effective values.
STUDIO_PROFILE=$profile
STUDIO_PROJECTS_UE=$HOME/StudioProjects/unreal
STUDIO_PROJECTS_GODOT=$HOME/StudioProjects/godot
STUDIO_EVAL_HOME=$HOME/StudioProjects/evals
STUDIO_MODELS_DIR=$HOME/llm-models
STUDIO_UE_ROOT=
STUDIO_GODOT_HOME=$HOME/.local/share/studio/godot
STUDIO_ASSET_HOME=$HOME/StudioProjects/assets
STUDIO_LLAMA_URL=http://127.0.0.1:8080
STUDIO_GPU_POLICY=timeshare
STUDIO_GPU_MODELS=$big_models
STUDIO_SMALL_MODELS=$small_models
STUDIO_LOCAL_MODEL=$first_big
STUDIO_LOCAL_SMALL_MODEL=${first_small:-$first_big}
STUDIO_WORKER_GPU=$((big < 0 ? 0 : big))
STUDIO_SMALL_GPU=$((small < 0 ? 0 : small))
STUDIO_UE_ADAPTER=$((big < 0 ? 0 : big))
STUDIO_GODOT_GPU=$godot_gpu
STUDIO_GODOT_ON_SMALL_GPU=$godot_on_small"
  if ((dry)); then echo "$conf" | sed 's/^/    [dry-run] /'; else mkdir -p "$(dirname "$CFG")"; echo "$conf" > "$CFG"; fi
else
  say "Keeping $CFG (use --reconfigure to rewrite)"
fi

# ---------------------------------------------------------------- 4. commands, skills, routing
say "Linking commands into ~/.local/bin and skills into ~/.claude/skills"
run mkdir -p "$HOME/.local/bin" "$HOME/.claude/skills" "$HOME/.config/studio"
for f in "$STUDIO"/bin/* "$STUDIO"/models/bin/*; do [[ -f $f && -x $f ]] && run ln -sf "$f" "$HOME/.local/bin/$(basename "$f")"; done
for s in "$STUDIO"/skill/*/; do run ln -sfn "${s%/}" "$HOME/.claude/skills/$(basename "$s")"; done
say "Routing and model catalog for profile $profile"
if ((dry)); then echo "    [dry-run] write ~/.config/studio/routing.json and models.json"; else
  rm -f "$HOME/.config/studio/routing.json"   # may be a symlink into a repo: never write through it
  python3 -c 'import json,sys; open(sys.argv[2], "w").write(json.dumps(json.load(open(sys.argv[1]))["routing"], indent=2) + "\n")' \
    "$STUDIO/models/profiles/$profile.json" "$HOME/.config/studio/routing.json"
  python3 "$STUDIO/models/gen-config.py" effective "$profile" -o "$HOME/.config/studio/models.json" >/dev/null
fi

# ---------------------------------------------------------------- 5. services
say "User services (systemd --user)"
run mkdir -p "$HOME/.config/systemd/user"
for u in "$STUDIO"/systemd/*.service "$STUDIO"/systemd/*.timer; do [[ -e $u ]] && run ln -sf "$u" "$HOME/.config/systemd/user/"; done
((local)) && run ln -sf "$STUDIO/models/systemd/llama-swap.service" "$HOME/.config/systemd/user/"
run systemctl --user daemon-reload
run systemctl --user enable --now studio-broker.service
((godot)) && run systemctl --user enable --now godot-refresh.timer
run systemctl --user enable --now studio-assets-sync.timer
run systemctl --user enable --now studio-status.service   # progress dashboard (port 8767; docs/dashboard.md)

# ---------------------------------------------------------------- 6. local models
if ((local)); then
  say "Local models (profile $profile)"
  if ! command -v llama-swap >/dev/null && [[ ! -x $HOME/.local/bin/llama-swap ]]; then
    url=$(curl -s https://api.github.com/repos/mostlygeek/llama-swap/releases/latest | python3 -c \
      'import json,sys; print(next(a["browser_download_url"] for a in json.load(sys.stdin)["assets"] if "linux_amd64" in a["name"]))')
    run sh -c "curl -fsSL '$url' | tar -xz -C '$HOME/.local/bin' llama-swap"
  fi
  ((build)) && run "$STUDIO/models/build-llama.sh"
  ((models)) && run "$STUDIO/models/download.sh" "$profile"
  run python3 "$STUDIO/models/gen-config.py" llama-swap "$profile" -o "$HOME/.config/llama-swap/config.yaml"
  command -v opencode >/dev/null && run python3 "$STUDIO/models/gen-config.py" opencode "$profile" -o "$HOME/.config/opencode/opencode.json"
  run systemctl --user enable llama-swap.service
fi

# ---------------------------------------------------------------- 7. Godot
if ((godot)); then
  say "Godot (latest stable + reference bundle)"
  run "$STUDIO/bin/godot-refresh" install latest --activate
fi

# ---------------------------------------------------------------- 8. asset library (optional first sync)
if ((assets)); then
  say "Asset library: first sync (Kenney mirror, Poly Haven + ambientCG index, thumbnails)"
  run "$STUDIO/bin/studio-assets" sync
else
  echo "    Asset library: runs weekly (studio-assets-sync.timer); first sync now with: studio-assets sync"
fi

say "Done. Next:"
echo "    studio-config                      # check the paths and GPUs"
echo "    Unreal (optional): install UE 5.x, then set STUDIO_UE_ROOT in $CFG"
echo "    In Claude Code: /studio <brief>    # e.g. /studio game: a small 2D platformer in Godot"
((local)) && echo "    Fully local director: claude-local, then /studio <brief>"
