#!/usr/bin/env bash
# export.sh DIR: every DIR/*.drawio -> DIR/*.drawio.svg (diagram embedded: opens in draw.io) + a PNG preview in DIR/png
cd "$1" && mkdir -p png
for f in *.drawio; do
  "${DRAWIO:-drawio}" --no-sandbox -x -f svg --embed-diagram -o "${f%.drawio}.drawio.svg" "$f" >/dev/null 2>&1
  "${DRAWIO:-drawio}" --no-sandbox -x -f png -s 1 -o "png/${f%.drawio}.png" "$f" >/dev/null 2>&1
  # drop draw.io's PNG fallbacks for the HTML labels (browsers render the labels; the fallbacks are 90% of the file)
  python3 - "${f%.drawio}.drawio.svg" <<'PY'
import re, sys
p = sys.argv[1]; t = open(p).read()
t = re.sub(r'<image [^>]*href="data:image/png;base64,[^"]*"[^>]*/>', '', t)
open(p, "w").write(t)
PY
done
ls -la *.svg
