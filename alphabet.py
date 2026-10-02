"""The writing alphabet: every character is a short sequence of direction flicks, defined in alphabet.json."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHABET_FILE = os.path.join(HERE, "alphabet.json")

NAMES = ["u", "tr", "r", "br", "d", "bl", "l", "tl"]               # index = direction, 0 = up, clockwise
NAME_TO_DIR = {n: i for i, n in enumerate(NAMES)}
ARROWS = dict(zip(NAMES, "↑↗→↘↓↙←↖"))
LONG_NAMES = {"u": "up", "tr": "up-right", "r": "right", "br": "down-right",
              "d": "down", "bl": "down-left", "l": "left", "tl": "up-left"}


def load_entries(path=ALPHABET_FILE):
    """-> [(character, [sequence, ...])] in file order, each sequence a tuple of direction names.
    A character may list several sequences (all accepted). Raises ValueError on an unknown direction or when two
    entries share exactly the same sequence."""
    with open(path) as f:
        data = json.load(f)
    entries, used = [], {}
    for group in ("letters", "symbols"):
        for ch, seqs in data.get(group, {}).items():
            parsed = []
            for seq in ([seqs] if isinstance(seqs, str) else seqs):
                names = tuple(seq.split())
                bad = [n for n in names if n not in NAME_TO_DIR]
                if bad or not names:
                    raise ValueError(f"{ch!r}: unknown direction {bad or seq!r} (use {' '.join(NAMES)})")
                if names in used:
                    raise ValueError(f"{ch!r} and {used[names]!r} both use '{' '.join(names)}'")
                used[names] = ch
                parsed.append(names)
            entries.append((ch, parsed))
    return entries


def load_alphabet(path=ALPHABET_FILE):
    """-> {sequence tuple: character}."""
    return {names: ch for ch, seqs in load_entries(path) for names in seqs}


def arrows(names):
    return " ".join(ARROWS[n] for n in names)


def cheatsheet(path=ALPHABET_FILE):
    out = ["character  flicks, in order (lift your finger between flicks)", ""]
    for ch, seqs in load_entries(path):
        for i, names in enumerate(seqs):
            out.append(f"  {ch if i == 0 else ' '}        {arrows(names):<12}({' '.join(names)})"
                       + ("   also accepted" if i else ""))
    out += ["", "middle click = accept   left click = undo   right click = space   wheel = number 0-9 (then middle click)"]
    return "\n".join(out)
