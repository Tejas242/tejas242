#!/usr/bin/env python3
"""Turn a rendered night into the README banner.

usage: compose.py <night.png> <portrait> <out.svg> [seed]

The night is screenager.dev's own header, rendered at 830x300 CSS px and 2x
density (see render.sh). This adds what a still image can't carry:

  - stars blink in pixel steps, the way the site's renderer twinkles them
  - a few lit windows switch off and on again over the evening
  - now and then a shooting star crosses, moving in whole art pixels
  - the portrait sits on the horizon, half in the night, as on the site

Everything is one self-contained SVG (CSS animation, inline images), so it
renders through GitHub's image proxy, and it stands still for readers who
prefer reduced motion. Stars and windows are found in the pixels themselves,
so any seed works.
"""
import base64, io, random, sys
from collections import deque

import numpy as np
from PIL import Image

night_path, portrait_path, out_path = sys.argv[1:4]
seed = sys.argv[4] if len(sys.argv) > 4 else night_path
rand = random.Random(seed)

W, H, DPR = 830, 300, 2  # CSS size of the night, and its pixel density
TILE, INSET = 112, 6  # the portrait frame, as on the site's home page
ART = 3  # one art pixel, in CSS px
SKY = "#0f150e"  # --night-sky, also the site's page background
RULE = "#353e33"  # --rule-strong in the site's dark theme

img = Image.open(night_path).convert("RGB")
assert img.size == (W * DPR, H * DPR), f"expected {W * DPR}x{H * DPR}, got {img.size}"
px = np.asarray(img).astype(int)
r, g, b = px[..., 0], px[..., 1], px[..., 2]
lum = (r + g + b) / 3
chroma = px.max(axis=2) - px.min(axis=2)


def components(mask):
    """Bounding boxes (x0, y0, x1, y1) of 4-connected regions in a boolean mask."""
    seen = np.zeros_like(mask)
    boxes = []
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        q, box = deque([(y, x)]), [x, y, x, y]
        seen[y, x] = True
        while q:
            cy, cx = q.popleft()
            box = [min(box[0], cx), min(box[1], cy), max(box[2], cx), max(box[3], cy)]
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        boxes.append(box)
    return boxes


def hexat(x, y):
    x, y = min(max(int(x), 0), W * DPR - 1), min(max(int(y), 0), H * DPR - 1)
    return "#%02x%02x%02x" % tuple(px[y, x])


def css(v):
    return round(v / DPR, 2)


# Saturn is warm; nothing near it counts as a star
sky = np.zeros(lum.shape, bool)
sky[: int(H * DPR * 0.45)] = True
warm = sky & (r - b > 28) & (lum > 90)
planet = None
if warm.any():
    ys, xs = np.nonzero(warm)
    planet = (xs.min() - 12, ys.min() - 12, xs.max() + 12, ys.max() + 12)


def off_planet(box):
    if planet is None:
        return True
    return box[2] < planet[0] or box[0] > planet[2] or box[3] < planet[1] or box[1] > planet[3]


stars = [bx for bx in components(sky & (lum > 110) & (chroma < 26)) if off_planet(bx)]
lit = np.zeros(lum.shape, bool)
lit[int(H * DPR * 0.55):] = True
lamps = (r > 170) & (g > 120) & (b < 130) & (r - b > 60)
screens = (g > 170) & (r < 160) & (b < 160)
windows = components(lit & (lamps | screens))

# ── SVG ──────────────────────────────────────────────────────────────────────
def data_uri(image, fmt):
    buf = io.BytesIO()
    image.save(buf, fmt, optimize=True)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


palette = img.quantize(colors=256, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE)
portrait = Image.open(portrait_path).convert("RGB")
side = (TILE - 2 * INSET) * DPR
portrait = portrait.resize((side, side), Image.LANCZOS)

total_h = H + TILE // 2 + 1
out = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{total_h}" viewBox="0 0 {W} {total_h}">',
    "<title>A pixel-art night over a city, the header of screenager.dev, with Tejas's portrait on the horizon</title>",
    "<style>",
    ".px{image-rendering:pixelated;image-rendering:crisp-edges}",
    "@keyframes twinkle{0%,100%{opacity:0}50%{opacity:.85}}",
    "@keyframes flicker{0%,82%,100%{opacity:0}84%,97%{opacity:1}}",
    "@keyframes fall{0%{transform:translate(0,0);opacity:0}1%{opacity:1}"
    "9%{transform:translate(var(--dx),var(--dy));opacity:0}100%{transform:translate(var(--dx),var(--dy));opacity:0}}",
    ".tw{opacity:0;animation:twinkle var(--t) steps(3,jump-none) var(--d) infinite}",
    ".fl{opacity:0;animation:flicker var(--t) steps(1,end) var(--d) infinite}",
    ".fall{opacity:0;animation:fall 13s steps(26,end) 4s infinite}",
    "@media (prefers-reduced-motion:reduce){.tw,.fl,.fall{animation:none;opacity:0}}",
    "</style>",
    f'<image class="px" width="{W}" height="{H}" href="{data_uri(palette, "PNG")}"/>',
]

# a twinkle dims a star by laying the sky beside it over it
for x0, y0, x1, y1 in rand.sample(stars, min(len(stars), 40)):
    t, d = rand.uniform(2.4, 6.5), -rand.uniform(0, 6.5)
    out.append(f'<rect class="tw" style="--t:{t:.2f}s;--d:{d:.2f}s" x="{css(x0)}" y="{css(y0)}" '
               f'width="{css(x1 - x0 + 1)}" height="{css(y1 - y0 + 1)}" fill="{hexat(x0 - 2, y0)}"/>')

# a few windows go dark for a while, each on its own clock
for x0, y0, x1, y1 in rand.sample(windows, min(len(windows), 8)):
    t, d = rand.uniform(9, 23), -rand.uniform(0, 23)
    out.append(f'<rect class="fl" style="--t:{t:.2f}s;--d:{d:.2f}s" x="{css(x0)}" y="{css(y0)}" '
               f'width="{css(x1 - x0 + 1)}" height="{css(y1 - y0 + 1)}" fill="{hexat(x0 - 1, y1 + 2)}"/>')

# a shooting star: a head and a fading tail of art pixels, sliding down-right
sx, sy = rand.uniform(40, W * 0.35), rand.uniform(12, 40)
dx, dy = 210, 66
trail = []
for i in range(6):
    k = i * 1.6
    trail.append(f'<rect x="{sx - k * ART * 1.0:.1f}" y="{sy - k * ART * dy / dx:.1f}" width="{ART}" height="{ART}" '
                 f'fill="#dfe4d9" opacity="{1 - i * 0.16:.2f}"/>')
out.append(f'<g class="fall" style="--dx:{dx}px;--dy:{dy}px">' + "".join(trail) + "</g>")

# the horizon, and the portrait seated on it
out.append(f'<rect x="0" y="{H - 1}" width="{W}" height="1" fill="{RULE}"/>')
tx, ty = (W - TILE) / 2, H - TILE / 2
out.append(f'<rect x="{tx + 0.5}" y="{ty + 0.5}" width="{TILE - 1}" height="{TILE - 1}" fill="{SKY}" stroke="{RULE}"/>')
out.append(f'<image x="{tx + INSET}" y="{ty + INSET}" width="{TILE - 2 * INSET}" height="{TILE - 2 * INSET}" '
           f'href="{data_uri(portrait, "JPEG")}"/>')
out.append("</svg>")

with open(out_path, "w") as f:
    f.write("\n".join(out) + "\n")
print(f"{out_path}: {len(stars)} stars, {len(windows)} windows")
