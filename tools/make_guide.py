"""Build docs/GUIDE.md and docs/alphabet.svg from alphabet.json, so the reference guide never drifts from the alphabet.

    python tools/make_guide.py [--alphabet alphabet.json] [--out docs]
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from alphabet import ALPHABET_FILE, ARROWS, LONG_NAMES, NAME_TO_DIR, NAMES, arrows, load_entries   # noqa: E402

CELL_W, GAP, MARGIN, COLS = 214, 10, 24, 4
CHIP = 28
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
INK, MUTED, ACCENT, PAPER, CARD, LINE = "#1f2328", "#59636e", "#0969da", "#ffffff", "#f6f8fa", "#d0d7de"


def chip(x, y, name, color=ACCENT):
    """A small square with an arrow in it, pointing in direction `name`."""
    ang = math.radians(NAME_TO_DIR[name] * 45)
    dx, dy = math.sin(ang), -math.cos(ang)
    cx, cy = x + CHIP / 2, y + CHIP / 2
    sx, sy, ex, ey = cx - 8 * dx, cy - 8 * dy, cx + 9 * dx, cy + 9 * dy
    bx, by, px, py = ex - 7 * dx, ey - 7 * dy, -dy, dx
    head = f"{ex:.1f},{ey:.1f} {bx + 4.5 * px:.1f},{by + 4.5 * py:.1f} {bx - 4.5 * px:.1f},{by - 4.5 * py:.1f}"
    return (f'<rect x="{x}" y="{y}" width="{CHIP}" height="{CHIP}" rx="6" fill="{PAPER}" stroke="{LINE}"/>'
            f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
            f'<polygon points="{head}" fill="{color}"/>')


def make_svg(entries):
    cell_h = lambda ch_seqs: 20 + 36 * len(ch_seqs[1])
    rows = [entries[i:i + COLS] for i in range(0, len(entries), COLS)]
    header, footer = 150, 100
    body = sum(max(cell_h(e) for e in row) + GAP for row in rows)
    width = MARGIN * 2 + COLS * CELL_W + (COLS - 1) * GAP
    height = header + body + footer
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'font-family="{FONT}">',
           f'<rect width="{width}" height="{height}" fill="{PAPER}"/>',
           f'<text x="{MARGIN}" y="52" font-size="30" font-weight="700" fill="{INK}">Ring Writer alphabet</text>',
           f'<text x="{MARGIN}" y="82" font-size="15" fill="{MUTED}">Flick one direction, lift your finger, flick the next.</text>',
           f'<text x="{MARGIN}" y="104" font-size="15" fill="{MUTED}">Then middle-click to accept the letter.</text>',
           f'<text x="{MARGIN}" y="126" font-size="13" fill="{MUTED}">Gray arrows = also-accepted alternative.</text>']
    # compass legend: the eight directions and their codes
    gx, gy = width - MARGIN - 3 * 74, 18
    layout = [["tl", "u", "tr"], ["l", None, "r"], ["bl", "d", "br"]]
    for r, line in enumerate(layout):
        for c, name in enumerate(line):
            x, y = gx + c * 74, gy + r * 38
            if name:
                out.append(chip(x, y, name))
                out.append(f'<text x="{x + CHIP + 5}" y="{y + 19}" font-size="14" fill="{INK}">{name}</text>')
            else:
                out.append(f'<circle cx="{x + CHIP / 2}" cy="{y + CHIP / 2}" r="3" fill="{MUTED}"/>')
    y = header
    for row in rows:
        h = max(cell_h(e) for e in row)
        for c, (ch, seqs) in enumerate(row):
            x = MARGIN + c * (CELL_W + GAP)
            out.append(f'<rect x="{x}" y="{y}" width="{CELL_W}" height="{h}" rx="10" fill="{CARD}" stroke="{LINE}"/>')
            esc = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}.get(ch, ch)
            out.append(f'<text x="{x + 16}" y="{y + h / 2 + 12}" font-size="34" font-weight="700" fill="{INK}">{esc}</text>')
            for i, names in enumerate(seqs):
                for k, name in enumerate(names):
                    out.append(chip(x + 56 + k * (CHIP + 3), y + 12 + i * 36, name, ACCENT if i == 0 else MUTED))
        y += h + GAP
    controls = ["middle click = accept the letter (nothing drawn: accept the number, else space)",
                "left click = undo the last flick (nothing drawn: backspace)     right click = space",
                "wheel = number 0-9: up adds one, down subtracts one; middle click accepts it"]
    for i, line in enumerate(controls):
        out.append(f'<text x="{MARGIN}" y="{y + 30 + i * 22}" font-size="13.5" fill="{MUTED}">{line}</text>')
    out.append("</svg>")
    return "\n".join(out)


def make_markdown(entries):
    seqs_of = {ch: s for ch, s in entries}
    lines = ["# Ring Writer reference guide", "",
             "*Generated from `alphabet.json` by `tools/make_guide.py`. Edit the alphabet, then run the script again.*", "",
             "![Alphabet cheat sheet](alphabet.svg)", "",
             "## The eight flicks", "",
             "```", "  ↖ tl     ↑ u     ↗ tr", "  ← l      ·      → r", "  ↙ bl     ↓ d     ↘ br", "```", "",
             "## Writing a letter", "",
             "1. Flick the pad in the first direction, then lift your finger.",
             "2. Flick the next direction, lift, and so on until the letter is spelled.",
             "3. **Middle click** to accept it. The screen shows what you have drawn so far (for example `d r =L`) and which",
             "   letters it could still become, so you can check before you accept.",
             "4. Made a mistake? **Left click** undoes the last flick. With nothing drawn it deletes a character.", "",
             "Every flick is separate: the pause when you lift is what lets the same direction repeat (`d d r`).", "",
             "## Letters", "", "| Letter | Flicks | Codes |", "|:--:|:--|:--|"]
    for ch, seqs in entries:
        if ch.isalpha():
            lines.append(f"| **{ch}** | " + "<br>".join(arrows(s) for s in seqs) + " | "
                         + "<br>".join("`" + " ".join(s) + "`" for s in seqs) + " |")
    lines += ["", "## Symbols", "", "| Symbol | Flick | Code |", "|:--:|:--|:--|"]
    for ch, seqs in entries:
        if not ch.isalpha():
            lines.append(f"| `{ch}` | " + "<br>".join(arrows(s) for s in seqs) + " | "
                         + "<br>".join("`" + " ".join(s) + "`" for s in seqs) + " |")
    lines += ["", "Punctuation sticks to the word before it. The first letter of the text, and the first after `. ? !`, is a capital.", ""]
    # letters whose sequence is the start of another one
    overlaps = []
    for ch, seqs in entries:
        for s in seqs:
            longer = [c for c, ss in entries for t in ss if len(t) > len(s) and t[:len(s)] == s and c != ch]
            if longer and ch.isalpha():
                overlaps.append(f"- `{' '.join(s)}` ({arrows(s)}) is **{ch}**, and also the start of "
                                + ", ".join(sorted(dict.fromkeys(longer))))
    if overlaps:
        lines += ["## Letters that start other letters", "",
                  "You accept a letter yourself, so this is safe: just keep flicking for the longer one, or middle click to take the shorter.", ""]
        lines += overlaps + [""]
    lines += ["## Numbers and spaces", "",
              "- **Wheel**: each tick up adds one, each tick down subtracts one (0 to 9). **Middle click** accepts the number as a character.",
              "- **Right click** inserts a space. Middle click with nothing drawn and no number selected also inserts one.", "",
              "## Buttons at a glance", "",
              "| Control | Does |", "|:--|:--|",
              "| Flick | adds a direction to the letter |",
              "| Middle click | accepts the letter, else the number, else a space |",
              "| Left click | undoes the last flick, else backspace |",
              "| Right click | space |",
              "| Wheel | number 0-9 |", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alphabet", default=ALPHABET_FILE)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs"))
    a = ap.parse_args()
    entries = load_entries(a.alphabet)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "alphabet.svg"), "w") as f:
        f.write(make_svg(entries))
    with open(os.path.join(a.out, "GUIDE.md"), "w") as f:
        f.write(make_markdown(entries))
    print(f"wrote {a.out}/GUIDE.md and alphabet.svg ({len(entries)} characters)")


if __name__ == "__main__":
    main()
