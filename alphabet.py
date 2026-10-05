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


DEFAULT_PUNCTUATION = list(".,?!'\"-:;()/@&#$%+=*_")


def load_punctuation(path=ALPHABET_FILE):
    """The marks the wheel walks through (scroll down from rest). Edit the "punctuation" list in alphabet.json."""
    with open(path) as f:
        data = json.load(f)
    marks = data.get("punctuation", DEFAULT_PUNCTUATION)
    return [m for m in marks if isinstance(m, str) and len(m) == 1]


def near_collisions(entries):
    """Pairs of different characters whose sequences are one 45-degree slip apart (same length, one flick off by a step).
    A slip between them turns one valid letter into the other, so no correction can notice it."""
    flat = [(ch, tuple(NAME_TO_DIR[n] for n in seq)) for ch, seqs in entries for seq in seqs]
    out = []
    for i, (ca, a) in enumerate(flat):
        for cb, b in flat[i + 1:]:
            if ca != cb and len(a) == len(b):
                diffs = [(x, y) for x, y in zip(a, b) if x != y]
                if len(diffs) == 1 and min((diffs[0][0] - diffs[0][1]) % 8, (diffs[0][1] - diffs[0][0]) % 8) == 1:
                    out.append((ca, " ".join(NAMES[d] for d in a), cb, " ".join(NAMES[d] for d in b)))
    return out


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
    out += ["", "punctuation (wheel down from rest, middle click to insert): " + " ".join(load_punctuation(path))]
    out += ["middle click = accept   left click = undo   right click = space   wheel up = number 0-9 (then middle click)"]
    return "\n".join(out)
