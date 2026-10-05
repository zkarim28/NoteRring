"""Fit-check: lay the parts out in two layers (skin side and top side), size a case around them, draw it.

    .venv/bin/python fitcheck.py            writes fitcheck.png, fitcheck.stl and prints the case size
Edit parts.py with your measurements first. All parts are drawn as plain blocks.
"""
import argparse
import json
import sys

from build123d import Box, Compound, Pos, export_stl

import parts as P
from preview import render
from viewer import write_html


def pack(items, max_length):
    """Shelf packing: fill rows along x up to max_length. items: [(name, x, y)]. Returns ({name: (x0, y0)}, width, depth)."""
    placed, x, y, row_depth, width = {}, 0.0, 0.0, 0.0, 0.0
    for name, w, d in sorted(items, key=lambda t: -t[2]):
        if x > 0 and x + w > max_length:
            y += row_depth + P.GAP
            x, row_depth = 0.0, 0.0
        placed[name] = (x, y)
        x += w + P.GAP
        row_depth = max(row_depth, d)
        width = max(width, x - P.GAP)
    return placed, width, y + row_depth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", action="append", default=[], help="leave a part out, e.g. --skip 'SD card module' (repeatable)")
    ap.add_argument("--max-length", type=float, default=P.MAX_LENGTH, help="longest the case may be along the wrist (mm, inner)")
    ap.add_argument("--out", default="fitcheck", help="output name (writes NAME.png)")
    args = ap.parse_args()
    P.MAX_LENGTH = args.max_length
    parts = {k: v for k, v in P.PARTS.items() if k not in args.skip and P.ENABLED.get(k, True)}
    if P.USE_CHARGER_MODULE:
        parts[P.CHARGER[0]] = P.CHARGER[1]
    layers = {"bottom": [], "top": []}
    for name, (x, y, z, layer, colour, note) in parts.items():
        layers[layer].append((name, x, y))
    packed = {k: pack(v, P.MAX_LENGTH) for k, v in layers.items()}
    inner_x = max(w for _, w, _ in packed.values()) + 2 * P.CLEARANCE
    inner_y = max(d for _, _, d in packed.values()) + 2 * P.CLEARANCE
    h = {k: max((parts[n][2] for n, _, _ in v), default=0) for k, v in layers.items()}
    inner_z = h["bottom"] + P.GAP + h["top"] + 2 * P.CLEARANCE if h["bottom"] else h["top"] + 2 * P.CLEARANCE
    outer = (inner_x + 2 * P.WALL, inner_y + 2 * P.WALL, inner_z + P.SKIN_WALL + P.WALL)

    shapes, named = [], []
    z_bottom = P.SKIN_WALL + P.CLEARANCE
    z_top = z_bottom + (h["bottom"] + P.GAP if h["bottom"] else 0)
    for layer, z0 in (("bottom", z_bottom), ("top", z_top)):
        placed, _, _ = packed[layer]
        for name, (px, py) in placed.items():
            x, y, z, _, colour, _ = parts[name]
            cx = P.WALL + P.CLEARANCE + px + x / 2
            cy = P.WALL + P.CLEARANCE + py + y / 2
            block = Pos(cx, cy, z0 + z / 2) * Box(x, y, z)
            shapes.append((block, colour, 0.95))
            named.append((name, block, colour))
    case = Pos(outer[0] / 2, outer[1] / 2, outer[2] / 2) * Box(*outer)
    shapes.insert(0, (case, "#bbbbbb", 0.12))
    # an open-topped shell (floor + four walls) so the 3D files show the parts sitting inside it
    cavity_h = outer[2] - P.SKIN_WALL + 1
    shell = case - Pos(outer[0] / 2, outer[1] / 2, P.SKIN_WALL + cavity_h / 2) * Box(outer[0] - 2 * P.WALL, outer[1] - 2 * P.WALL, cavity_h)

    render(shapes, args.out + ".png")
    export_stl(Compound([shell] + [b for _, b, _ in named]), args.out + "_assembly.stl")
    write_html(args.out + ".html", [("case (open top)", shell, "#9aa0a6", 0.28)] + [(n, b, c, 1.0) for n, b, c in named],
               title=f"Wrist unit fit-check: {outer[0]:.1f} x {outer[1]:.1f} x {outer[2]:.1f} mm")
    with open("layout.json", "w") as fh:
        json.dump({"outer": [round(v, 2) for v in outer]}, fh)
    print(f"case outer size: {outer[0]:.1f} x {outer[1]:.1f} x {outer[2]:.1f} mm  (x along wrist, y across, z height)")
    print(f"  skin-side layer {h['bottom']:.1f} mm tall, top layer {h['top']:.1f} mm tall, walls {P.WALL} (skin side {P.SKIN_WALL})")
    for layer in ("bottom", "top"):
        for name in packed[layer][0]:
            print(f"  [{layer:6}] {name}: {parts[name][0]} x {parts[name][1]} x {parts[name][2]}   {parts[name][5]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
