"""Ring Writer: write with a D06 ring by flicking one direction per stroke. One letter at a time, no autocomplete.

Each letter is a short sequence of direction flicks (alphabet.json; see docs/GUIDE.md). Flick, lift, flick ... then
middle-click to accept the letter.

  middle click = accept the letter you drew (nothing drawn: accept the number or punctuation mark, else insert a space)
                 If your flicks spell no letter, the best guess is SUGGESTED (e.g. "W?"): nothing changes until you middle-click.
  left click   = undo the last flick (nothing drawn: backspace)
  right click  = space
  wheel up     = a number: from rest each tick up adds one (0-9), each tick down subtracts one; middle click accepts it
  wheel down   = punctuation: from rest, scroll down to walk through the marks (. , ? ! ...), up to go back; middle click inserts it

  python ring_writer.py --cheatsheet                     print the alphabet
  python ring_writer.py --check                          warn about letters that are one slip apart
  python ring_writer.py --raw ...                        type the stroke pictograms (↘↗↘↗) instead of letters
  python ring_writer.py --glyphs names ...               show flicks as names (br tr) instead of arrows (↘ ↗)
  python ring_writer.py --demo                           try it with the keyboard, no hardware
  python ring_writer.py --port /dev/cu.usbmodem1101 --calibrate     once
  python ring_writer.py --port /dev/cu.usbmodem1101

Keyboard stand-ins (also work with the ring): numpad keys 1-9 add a flick (8 = up, 6 = right, 3 = down-right ...),
Enter = accept, Backspace = undo, Space = space, + = wheel up, - = wheel down. Ctrl-C quits.
The serial port must be free (close any serial monitor). Notes are saved to notes/ after every change.
"""
import argparse
import datetime
import os
import select
import sys
import termios
import time
import tty

from alphabet import ALPHABET_FILE, ARROWS, NAMES, cheatsheet, load_alphabet, load_entries, load_punctuation, near_collisions
from flick import Flick, calibrate, load_calibration, open_port
import settings
from hid_report import LEFT, MIDDLE, RIGHT, parse, split_ts

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = os.path.join(HERE, "notes")
SENTENCE_END = (". ", "? ", "! ", "\n")
ATTACH = ".,?!:;)%"            # marks that stick to the word before them (no space in between)
KEYPAD = {"8": 0, "9": 1, "6": 2, "3": 3, "2": 4, "1": 5, "4": 6, "7": 7}   # numpad layout = direction index


class App:
    """The writer's state: the flicks drawn so far, the number selector, and the text."""

    def __init__(self, alphabet, notes_dir=NOTES_DIR, marks=None, suggest=True, raw=False):
        self.raw = raw                                 # raw mode: the text is the stroke pictograms, not decoded letters
        self.alpha, self.seq, self.num = alphabet, [], None
        self.alts = []                                 # per flick: its runner-up direction (or None)
        self.marks = list(marks) if marks else list(load_punctuation())
        self.punct = None                              # index of the mark the wheel is showing, or None
        self.suggest_on = suggest
        self.text, self.note = "", ""
        self.notes_dir, self.path, self.saved = notes_dir, None, ""

    def add(self, token, alt=None):
        self.seq.append(token)
        self.alts.append(alt)
        self.note = ""
        if self.raw:
            self.text += ARROWS[token]
            self._save()

    def exact(self):
        return self.alpha.get(tuple(self.seq))

    def more(self):
        """Characters the flicks so far could still become."""
        n = len(self.seq)
        found = [ch for names, ch in self.alpha.items() if len(names) > n and names[:n] == tuple(self.seq)]
        return list(dict.fromkeys(found))

    def suggest(self):
        """For flicks that spell no letter: ('W', 'angle'|'slip'|'edit') when one letter is the clear best guess,
        ('?', [letters]) when several tie, or None. Nothing is applied: accept() only uses it after your middle click.

        Evidence, strongest first (the first level with any match decides):
          angle - swapping one flick for its runner-up direction (it landed near a boundary) gives a letter
          slip  - any one flick off by 45 degrees gives a letter
          edit  - dropping one extra flick, or adding one missing flick (needs 3+ flicks), gives a letter"""
        seq = tuple(self.seq)
        if not self.suggest_on or len(seq) < 2 or seq in self.alpha:
            return None
        idx = {n: i for i, n in enumerate(NAMES)}
        levels = {"angle": [], "slip": [], "edit": []}
        for i, alt in enumerate(self.alts):
            if alt is not None and seq[:i] + (alt,) + seq[i + 1:] in self.alpha:
                levels["angle"].append(self.alpha[seq[:i] + (alt,) + seq[i + 1:]])
        for i, tok in enumerate(seq):
            for step in (1, -1):
                v = seq[:i] + (NAMES[(idx[tok] + step) % 8],) + seq[i + 1:]
                if v in self.alpha:
                    levels["slip"].append(self.alpha[v])
        if len(seq) >= 3:
            for i in range(len(seq)):
                if seq[:i] + seq[i + 1:] in self.alpha:
                    levels["edit"].append(self.alpha[seq[:i] + seq[i + 1:]])
            for i in range(len(seq) + 1):
                for n in NAMES:
                    if seq[:i] + (n,) + seq[i:] in self.alpha:
                        levels["edit"].append(self.alpha[seq[:i] + (n,) + seq[i:]])
        for kind in ("angle", "slip", "edit"):
            found = list(dict.fromkeys(levels[kind]))
            if found:
                return (found[0], kind) if len(found) == 1 else ("?", found)
        return None

    def _log_fix(self, flicks, ch, kind):
        """Keep a record of approved corrections, so the thresholds can be tuned on real data."""
        os.makedirs(self.notes_dir, exist_ok=True)
        with open(os.path.join(self.notes_dir, "corrections.log"), "a") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')}\t{flicks}\t{ch}\t{kind}\n")

    def _put(self, ch):
        if ch.isalpha() and (not self.text or self.text.endswith(SENTENCE_END)):
            ch = ch.upper()
        elif ch.isalpha():
            ch = ch.lower()
        elif ch in ATTACH and self.text.endswith(" "):
            self.text = self.text[:-1]                 # punctuation sticks to the word before it
        self.text += ch
        self.note = f"+ {ch}"
        self._save()

    def accept(self):
        if self.seq and self.raw:                      # raw mode: keep the arrows, say what they would decode to, mark the letter boundary
            ch = self.exact()
            if ch is None:
                s = self.suggest()
                ch = f"{s[0]}?" if s and s[0] != "?" else "?"
            self.seq, self.alts = [], []
            self.text += " "
            self.note = f"= {ch}"
            self._save()
        elif self.seq:
            ch, fixed = self.exact(), None
            if ch is None:
                s = self.suggest()
                if s is None:
                    self.note = "no such letter"
                    return
                if s[0] == "?":
                    self.note = "unsure: " + " ".join(s[1])
                    return
                ch, fixed = s
            flicks = " ".join(self.seq)
            self.seq, self.alts = [], []
            self._put(ch)
            if fixed:
                self.note = f"+ {ch} (fixed)"
                self._log_fix(flicks, ch, fixed)
        elif self.num is not None:
            n, self.num = self.num, None
            self._put(str(n))
        elif self.punct is not None:
            mark, self.punct = self.marks[self.punct], None
            self._put(mark)
        else:
            self.space()

    def space(self):
        if self.seq:
            self.note = "finish or undo the letter"
            return
        self.num = self.punct = None
        self.text += " "
        self.note = "+ space"
        self._save()

    def undo(self):
        if self.seq:
            self.seq.pop()
            if self.alts:
                self.alts.pop()
            if self.raw:
                self.text = self.text[:-1]
                self._save()
        elif self.num is not None:
            self.num = None
            self.note = "number cancelled"
        elif self.punct is not None:
            self.punct = None
            self.note = "mark cancelled"
        else:
            self.text = self.text[:-1]
            self.note = "backspace"
            self._save()

    def wheel(self, step):
        """step > 0 = wheel up, step < 0 = wheel down. From rest, up starts a number (0-9) and down starts punctuation.
        In a number: up adds, down subtracts. In punctuation: down goes to the next mark (wrapping), up goes back and
        cancels when it goes back past the first mark."""
        if self.num is not None:
            self.num = max(0, min(9, self.num + step))
        elif self.punct is not None:
            if step < 0:
                self.punct = (self.punct + 1) % len(self.marks)
            else:
                self.punct = None if self.punct == 0 else self.punct - 1
        elif step > 0:
            self.num = min(9, step)
        elif self.marks:
            self.punct = 0

    def _save(self):
        """Rewrite the current note file after every change, so nothing is lost if the power dies."""
        if not self.text or self.text == self.saved:
            return
        if self.path is None:
            os.makedirs(self.notes_dir, exist_ok=True)
            self.path = os.path.join(self.notes_dir, datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".txt")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(self.text)
        self.saved = self.text

    def render(self, cols=21, rows=4, glyphs="names"):
        """What a tiny cols x rows character display shows (21x4 = a 128x32 OLED with a 6x8 font).
        glyphs="names" is plain ASCII (br tr); glyphs="arrows" draws the pictograms (↘ ↗) for a terminal."""
        show = (lambda toks: " ".join(ARROWS[t] for t in toks)) if glyphs == "arrows" else (lambda toks: " ".join(toks))
        seq = self.seq
        text = (self.text.replace("\n", "|") + "_")[-cols:]
        tag = "ABC"
        if seq:
            ch = self.alpha.get(tuple(seq))
            row2 = show(seq) + f" ={ch if ch else '?'}"
            hint = "more " + "".join(self.more())[:cols - 9]
            sug = None if ch else self.suggest()
            if sug:
                tag = "FIX"
                if sug[0] == "?":
                    hint = "/".join(sug[1])[:cols - 5] + "?"
                else:
                    pic = ""
                    if glyphs == "arrows":                       # also draw the guessed letter's pictogram
                        pic = " " + "".join(ARROWS[t] for t in next(k for k, v in self.alpha.items() if v == sug[0]))
                    hint = f"~{sug[0]}?{pic} mid=ok"
                    if len(hint) > cols - 4:
                        hint = f"~{sug[0]}?{pic} ok"
        elif self.num is not None:
            row2, hint, tag = f"number: {self.num}", "mid=accept", "NUM"
        elif self.punct is not None:
            lo = max(0, self.punct - 2)
            row2 = " ".join(f"[{m}]" if i == self.punct else m for i, m in enumerate(self.marks[lo:self.punct + 5], lo))
            hint, tag = "down=next up=back", "SYM"
        else:
            row2, hint = "draw a letter", ""
        lines = [text, row2, f"{hint[:cols - 4]:<{cols - 4}} {tag}", self.note or "mid=ok L=undo R=space"]
        edge = "+" + "-" * cols + "+"
        return "\n".join([edge] + ["|" + ln[:cols].ljust(cols) + "|" for ln in lines[:rows]] + [edge])


def alt_name(det):
    """The runner-up direction of the flick the detector just finished, as a name (or None)."""
    return NAMES[det.last_alt] if det.last_alt is not None else None


def live(args):
    app = App(load_alphabet(args.alphabet), args.notes_dir, load_punctuation(args.alphabet), suggest=not args.no_suggest, raw=args.raw)
    cal = load_calibration()
    det = Flick(args.min_flick, cal["rot"], cal["gy"], args.gap, lockout=args.lockout, soft=args.soft_angle)
    cols, rows = (int(v) for v in args.screen.lower().split("x"))
    sign = -1 if args.flip else 1
    ser = None if args.demo else open_port(args.port)
    buf, prev_btn, last = b"", 0, {LEFT: 0.0, RIGHT: 0.0, MIDDLE: 0.0}
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    dirty = True
    try:
        while True:
            r, _, _ = select.select([ser, sys.stdin] if ser else [sys.stdin], [], [], 0.01)      # how often a finished flick is noticed
            now = time.time()
            if ser in r:
                buf += ser.read(4096)
                *lines, buf = buf.split(b"\n")
                for line in lines:
                    p = parse(split_ts(line.decode(errors="replace"))[1])
                    if not p:
                        continue
                    btn, dx, dy, wheel = p
                    for bit, action in ((LEFT, app.undo), (MIDDLE, app.accept), (RIGHT, app.space)):
                        if btn & bit and not prev_btn & bit and now - last[bit] > args.debounce:
                            last[bit] = now
                            d = det.poll(now + 1)              # a click ends a flick that is still being counted
                            if d is not None:
                                app.add(NAMES[d], alt_name(det))
                            action()
                            det.click(now)
                    if wheel:
                        app.wheel(sign * (1 if wheel < 0 else -1))
                        det.click(now)
                    elif (dx or dy) and not btn:
                        d = det.feed(dx, dy, now)
                        if d is not None:
                            app.add(NAMES[d], alt_name(det))
                    prev_btn = btn
                    dirty = True
            d = det.poll(now)
            if d is not None:
                app.add(NAMES[d], alt_name(det))
                dirty = True
            if sys.stdin in r:
                chunk = os.read(fd, 64).decode(errors="ignore")    # several keys can arrive at once
                if "\x03" in chunk:
                    break
                for ch in chunk:
                    if ch in KEYPAD:
                        app.add(NAMES[KEYPAD[ch]])
                    elif ch in ("\r", "\n"):
                        app.accept()
                    elif ch in ("\x7f", "\b"):
                        app.undo()
                    elif ch == " ":
                        app.space()
                    elif ch in "+=":
                        app.wheel(1)
                    elif ch == "-":
                        app.wheel(-1)
                dirty = True
            if dirty:
                sys.stdout.write("\x1b[H\x1b[J" + app.render(cols, rows, args.glyphs) + "\n")
                sys.stdout.flush()
                dirty = False
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def build_parser(saved=None):
    """The command line. `saved` (from settings.json) supplies defaults for port, min_flick, gap, lockout and debounce."""
    ap = argparse.ArgumentParser(description="Write with a D06 ring: one direction flick per stroke.")
    ap.add_argument("--port", help="serial port of the ESP32, e.g. /dev/cu.usbmodem1101")
    ap.add_argument("--demo", action="store_true", help="no hardware: use the keyboard stand-ins")
    ap.add_argument("--cheatsheet", action="store_true", help="print the alphabet and exit")
    ap.add_argument("--calibrate", action="store_true", help="measure the pad's rotation and stretch, then exit")
    ap.add_argument("--alphabet", default=ALPHABET_FILE, help="alphabet file (default alphabet.json)")
    ap.add_argument("--min-flick", type=float, default=100, help="shortest flick that counts, in ring units (smaller = more sensitive)")
    ap.add_argument("--gap", type=float, default=0.12, help="pause (s) that counts as lifting your finger: smaller = faster response, but too small can split one flick into two")
    ap.add_argument("--lockout", type=float, default=0.35, help="seconds the pad is ignored after a click or wheel tick (a click jiggles the pad); smaller = the next letter can start sooner")
    ap.add_argument("--measure", action="store_true", help="measure your ring's report rate and click jiggle (about 40 s), then suggest --gap and --lockout")
    ap.add_argument("--flip", action="store_true", help="reverse the wheel (swaps which direction counts numbers and which walks punctuation)")
    ap.add_argument("--glyphs", choices=["arrows", "names"], default="arrows",
                    help="how flicks are drawn on screen: arrows (↘ ↗, for a terminal) or names (br tr, plain ASCII for a small display)")
    ap.add_argument("--raw", action="store_true",
                    help="type the stroke pictograms instead of letters (middle click ends a letter and shows what it would decode to)")
    ap.add_argument("--no-suggest", action="store_true", help="turn the correction suggestions off")
    ap.add_argument("--soft-angle", type=float, default=12.0,
                    help="a flick this many degrees from the centre of its direction also remembers the neighbouring one as a runner-up (smaller = more runner-ups)")
    ap.add_argument("--check", action="store_true", help="list pairs of letters that are one slip apart, then exit")
    ap.add_argument("--screen", default="21x4", help="size of the small display in characters, e.g. 21x4")
    ap.add_argument("--debounce", type=float, default=0.25, help="shortest time (s) between two presses of the same button; --measure saw no double events, so it can be small")
    ap.add_argument("--notes-dir", default=NOTES_DIR, help="where notes are saved")
    if saved:
        ap.set_defaults(**saved)
    return ap


def main():
    ap = build_parser(settings.load())
    a = ap.parse_args()
    if a.cheatsheet:
        print(cheatsheet(a.alphabet))
    elif a.check:
        pairs = near_collisions(load_entries(a.alphabet))
        for ca, sa, cb, sb in pairs:
            print(f"{ca} ({sa})  vs  {cb} ({sb}): one flick off by 45 degrees turns one into the other")
        print(f"{len(pairs)} close pair(s)." if pairs else "no letters are one slip apart.")
    elif a.measure:
        if not a.port:
            ap.error("--measure needs --port")
        import measure
        measure.run(a.port)
    elif a.calibrate:
        if not a.port:
            ap.error("--calibrate needs --port")
        calibrate(a.port)
    elif a.port or a.demo:
        live(a)
    else:
        ap.error("give --port PORT (or --demo, or --cheatsheet)")


if __name__ == "__main__":
    main()
