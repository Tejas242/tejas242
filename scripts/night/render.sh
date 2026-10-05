#!/usr/bin/env bash
# Render a week of nights for the README art: assets/nights/<mon..sun>.svg.
#
#   scripts/night/render.sh [seed-hex ...]     seven seeds, Monday first
#
# Runs locally: it bundles screenager.dev's own night generator (a private repo,
# so CI can't), renders each seed headless at 830x300 CSS px and 2x density, and
# hands the frame to compose.py. The workflow then shows the night for the day.
#
#   SITE=~/portfolio/screenager.dev   the site checkout
#   BROWSER=brave                     any Chromium with --headless=new
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SITE="${SITE:-$HOME/portfolio/screenager.dev}"
BROWSER="${BROWSER:-brave}"
SEEDS=("$@")
[ ${#SEEDS[@]} -eq 7 ] || SEEDS=(5eed0001 1a2b3c4d c0ffee42 7a1e0b05 0badf00d 2c852c00 9e43960a)
DAYS=(mon tue wed thu fri sat sun)

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir "$work/night"
cp "$SITE"/src/lib/night/*.ts "$SITE/src/lib/css-colour.ts" "$work/night/"
rm -f "$work"/night/*.test.ts
sed -i 's#@/lib/night/#./#g; s#@/lib/css-colour#./css-colour#' "$work"/night/*.ts
cat > "$work/entry.ts" <<'EOF'
import { mountNight } from "./night/render"

const seed = Number.parseInt(new URLSearchParams(location.search).get("seed") ?? "1", 16)
mountNight(document.querySelector("canvas") as HTMLCanvasElement, { seed, setting: "city" })
EOF
bun build "$work/entry.ts" --target browser --outfile "$work/night.js" >/dev/null

vars="$(sed -n '/^:root {/,/^}/p' "$SITE/src/styles/color.css" | grep -- '--night')"
cat > "$work/index.html" <<EOF
<!doctype html><meta charset="utf-8"><style>
:root{$vars}
html,body{margin:0;overflow:hidden}
.frame{position:relative;width:830px;height:300px;overflow:hidden;
  background:linear-gradient(var(--night-sky) 35%,var(--night-horizon))}
canvas{position:absolute;inset:0 auto auto 0;image-rendering:pixelated}
</style><div class="frame"><canvas></canvas></div><script src="night.js"></script>
EOF

# A brand-new browser profile can stall on its first headless launch, so keep one.
profile="${XDG_CACHE_HOME:-$HOME/.cache}/readme-night-browser"
mkdir -p "$ROOT/assets/nights"
for i in "${!SEEDS[@]}"; do
  png="$work/${SEEDS[$i]}.png"
  for _ in 1 2; do
    timeout 60 "$BROWSER" --headless=new --user-data-dir="$profile" --no-first-run \
      --use-angle=swiftshader --enable-unsafe-swiftshader --force-prefers-reduced-motion \
      --hide-scrollbars --window-size=830,300 --force-device-scale-factor=2 \
      --virtual-time-budget=4000 --allow-file-access-from-files --screenshot="$png" \
      "file://$work/index.html?seed=${SEEDS[$i]}" >"$work/browser.log" 2>&1 || true
    [ -s "$png" ] && break
  done
  [ -s "$png" ] || { echo "render.sh: no image for seed ${SEEDS[$i]}" >&2; exit 1; }
  python3 "$ROOT/scripts/night/compose.py" "$png" "$ROOT/assets/nights/${DAYS[$i]}.svg" "${SEEDS[$i]}"
done
cp "$ROOT/assets/nights/$(date -u +%a | tr '[:upper:]' '[:lower:]').svg" "$ROOT/assets/night.svg"
