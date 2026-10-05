"""Tiny software renderer: draws build123d shapes with matplotlib, so layouts can be checked without a CAD program."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
from matplotlib.colors import to_rgb                  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402


def _triangles(shape, tol=0.05):
    verts, tris = shape.tessellate(tol)
    v = np.array([[p.X, p.Y, p.Z] for p in verts])
    return v[np.array(tris)]                          # (n, 3 corners, 3 coords)


def _shade(tri, colour, alpha):
    light = np.array([0.4, -0.5, 0.8])
    light /= np.linalg.norm(light)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    k = 0.45 + 0.55 * np.abs(n @ light)
    return [(*(np.array(to_rgb(colour)) * s), alpha) for s in k]


def _view2d(ax, tris, axes, depth_axis, title, flip_depth=False):
    """Orthographic view: project onto two axes, draw far triangles first."""
    polys = []
    for t, colour, alpha in tris:
        if alpha < 0.3:                                # the case envelope: outline only, drawn separately below
            continue
        depth = t[:, :, depth_axis].mean(axis=1)
        order = np.argsort(depth if not flip_depth else -depth)
        shade = _shade(t, colour, alpha)
        for i in order:
            polys.append((depth[i] * (-1 if flip_depth else 1), t[i][:, list(axes)], shade[i]))
    polys.sort(key=lambda p: p[0])
    ax.add_collection(PolyCollection([p[1] for p in polys], facecolors=[p[2] for p in polys],
                                     edgecolors=(0, 0, 0, 0.15), linewidths=0.2))
    for t, colour, alpha in tris:
        if alpha < 0.3:
            pts = t.reshape(-1, 3)[:, list(axes)]
            lo, hi = pts.min(axis=0), pts.max(axis=0)
            ax.add_patch(plt.Rectangle(lo, *(hi - lo), fill=False, edgecolor="#666666", linestyle="--", linewidth=1.2))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_xlabel("xyz"[axes[0]] + " (mm)")
    ax.set_ylabel("xyz"[axes[1]] + " (mm)")


def render(items, path, size=5.4):
    """items: [(shape, colour, alpha)]; alpha < 0.3 marks the case envelope. One PNG: isometric, top, front."""
    tris = [(_triangles(s), c, a) for s, c, a in items]
    allv = np.concatenate([t.reshape(-1, 3) for t, _, _ in tris])
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    mid, half = (lo + hi) / 2, (hi - lo).max() / 2 * 1.05
    fig = plt.figure(figsize=(size * 3, size))
    ax = fig.add_subplot(1, 3, 1, projection="3d")
    for t, c, a in tris:
        edge = (0, 0, 0, 0.0) if a < 0.3 else (0, 0, 0, 0.25)
        ax.add_collection3d(Poly3DCollection(t, facecolors=_shade(t, c, a * (0.0 if a < 0.3 else 1)), edgecolors=edge, linewidths=0.3))
    # case envelope as 12 wire edges
    for t, c, a in tris:
        if a < 0.3:
            l, h = t.reshape(-1, 3).min(axis=0), t.reshape(-1, 3).max(axis=0)
            for i in (0, 1):
                for j in (0, 1):
                    for k, (p, q) in enumerate((((l[0], (l, h)[i][1], (l, h)[j][2]), (h[0], (l, h)[i][1], (l, h)[j][2])),
                                                (((l, h)[i][0], l[1], (l, h)[j][2]), ((l, h)[i][0], h[1], (l, h)[j][2])),
                                                (((l, h)[i][0], (l, h)[j][1], l[2]), ((l, h)[i][0], (l, h)[j][1], h[2])))):
                        ax.plot(*zip(p, q), color="#666666", linewidth=0.9)
    ax.set_xlim(mid[0] - half, mid[0] + half)
    ax.set_ylim(mid[1] - half, mid[1] + half)
    ax.set_zlim(mid[2] - half, mid[2] + half)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=28, azim=-55)
    ax.set_title("isometric")
    ax.set_xlabel("x along wrist")
    ax.set_ylabel("y across")
    ax.set_zlabel("z up")
    ax.grid(False)
    _view2d(fig.add_subplot(1, 3, 2), tris, (0, 1), 2, "top view (looking down at the display side)")
    _view2d(fig.add_subplot(1, 3, 3), tris, (0, 2), 1, "side view (z = height above the skin)", flip_depth=True)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
