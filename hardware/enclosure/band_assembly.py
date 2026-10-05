"""The watch head as one big link of a Zen-style chain, plus a small test strip. Everything prints flat, in place.

    .venv/bin/python band_assembly.py --test-strip                  4 links, 3 joints with different clearances (print this first)
    .venv/bin/python band_assembly.py --wrist-circ 165              the whole band: links + head + links

Writes band_flat.stl / band_flat.html (or test_strip.stl). The head here is the plain open-top shell from fitcheck.py's layout
(outer size from layout.json): no lid, display window or USB-C opening yet.
Axes while printing: x along the band, y across it, z up from the bed (the bed side is the skin side).
"""
import argparse
import json
import math
import os

from build123d import Axis, Box, Compound, Pos, export_stl

import zen
from viewer import write_html

HERE = os.path.dirname(os.path.abspath(__file__))
PLAIN = "#aab2bd"


def head_module(outer, floor=2.5, wall=2.0, clr=0.35, side=0.3):
    """Shell + a slot lug on its left + a tongue lug on its right, fused into one body. Left face at x = 0."""
    ox, oy, oz = outer
    shell_x0 = zen.L - 1.0                                      # the lugs overlap the shell by 1 mm so everything fuses
    shell = Pos(shell_x0 + ox / 2, 0, oz / 2) * Box(ox, oy, oz)
    cavity = Pos(shell_x0 + ox / 2, 0, floor + (oz - floor + 1) / 2) * Box(ox - 2 * wall, oy - 2 * wall, oz - floor + 1)
    shell = shell - cavity
    left = zen.link(clr, side, slot=True, with_tongue=False)
    right_x = shell_x0 + ox - 1.0
    right = Pos(right_x, 0, 0) * zen.link(clr, side, slot=False, with_tongue=True)
    body = shell + left + right
    return body, right_x + zen.L                                # module body ends here (before the neighbour's gap)


def clasp_parts(style):
    """(male_end, female_end, closed_pair) functions for the chosen buckle style."""
    if style == "open":
        return zen.male_end, zen.female_end, zen.closed_pair
    return zen.male_end_enc, zen.female_end_enc, zen.closed_pair_enc


def band(outer, wrist_circ, clr=0.35, side=0.3, clasp="enclosed"):
    """links + head module + links, with the snap-buckle ends: prongs on the far left, socket on the far right."""
    male_fn, female_fn, _ = clasp_parts(clasp)
    head, head_end = head_module(outer, clr=clr, side=side)
    target = wrist_circ + math.pi * zen.T          # the band's centre line runs T/2 above the skin
    n_each = max(2, round(((target - head_end - zen.GAP - zen.FEMALE_LEN) / zen.PITCH + 1) / 2))
    left = []
    for j in range(n_each):                                      # j = 0 is the free (prong) end
        x = -(n_each - j) * zen.PITCH
        left.append(Pos(x, 0, 0) * (male_fn(clr, side) if j == 0 else zen.link(clr, side, slot=True, with_tongue=True)))
    right = []
    for k in range(n_each):
        x = head_end + zen.GAP + k * zen.PITCH
        last = k == n_each - 1
        right.append(Pos(x, 0, 0) * (female_fn(clr, side, slot=True) if last else zen.link(clr, side, slot=True, with_tongue=True)))
    loop_len = (2 * n_each - 1) * zen.PITCH + head_end + zen.GAP + zen.FEMALE_LEN
    return left, head, right, n_each, head_end, loop_len


def test_strip():
    """4 links, joints with (pin clearance, side clearance) = (0.25, 0.20), (0.35, 0.30), (0.45, 0.40)."""
    pairs = [(0.25, 0.20), (0.35, 0.30), (0.45, 0.40)]
    links = []
    for i in range(4):
        tongue_clr = pairs[i][0] if i < 3 else 0.35
        slot_side = pairs[i - 1][1] if i > 0 else 0.3
        links.append(Pos(i * zen.PITCH, 0, 0) * zen.link(tongue_clr, slot_side, slot=(i > 0), with_tongue=(i < 3)))
    return links, pairs


def check(solids, names):
    """Overlap and closest distance between neighbours; returns the worst values."""
    worst_overlap, closest = 0.0, 1e9
    for i in range(len(solids) - 1):
        ov = solids[i] & solids[i + 1]
        worst_overlap = max(worst_overlap, ov.volume if ov is not None else 0.0)
        closest = min(closest, solids[i].distance_to(solids[i + 1]))
    return worst_overlap, closest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-strip", action="store_true")
    ap.add_argument("--clasp-test", action="store_true", help="just the two halves of the snap buckle, to test it before the whole band")
    ap.add_argument("--wrist-circ", type=float, default=165.0)
    ap.add_argument("--clasp", choices=["enclosed", "open"], default="enclosed", help="enclosed = closed sleeve, pull to release; open = side windows, squeeze to release")
    ap.add_argument("--clr", type=float, default=0.35, help="clearance around the pin (mm)")
    ap.add_argument("--side", type=float, default=0.30, help="clearance each side of the tongue (mm)")
    a = ap.parse_args()

    if a.test_strip:
        links, pairs = test_strip()
        ov, closest = check(links, None)
        export_stl(Compound(links), "test_strip.stl")
        write_html("test_strip.html", [(f"link {i + 1}", s, PLAIN, 1.0) for i, s in enumerate(links)], title="Test strip: 3 joints, tighter to looser")
        print("test_strip.stl written: 4 links, 3 joints (left to right): " + ", ".join(f"pin {c:.2f} / side {s:.2f} mm" for c, s in pairs))
        print(f"  neighbour overlap {ov:.4f} mm^3 (must be 0), closest gap {closest:.2f} mm, size {4 * zen.PITCH + 4.5:.1f} x {zen.W} x {zen.T} mm")
        return

    male_fn, female_fn, pair_fn = clasp_parts(a.clasp)
    if a.clasp_test:
        female = female_fn(a.clr, a.side, slot=False)
        male = Pos(zen.FEMALE_LEN + 18.0, 0, 0) * male_fn(a.clr, a.side, tongue_on=False)
        export_stl(Compound([female, male]), "clasp_test.stl")
        f2, m2 = pair_fn(a.clr, a.side)
        write_html("clasp_closed.html", [("socket (female)", f2, "#e08a1e", 1.0), ("prongs (male)", m2, "#6c7a89", 1.0)], title=f"Snap buckle ({a.clasp}), closed")
        keep = Pos(60, 0, 0.99) * Box(160, 40, 1.98)          # the lower half only (z < 1.98): a cutaway through the middle of the tunnel
        write_html("clasp_section.html", [("socket, cut open", f2 & keep, "#e08a1e", 1.0), ("prongs, cut open", m2 & keep, "#6c7a89", 1.0)],
                   title=f"Buckle cutaway ({a.clasp}): looking into the sleeve")
        print(f"clasp_test.stl ({a.clasp}): the socket and the prong end, printed apart (push them together by hand to test the click)")
        print("clasp_closed.html: closed; clasp_section.html: cut in half so you can see inside the sleeve")
        return

    layout = os.path.join(HERE, "layout.json")
    outer = json.load(open(layout))["outer"] if os.path.exists(layout) else [47.7, 36.2, 17.7]
    left, head, right, n_each, head_end, loop_len = band(outer, a.wrist_circ, a.clr, a.side, a.clasp)
    chain = left + [head] + right
    ov, closest = check(chain, None)
    export_stl(Compound(chain), "band_flat.stl")
    items = [(f"prong end (male half of the {a.clasp} buckle)", left[0], "#e08a1e", 1.0), ("links, left of the head", Compound(left[1:]), PLAIN, 1.0),
             ("head module (shell + hinge lugs)", head, "#6c7a89", 1.0), ("links, right of the head", Compound(right[:-1]), "#8fa3b8", 1.0),
             ("socket end (female half of the buckle)", right[-1], "#e08a1e", 1.0)]
    write_html("band_flat.html", items, title=f"Band as printed (flat): {2 * n_each} parts + head, wrist {a.wrist_circ:.0f} mm")
    bb = Compound(chain).bounding_box()
    print(f"band_flat.stl: {2 * n_each} links ({n_each} each side, incl. the two buckle ends) + the head module, {len(chain)} separate bodies")
    print(f"  print size {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm (fits a 256 mm bed: {bb.size.X < 250})")
    print(f"  neighbour overlap {ov:.4f} mm^3 (must be 0), closest gap between neighbours {closest:.2f} mm")
    print(f"  closed loop length {loop_len:.1f} mm along the band centre line, about {loop_len - math.pi * zen.T:.0f} mm round the skin (target {a.wrist_circ:.0f} mm)")
    print(f"  rigid head module {head_end:.1f} mm; buckle: prongs {zen.PL:.0f} mm long, socket plate {zen.FEMALE_LEN:.1f} mm")
    vol = sum(s.volume for s in chain)
    print(f"  plastic volume ~{vol / 1000:.1f} cm^3, about {vol / 1000 * 1.27:.0f} g in PETG")


if __name__ == "__main__":
    main()
