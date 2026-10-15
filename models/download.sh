#!/usr/bin/env bash
# download.sh PROFILE: fetch the GGUF files a hardware profile needs into STUDIO_MODELS_DIR. Re-run to resume.
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
eval "$(python3 "$here/../lib/studio_config.py" --shell)"
profile=${1:?usage: download.sh PROFILE   (see: models/gen-config.py list)}
mkdir -p "$STUDIO_MODELS_DIR"
python3 "$here/gen-config.py" downloads "$profile" | while read -r repo file dest; do
  dest=${dest:-$file}
  url="https://huggingface.co/$repo/resolve/main/$file"
  if [[ -f "$STUDIO_MODELS_DIR/$dest" ]]; then
    remote=$(curl -sIL "$url" | tr -d '\r' | awk 'tolower($1)=="content-length:"{n=$2} END{print n}')
    if [[ -n $remote && $remote == "$(stat -c %s "$STUDIO_MODELS_DIR/$dest")" ]]; then
      echo ">> $dest complete"; continue
    fi
  fi
  echo ">> $repo/$file -> $dest"
  curl -fL --retry 5 -C - -o "$STUDIO_MODELS_DIR/$dest" "$url"
done
