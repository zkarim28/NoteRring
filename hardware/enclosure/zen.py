"""Print-in-place chain links with fully enclosed hinge pins, in the style of the Zen Link bracelet (own geometry).

Printed flat: x = along the chain, y = across the band (hinge axes run along y), z = thickness (the side on the bed is the skin side).

Every link has a slot (female end) at its LEFT face and a tongue (male end) at its RIGHT end:
  * slot: a cavity open at the left face, 5.6 mm wide, with the pin fused into the two side walls ("ears"),
  * tongue: 5 mm wide, rounded, with a hole slightly bigger than the pin.
The next link's slot receives the tongue, so the pin is hidden inside the 13 mm wide plate: nothing is visible from the sides.
Clearances (`clr` around the pin, `side` on each side of the tongue) are what make it move after printing; tune them with a test strip.
"""
from build123d import Axis, Box, Cylinder, Pos, Rot, chamfer

T = 4.0          # thickness
W = 13.0         # band width
L = 7.0          # plate length
GAP = 0.5        # gap between neighbouring plates
A = 2.5          # hinge axis distance from a link's left face
PIN_D = 2.7
TONGUE_W = 5.0
CH = 1.0         # chamfer on the plate end edges, so neighbouring links can bend
PITCH = L + GAP  # hinge to hinge
AXIS_R = L + GAP + A      # hinge axis of the tongue, measured from the link's left face


def _y_cylinder(radius, length):
    """A cylinder along y (the hinge axis direction)."""
    return Rot(90, 0, 0) * Cylinder(radius, length)


def slot_and_pin(clr, side):
    """(cut, pin): the cavity to cut from a plate's left end, and the pin to fuse back in."""
    slot_w = TONGUE_W + 2 * side
    cut = Pos(A / 2 - 0.05, 0, T / 2) * Box(A + 0.1, slot_w, T + 2)
    cut = cut + Pos(A, 0, T / 2) * _y_cylinder(T / 2 + 0.4, slot_w)
    pin = Pos(A, 0, T / 2) * _y_cylinder(PIN_D / 2, slot_w + 1.2)       # 0.6 mm embedded into each ear
    return cut, pin


def tongue(clr, length_to=AXIS_R, start=None):
    """The male end: a rounded tongue with the pin hole, starting `start` (default L - 1) inside the plate."""
    s = L - 1.0 if start is None else start
    t = Pos((s + length_to) / 2, 0, T / 2) * Box(length_to - s, TONGUE_W, T)
    t = t + Pos(length_to, 0, T / 2) * _y_cylinder(T / 2, TONGUE_W)
    hole = Pos(length_to, 0, T / 2) * _y_cylinder(PIN_D / 2 + clr, TONGUE_W + 1)
    return t - hole


def link(clr=0.35, side=0.3, slot=True, with_tongue=True, length=L):
    """One plate. Left face at x = 0."""
    body = Pos(length / 2, 0, T / 2) * Box(length, W, T)
    body = chamfer(body.edges().filter_by(Axis.Y), CH)
    if slot:
        cut, pin = slot_and_pin(clr, side)
        body = (body - cut) + pin
    if with_tongue:
        body = body + tongue(clr, length + GAP + A, length - 1.0)
    return body


def chain(n, clr=0.35, side=0.3):
    """n links in a row, printed flat. Returns a list of solids (each link a separate body)."""
    return [Pos(i * PITCH, 0, 0) * link(clr, side, slot=True, with_tongue=(i < n - 1 or True)) for i in range(n)]


# ---------------------------------------------------------------- clasp: printed side-release snap buckle
# Male end (left free end of the band): two flexible prongs with barbs. Female end (right free end): a long plate with a
# tunnel and a window in each side wall. Prongs flex in the print plane (y), so the layers run along the flexing direction:
# strong. Needs PETG (or a tough PLA); the strain on the prongs is about 1.5 %.
PL = 12.0            # prong length
ARM_W = 1.7          # prong thickness in the flexing direction
ARM_OUT = 4.2        # outer face of a prong (relaxed), measured from the centre line
BARB_H = 1.0         # how far a barb sticks out
BARB_Z = 2.0         # barb height (z), centred in the thickness
BARB_LEAD = 2.0      # length of the entry ramp
BARB_LEN = 3.2       # ramp + flat
TUNNEL_HALF = 4.4    # half width of the tunnel (0.2 mm clearance round the prongs)
TUNNEL_DEPTH = 13.0
WIN_Z = 2.4          # window height, centred
FEMALE_LEN = 6.5 + TUNNEL_DEPTH     # plate length: 6.5 mm of slot + wall, then the tunnel
BUTT_GAP = 0.3       # gap between the two end faces when the clasp is closed
CATCH_PLAY = 0.2     # slack between a barb's back face and the window's catch edge


def _poly(points, z0, height):
    from build123d import Polygon, extrude
    prism = extrude(Polygon(*points, align=None), amount=height)
    return Pos(0, 0, z0 - prism.bounding_box().min.Z) * prism      # whichever way it extruded, sit it at z0 .. z0 + height


def male_end(clr=0.35, side=0.3, tongue_on=True):
    """A normal link (tongue on the right) with two barbed prongs sticking out of its plain left face."""
    body = link(clr, side, slot=False, with_tongue=tongue_on)
    for s in (1, -1):
        y0, y1 = sorted((s * (ARM_OUT - ARM_W), s * ARM_OUT))
        arm = Pos(-PL / 2 + 0.25, (y0 + y1) / 2, T / 2) * Box(PL + 0.5, y1 - y0, T)
        barb = _poly([(-PL, s * (ARM_OUT - 0.1)), (-PL + BARB_LEAD, s * (ARM_OUT + BARB_H)),
                      (-PL + BARB_LEN, s * (ARM_OUT + BARB_H)), (-PL + BARB_LEN, s * (ARM_OUT - 0.1))],
                     (T - BARB_Z) / 2, BARB_Z)
        body = body + arm + barb
    return body


def female_end(clr=0.35, side=0.3, slot=True):
    """A long plate: slot + pin on its left (to join the chain), a tunnel with two side windows opening to the right."""
    body = link(clr, side, slot=slot, with_tongue=False, length=FEMALE_LEN)
    tunnel = Pos(FEMALE_LEN - TUNNEL_DEPTH / 2 + 0.5, 0, T / 2) * Box(TUNNEL_DEPTH + 1, 2 * TUNNEL_HALF, T + 2)
    body = body - tunnel
    x_catch = FEMALE_LEN + BUTT_GAP - (PL - BARB_LEN) + CATCH_PLAY      # the window edge a barb's back face rests against
    x_front = x_catch - (BARB_LEN + 0.8)
    for s in (1, -1):
        win = Pos((x_front + x_catch) / 2, s * (TUNNEL_HALF + 1.2), T / 2) * Box(x_catch - x_front, 2.8, WIN_Z)
        body = body - win
    return body


def closed_pair(clr=0.35, side=0.3):
    """(female, male) positioned as when the clasp is closed. Female occupies x = 0..FEMALE_LEN."""
    female = female_end(clr, side, slot=False)
    male = Pos(FEMALE_LEN + BUTT_GAP, 0, 0) * male_end(clr, side)
    return female, male


# ---------------------------------------------------------------- enclosed clasp (default): closed sleeve + hidden detent pockets
# The socket is a fully closed tube (0.8 mm skin top and bottom, thick side walls). The prongs are 2 mm tall so they fit inside.
# Each barb clicks into a blind pocket in a side wall (nothing visible from outside). Release = a firm pull: the back of each barb is a steep
# ramp (E_BACK short = steep = harder to pull out). Estimated hold ~10-20 N (very rough: print and test; adjust E_BACK, E_BARB_H).
E_ARM_W, E_ARM_OUT, E_ARM_Z = 1.7, 2.9, 2.0
E_TUNNEL_HALF = 3.1                  # tunnel 6.2 mm wide
E_TUNNEL_Z0, E_TUNNEL_Z1 = 0.8, 3.2  # tunnel 2.4 mm tall: 0.8 mm skin above and below
E_BARB_H = 1.0
E_LEAD, E_FLAT, E_BACK = 2.0, 1.0, 0.5
E_BARB_LEN = E_LEAD + E_FLAT + E_BACK
E_POCKET_DEPTH = 1.2                 # measured outward from the tunnel wall; the outer skin stays 2.2 mm thick
E_PL = 12.0


def male_end_enc(clr=0.35, side=0.3, tongue_on=True):
    body = link(clr, side, slot=False, with_tongue=tongue_on)
    z0 = (T - E_ARM_Z) / 2
    for s in (1, -1):
        y0, y1 = sorted((s * (E_ARM_OUT - E_ARM_W), s * E_ARM_OUT))
        arm = Pos(-E_PL / 2 + 0.25, (y0 + y1) / 2, T / 2) * Box(E_PL + 0.5, y1 - y0, E_ARM_Z)
        barb = _poly([(-E_PL, s * (E_ARM_OUT - 0.1)), (-E_PL + E_LEAD, s * (E_ARM_OUT + E_BARB_H)),
                      (-E_PL + E_LEAD + E_FLAT, s * (E_ARM_OUT + E_BARB_H)), (-E_PL + E_BARB_LEN, s * (E_ARM_OUT - 0.1))], z0, E_ARM_Z)
        body = body + arm + barb
    return body


def female_end_enc(clr=0.35, side=0.3, slot=True):
    body = link(clr, side, slot=slot, with_tongue=False, length=FEMALE_LEN)
    th = E_TUNNEL_Z1 - E_TUNNEL_Z0
    zc = (E_TUNNEL_Z0 + E_TUNNEL_Z1) / 2
    x0 = FEMALE_LEN - TUNNEL_DEPTH
    body = body - Pos(x0 + (TUNNEL_DEPTH + 1) / 2, 0, zc) * Box(TUNNEL_DEPTH + 1, 2 * E_TUNNEL_HALF, th)
    body = body - _poly([(FEMALE_LEN - 2.0, E_TUNNEL_HALF), (FEMALE_LEN + 0.1, E_TUNNEL_HALF + 1.2),
                         (FEMALE_LEN + 0.1, -E_TUNNEL_HALF - 1.2), (FEMALE_LEN - 2.0, -E_TUNNEL_HALF)], E_TUNNEL_Z0, th)   # lead-in funnel
    tip = FEMALE_LEN + BUTT_GAP - E_PL
    x_front, x_catch = tip - 0.3, tip + E_BARB_LEN + CATCH_PLAY
    for s in (1, -1):
        body = body - Pos((x_front + x_catch) / 2, s * (E_TUNNEL_HALF + E_POCKET_DEPTH / 2 - 0.05), zc) * Box(x_catch - x_front, E_POCKET_DEPTH + 0.1, th)
    return body


def closed_pair_enc(clr=0.35, side=0.3):
    female = female_end_enc(clr, side, slot=False)
    male = Pos(FEMALE_LEN + BUTT_GAP, 0, 0) * male_end_enc(clr, side)
    return female, male
