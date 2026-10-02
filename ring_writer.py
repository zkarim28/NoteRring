"""Ring Writer: write with a D06 ring by flicking one direction per stroke. One letter at a time, no autocomplete.

Each letter is a short sequence of direction flicks (alphabet.json; see docs/GUIDE.md). Flick, lift, flick ... then
middle-click to accept the letter.

  middle click = accept the letter you drew (nothing drawn: accept the number, else insert a space)
  left click   = undo the last flick (nothing drawn: backspace)
  right click  = space
  wheel        = number 0-9: each tick up adds one, each tick down subtracts one; middle click accepts it

  python ring_writer.py --cheatsheet                     print the alphabet
  python ring_writer.py --demo                           try it with the keyboard, no hardware
  python ring_writer.py --port /dev/cu.usbmodem1101 --calibrate     once
  python ring_writer.py --port /dev/cu.usbmodem1101

Keyboard stand-ins (also work with the ring): numpad keys 1-9 add a flick (8 = up, 6 = right, 3 = down-right ...),
Enter = accept, Backspace = undo, Space = space, + and - = number. Ctrl-C quits.
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

from alphabet import ALPHABET_FILE, NAMES, cheatsheet, load_alphabet
from flick import Flick, calibrate, load_calibration, open_port
from hid_report import LEFT, MIDDLE, RIGHT, parse, split_ts

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = os.path.join(HERE, "notes")
SENTENCE_END = (". ", "? ", "! ", "\n")
KEYPAD = {"8": 0, "9": 1, "6": 2, "3": 3, "2": 4, "1": 5, "4": 6, "7": 7}   # numpad layout = direction index


class App:
    """The writer's state: the flicks drawn so far, the number selector, and the text."""

    def __init__(self, alphabet, notes_dir=NOTES_DIR):
        self.alpha, self.seq, self.num = alphabet, [], None
        self.text, self.note = "", ""
        self.notes_dir, self.path, self.saved = notes_dir, None, ""

    def add(self, token):
        self.seq.append(token)
        self.note = ""

    def exact(self):
        return self.alpha.get(tuple(self.seq))

    def more(self):
        """Characters the flicks so far could still become."""
        n = len(self.seq)
        found = [ch for names, ch in self.alpha.items() if len(names) > n and names[:n] == tuple(self.seq)]
        return list(dict.fromkeys(found))

    def _put(self, ch):
        if ch.isalpha() and (not self.text or self.text.endswith(SENTENCE_END)):
            ch = ch.upper()
        elif ch.isalpha():
            ch = ch.lower()
        elif ch in ".,?!" and self.text.endswith(" "):
            self.text = self.text[:-1]                 # punctuation sticks to the word before it
        self.text += ch
        self.note = f"+ {ch}"
        self._save()

    def accept(self):
        if self.seq:
            ch = self.exact()
            if ch is None:
                self.note = "no such letter"
                return
            self.seq = []
            self._put(ch)
        elif self.num is not None:
            n, self.num = self.num, None
            self._put(str(n))
        else:
            self.space()

    def space(self):
        if self.seq:
            self.note = "finish or undo the letter"
            return
        self.text += " "
        self.note = "+ space"
        self._save()

    def undo(self):
        if self.seq:
            self.seq.pop()
        elif self.num is not None:
            self.num = None
            self.note = "number cancelled"
        else:
            self.text = self.text[:-1]
            self.note = "backspace"
            self._save()

    def wheel(self, step):
        self.num = max(0, min(9, (0 if self.num is None else self.num) + step))

    def _save(self):
        """Rewrite the current note file after every change, so nothing is lost if the power dies."""
        if not self.text or self.text == self.saved:
            return
        if self.path is None:
            os.makedirs(self.notes_dir, exist_ok=True)
            self.path = os.path.join(self.notes_dir, datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".txt")
        with open(self.path, "w") as f:
            f.write(self.text)
        self.saved = self.text

    def render(self, cols=21, rows=4):
        """What a tiny cols x rows character display shows (21x4 = a 128x32 OLED with a 6x8 font). Plain ASCII."""
        seq = self.seq
        text = (self.text.replace("\n", "|") + "_")[-cols:]
        if seq:
            ch = self.alpha.get(tuple(seq))
            row2 = " ".join(seq) + f" ={ch if ch else '?'}"
            hint = "more " + "".join(self.more())[:cols - 9]
        elif self.num is not None:
            row2, hint = f"number: {self.num}", "mid=accept"
        else:
            row2, hint = "draw a letter", ""
        tag = "NUM" if self.num is not None and not seq else "ABC"
        lines = [text, row2, f"{hint[:cols - 4]:<{cols - 4}} {tag}", self.note or "mid=ok L=undo R=space"]
        edge = "+" + "-" * cols + "+"
        return "\n".join([edge] + ["|" + ln[:cols].ljust(cols) + "|" for ln in lines[:rows]] + [edge])


def live(args):
    app = App(load_alphabet(args.alphabet), args.notes_dir)
    cal = load_calibration()
    det = Flick(args.min_flick, cal["rot"], cal["gy"], args.gap)
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
            r, _, _ = select.select([ser, sys.stdin] if ser else [sys.stdin], [], [], 0.04)
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
                        if btn & bit and not prev_btn & bit and now - last[bit] > 0.25:
                            last[bit] = now
                            d = det.poll(now + 1)              # a click ends a flick that is still being counted
                            if d is not None:
                                app.add(NAMES[d])
                            action()
                            det.click(now)
                    if wheel:
                        app.wheel(sign * (1 if wheel < 0 else -1))
                        det.click(now)
                    elif (dx or dy) and not btn:
                        d = det.feed(dx, dy, now)
                        if d is not None:
                            app.add(NAMES[d])
                    prev_btn = btn
                    dirty = True
            d = det.poll(now)
            if d is not None:
                app.add(NAMES[d])
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
                sys.stdout.write("\x1b[H\x1b[J" + app.render(cols, rows) + "\n")
                sys.stdout.flush()
                dirty = False
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    ap = argparse.ArgumentParser(description="Write with a D06 ring: one direction flick per stroke.")
    ap.add_argument("--port", help="serial port of the ESP32, e.g. /dev/cu.usbmodem1101")
    ap.add_argument("--demo", action="store_true", help="no hardware: use the keyboard stand-ins")
    ap.add_argument("--cheatsheet", action="store_true", help="print the alphabet and exit")
    ap.add_argument("--calibrate", action="store_true", help="measure the pad's rotation and stretch, then exit")
    ap.add_argument("--alphabet", default=ALPHABET_FILE, help="alphabet file (default alphabet.json)")
    ap.add_argument("--min-flick", type=float, default=100, help="shortest flick that counts, in ring units (smaller = more sensitive)")
    ap.add_argument("--gap", type=float, default=0.12, help="pause (s) that counts as lifting your finger")
    ap.add_argument("--flip", action="store_true", help="reverse the wheel (which way adds to the number)")
    ap.add_argument("--screen", default="21x4", help="size of the small display in characters, e.g. 21x4")
    ap.add_argument("--notes-dir", default=NOTES_DIR, help="where notes are saved")
    a = ap.parse_args()
    if a.cheatsheet:
        print(cheatsheet(a.alphabet))
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
