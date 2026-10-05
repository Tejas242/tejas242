#!/usr/bin/env python3
"""Turn a rendered night into the README's art.

usage: compose.py <night.png> <out.svg> [seed]

The night is screenager.dev's own header, rendered at 830x300 CSS px and 2x
density (see render.sh). This adds what a still image can't carry, all of it
moving in whole art pixels like the site's renderer:

  - stars blink, each on its own clock
  - lit windows go dark for a while, and a few dark ones come on
  - now and then a shooting star falls, two of them on different schedules
  - once in a long while a satellite crosses the top of the sky

One self-contained SVG (CSS animation, inline image), so it renders through
GitHub's image proxy, and it stands still for readers who prefer reduced
motion. Stars and windows are found in the pixels themselves, so any seed works.
"""
import base64, io, random, sys
from collections import deque

import numpy as np
from PIL import Image

night_path, out_path = sys.argv[1:3]
rand = random.Random(sys.argv[3] if len(sys.argv) > 3 else night_path)

W, H, DPR = 830, 300, 2  # CSS size of the night, and its pixel density
ART = 3  # one art pixel, in CSS px
STAR = "#dfe4d9"  # --night-star

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
town = np.zeros(lum.shape, bool)
town[int(H * DPR * 0.55):] = True
lamps = (r > 170) & (g > 120) & (b < 130) & (r - b > 60)
screens = (g > 170) & (r < 160) & (b < 160)
windows = components(town & (lamps | screens))


def data_uri(image):
    buf = io.BytesIO()
    image.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def rect(cls, t, d, box, fill):
    x0, y0, x1, y1 = box
    return (f'<rect class="{cls}" style="--t:{t:.2f}s;--d:{d:.2f}s" x="{css(x0)}" y="{css(y0)}" '
            f'width="{css(x1 - x0 + 1)}" height="{css(y1 - y0 + 1)}" fill="{fill}"/>')


def streak(sx, sy, dx, dy):
    """A shooting star's head and fading tail, laid back along its path."""
    k = dy / dx
    return "".join(f'<rect x="{sx - i * 1.6 * ART:.1f}" y="{sy - i * 1.6 * ART * k:.1f}" width="{ART}" '
                   f'height="{ART}" fill="{STAR}" opacity="{1 - i * 0.16:.2f}"/>' for i in range(6))


palette = img.quantize(colors=256, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE)
out = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
    "<title>A pixel-art night over a city, from screenager.dev: stars blink, windows go dark and light up, "
    "and now and then something falls</title>",
    "<style>",
    ".px{image-rendering:pixelated;image-rendering:crisp-edges}",
    "@keyframes twinkle{0%,100%{opacity:0}50%{opacity:.85}}",
    "@keyframes dark{0%,82%,100%{opacity:0}84%,97%{opacity:1}}",
    "@keyframes light{0%,82%,100%{opacity:1}84%,97%{opacity:0}}",
    "@keyframes fall{0%{transform:translate(0,0);opacity:0}1%{opacity:1}"
    "9%{transform:translate(var(--dx),var(--dy));opacity:0}100%{transform:translate(var(--dx),var(--dy));opacity:0}}",
    "@keyframes orbit{0%{transform:translateX(0)}70%,100%{transform:translateX(var(--dx))}}",
    "@keyframes beacon{0%,100%{opacity:.35}50%{opacity:.9}}",
    ".tw{opacity:0;animation:twinkle var(--t) steps(3,jump-none) var(--d) infinite}",
    ".off{opacity:0;animation:dark var(--t) steps(1,end) var(--d) infinite}",
    ".on{opacity:1;animation:light var(--t) steps(1,end) var(--d) infinite}",
    ".fall{opacity:0;animation:fall var(--t) steps(26,end) var(--d) infinite}",
    f".sat{{animation:orbit 95s steps({W // ART},end) -20s infinite}}",
    ".sat rect{animation:beacon 2.4s steps(2,jump-none) infinite}",
    "@media (prefers-reduced-motion:reduce){.tw,.off,.fall,.sat,.sat rect{animation:none}.tw,.off,.fall{opacity:0}"
    ".on{opacity:1}.sat{display:none}}",
    "</style>",
    f'<image class="px" width="{W}" height="{H}" href="{data_uri(palette)}"/>',
]

# a twinkle dims a star by laying the sky beside it over it
for box in rand.sample(stars, min(len(stars), 40)):
    out.append(rect("tw", rand.uniform(2.4, 6.5), -rand.uniform(0, 6.5), box, hexat(box[0] - 2, box[1])))

# windows keep their own hours: most go dark for a while, a few start dark and come on
lit = rand.sample(windows, min(len(windows), 12))
for i, box in enumerate(lit):
    cls = "on" if i % 4 == 0 else "off"
    out.append(rect(cls, rand.uniform(9, 23), -rand.uniform(0, 23), box, hexat(box[0] - 1, box[3] + 2)))

# two shooting stars on schedules that rarely line up
for t, delay in ((13, 4), (29, 17)):
    sx, sy = rand.uniform(40, W * 0.45), rand.uniform(10, 46)
    dx, dy = rand.uniform(170, 240), rand.uniform(50, 80)
    out.append(f'<g class="fall" style="--t:{t}s;--d:{delay}s;--dx:{dx:.0f}px;--dy:{dy:.0f}px">'
               + streak(sx, sy, dx, dy) + "</g>")

# a satellite: one dim pixel crossing the top of the sky, then gone for a while
sy = rand.choice(range(6, 30, ART))
out.append(f'<g class="sat" style="--dx:{W + 2 * ART}px"><rect x="{-ART}" y="{sy}" width="{ART}" height="{ART}" '
           f'fill="#bfcab8"/></g>')
out.append("</svg>")

with open(out_path, "w") as f:
    f.write("\n".join(out) + "\n")
print(f"{out_path}: {len(stars)} stars, {len(windows)} windows")
