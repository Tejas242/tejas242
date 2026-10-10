#!/usr/bin/env python3
"""Draw the README's header: assets/header-dark.svg and assets/header-light.svg.

usage: header.py        (SITE=~/portfolio/screenager.dev for the fonts)

The wordmark is Figtree Black and the line under it JetBrains Mono, both taken
from screenager.dev and turned into outlines, so GitHub needs no fonts. The
full stop is one green pixel and the dots are the palette the site, the
desktop and this page share, the same build as the dots README's header.
Runs locally only; the workflow never touches the header.
"""
import os, pathlib

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = pathlib.Path(os.environ.get("SITE", "~/portfolio/screenager.dev")).expanduser() / "src/assets/fonts"

WORD, LINE = "screenager", "backend  ·  search  ·  llm tooling  ·  go"
ALT = "screenager. backend, search, llm tooling, go"
W, H = 960, 250
BASE, SIZE, DOTS = 126, 132, 182  # wordmark baseline and size; the palette sits clear of the j
PIXEL, GAP = 22, 9  # the full stop and the space before it
SUB_BASE, SUB_SIZE, TRACK = 234, 20, 1.5

PALETTE = ["#0f150e", "#1b211a", "#889484", "#dee5d8", "#72dd71", "#a5d29e", "#9ccaff", "#ffb4ab"]
THEMES = {  # ink, full stop, line, dots that need an outline to be seen
    "dark": ("#dee5d8", "#72dd71", "#889484", {"#0f150e", "#1b211a"}),
    "light": ("#0f150e", "#2e8b3a", "#5d6859", {"#dee5d8", "#9ccaff", "#ffb4ab"}),
}


def font(name, weight):
    f = TTFont(FONTS / name)
    return instantiateVariableFont(f, {"wght": weight}) if "fvar" in f else f


def kerning(f):
    """Pair adjustments from GPOS (formats 1 and 2), enough for one short word."""
    pairs, classes = {}, []
    if "GPOS" not in f:
        return lambda a, b: 0
    for lookup in f["GPOS"].table.LookupList.Lookup:
        for sub in lookup.SubTable:
            sub = getattr(sub, "ExtSubTable", sub)
            if getattr(sub, "LookupType", lookup.LookupType) != 2:
                continue
            if sub.Format == 1:
                for first, ps in zip(sub.Coverage.glyphs, sub.PairSet):
                    for rec in ps.PairValueRecord:
                        v = rec.Value1 and getattr(rec.Value1, "XAdvance", 0) or 0
                        pairs.setdefault((first, rec.SecondGlyph), v)
            elif sub.Format == 2:
                classes.append(sub)

    def kern(a, b):
        if (a, b) in pairs:
            return pairs[(a, b)]
        for sub in classes:
            if a not in sub.Coverage.glyphs:
                continue
            c1, c2 = sub.ClassDef1.classDefs.get(a, 0), sub.ClassDef2.classDefs.get(b, 0)
            v = sub.Class1Record[c1].Class2Record[c2].Value1
            if v is not None and getattr(v, "XAdvance", 0):
                return v.XAdvance
        return 0

    return kern


def outline(f, text, size, track=0.0):
    """The text as one path at the origin, and its advance width."""
    cmap, glyphs = f.getBestCmap(), f.getGlyphSet()
    scale, kern = size / f["head"].unitsPerEm, kerning(f)
    names = [cmap[ord(ch)] for ch in text]
    pen, x = SVGPathPen(glyphs, lambda v: f"{v:.2f}".rstrip("0").rstrip(".")), 0.0
    for i, name in enumerate(names):
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
        x += glyphs[name].width * scale + track
        if i + 1 < len(names):
            x += kern(name, names[i + 1]) * scale
    return pen.getCommands(), x - track


def main():
    word, word_w = outline(font("Figtree-normal.woff2", 900), WORD, SIZE)
    line, line_w = outline(font("JetBrainsMono-normal.woff2", 400), LINE, SUB_SIZE, TRACK)
    left = (W - (word_w + GAP + PIXEL)) / 2
    dots_left = W / 2 - (len(PALETTE) - 1) * 14
    for theme, (ink, stop, muted, ringed) in THEMES.items():
        out = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-label="{ALT}">',
            f"<title>{ALT}</title>",
            f'<path fill="{ink}" transform="translate({left:.2f} {BASE})" d="{word}"/>',
            f'<rect x="{left + word_w + GAP:.2f}" y="{BASE - PIXEL}" width="{PIXEL}" height="{PIXEL}" fill="{stop}"/>',
        ]
        for i, c in enumerate(PALETTE):
            ring = ' stroke="#889484" stroke-width="1"' if theme == "dark" and c in ringed else ""
            ring = ' stroke="#9aa596" stroke-width="1"' if theme == "light" and c in ringed else ring
            out.append(f'<circle cx="{dots_left + i * 28:.1f}" cy="{DOTS}" r="7" fill="{c}"{ring}/>')
        out.append(f'<path fill="{muted}" transform="translate({(W - line_w) / 2:.2f} {SUB_BASE})" d="{line}"/>')
        out.append("</svg>")
        (ROOT / f"assets/header-{theme}.svg").write_text("\n".join(out) + "\n")
        print(f"assets/header-{theme}.svg")


main()
