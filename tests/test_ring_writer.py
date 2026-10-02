"""Run with:  python -m unittest discover -s tests -v   (no hardware, no extra packages)"""
import json
import math
import os
import sys
import tempfile
import unittest
import xml.dom.minidom

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import alphabet as al                      # noqa: E402
import make_guide                          # noqa: E402
from flick import Flick                    # noqa: E402
from hid_report import parse, split_ts     # noqa: E402
from ring_writer import App                # noqa: E402


def writer():
    return App(al.load_alphabet(), tempfile.mkdtemp())


def draw(app, ch):
    """Write one character the way the user does: its flicks, then middle click."""
    entries = dict(al.load_entries())
    app.seq = list(entries[ch][0])
    app.accept()


class AlphabetTests(unittest.TestCase):
    def test_every_letter_has_a_sequence(self):
        chars = {ch for ch, _ in al.load_entries()}
        self.assertTrue(set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") <= chars)

    def test_sequences_are_unique(self):
        table = al.load_alphabet()
        total = sum(len(s) for _, s in al.load_entries())
        self.assertEqual(len(table), total)

    def test_alternate_sequences(self):
        t = al.load_alphabet()
        for letter, seqs in {"A": ["bl br r", "bl br l"], "H": ["d d r", "d r d"],
                             "J": ["r d tl", "r l d tl"], "S": ["tl bl br bl tl", "l d r d l"]}.items():
            for s in seqs:
                self.assertEqual(t[tuple(s.split())], letter, (letter, s))

    def test_duplicate_sequence_rejected(self):
        d = {"letters": {"A": "u d", "B": "u d"}}
        p = os.path.join(tempfile.mkdtemp(), "a.json")
        with open(p, "w") as f:
            json.dump(d, f)
        with self.assertRaises(ValueError):
            al.load_alphabet(p)

    def test_unknown_direction_rejected(self):
        p = os.path.join(tempfile.mkdtemp(), "a.json")
        with open(p, "w") as f:
            json.dump({"letters": {"A": "u sideways"}}, f)
        with self.assertRaises(ValueError):
            al.load_alphabet(p)


class FlickTests(unittest.TestCase):
    def burst(self, det, deg, mag=300, t0=0.0, n=5):
        a = math.radians(deg)
        for i in range(n):
            det.feed(mag / n * math.sin(a), -mag / n * math.cos(a), t0 + i * 0.02)
        return det.poll(t0 + 1.0)

    def test_eight_directions(self):
        det = Flick(100)
        got = [self.burst(det, d * 45, t0=d * 2.0) for d in range(8)]
        self.assertEqual(got, list(range(8)))

    def test_tolerates_wobble(self):
        det = Flick(100)
        for i, deg in enumerate((-18, 18, 27, 63)):
            expected = 0 if abs(deg) < 22 else 1
            self.assertEqual(self.burst(det, deg, t0=i * 2.0), expected)

    def test_short_flick_ignored(self):
        self.assertIsNone(self.burst(Flick(100), 90, mag=40))

    def test_calibration_corrects_a_rotated_squashed_pad(self):
        raw, cal = Flick(50), Flick(50, rot=0.2493, gy=1.856)     # a pad rotated ~14 degrees, vertically squashed 2x
        def make(deg):
            a = math.radians(deg + 12)
            return 300 * math.sin(a), -300 * math.cos(a) * 0.5
        def run(det):
            out = []
            for d in range(8):
                x, y = make(d * 45)
                for i in range(5):
                    det.feed(x / 5, y / 5, d * 2.0 + i * 0.02)
                out.append(det.poll(d * 2.0 + 1.0))
            return out
        self.assertEqual(run(cal), list(range(8)))
        self.assertNotEqual(run(raw), list(range(8)))

    def test_click_lockout(self):
        det = Flick(100)
        det.click(10.0)
        det.feed(300, 0, 10.1)                                    # inside the lockout: ignored
        self.assertIsNone(det.poll(12.0))


class WriterTests(unittest.TestCase):
    def test_hello(self):
        app = writer()
        for ch in "HELLO":
            draw(app, ch)
        self.assertEqual(app.text, "Hello")

    def test_capital_after_sentence_end_and_attached_punctuation(self):
        app = writer()
        draw(app, "H"); draw(app, "I"); draw(app, ".")
        self.assertEqual(app.text, "Hi.")
        app.space(); draw(app, "A")
        self.assertEqual(app.text, "Hi. A")

    def test_unknown_sequence_keeps_flicks(self):
        app = writer()
        app.seq = ["d", "u", "d", "u", "d", "u"]
        app.accept()
        self.assertEqual((app.text, app.note), ("", "no such letter"))
        self.assertEqual(len(app.seq), 6)

    def test_undo_flick_then_backspace(self):
        app = writer()
        draw(app, "H"); draw(app, "I")
        app.seq = ["d", "l"]
        app.undo()
        self.assertEqual(app.seq, ["d"])
        app.seq = []
        app.undo()
        self.assertEqual(app.text, "H")

    def test_number_selector(self):
        app = writer()
        for _ in range(3):
            app.wheel(1)
        app.wheel(-1)
        self.assertEqual(app.num, 2)
        app.accept()
        self.assertEqual((app.text, app.num), ("2", None))
        app.wheel(-1)                                             # clamps at 0 and activates the selector
        self.assertEqual(app.num, 0)
        for _ in range(20):
            app.wheel(1)
        self.assertEqual(app.num, 9)
        app.undo()                                                # cancels the number, text untouched
        self.assertEqual((app.num, app.text), (None, "2"))

    def test_middle_click_with_nothing_drawn_is_a_space(self):
        app = writer()
        draw(app, "I")
        app.accept()
        self.assertEqual(app.text, "I ")

    def test_space_refused_while_a_letter_is_half_drawn(self):
        app = writer()
        app.seq = ["d"]
        app.space()
        self.assertEqual(app.text, "")

    def test_notes_are_saved(self):
        app = writer()
        draw(app, "H"); draw(app, "I")
        with open(app.path) as f:
            self.assertEqual(f.read(), "Hi")

    def test_screen_rows_fit(self):
        app = writer()
        for ch in "HELLO WORLD".replace(" ", ""):
            draw(app, ch)
        for state in ([], ["d", "r"], ["bl", "br", "r"]):
            app.seq = state
            lines = app.render(21, 4).splitlines()
            self.assertEqual(len(lines), 6)
            self.assertTrue(all(len(ln) == 23 for ln in lines), lines)


class ParseTests(unittest.TestCase):
    def test_log_line(self):
        self.assertEqual(parse("[id 3 h45] 00 07 00 20 00 00 -> btn=00 dx=7 dy=32 wheel=0"), (0, 7, 32, 0))

    def test_negative_values_and_buttons(self):
        self.assertEqual(parse("[id 3 h45] 04 bc ff d5 00 ff -> x"), (4, -68, 213, -1))

    def test_bare_and_timestamped(self):
        self.assertEqual(parse("01 00 00 00 00 00"), (1, 0, 0, 0))
        ts, rest = split_ts("12.345 [id 3 h45] 00 01 00 00 00 00")
        self.assertEqual(ts, 12.345)
        self.assertEqual(parse(rest), (0, 1, 0, 0))

    def test_other_lines_ignored(self):
        for line in ("Scanning 8 s...", "Found D06  d1:19:d1:4f:61:e8  rssi=-52  hid=1", "[id 1 h35] 00 00 00 00 00 00"):
            self.assertIsNone(parse(line))


class GuideTests(unittest.TestCase):
    def test_svg_and_markdown(self):
        entries = al.load_entries()
        xml.dom.minidom.parseString(make_guide.make_svg(entries))      # well-formed
        md = make_guide.make_markdown(entries)
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            self.assertIn(f"| **{ch}** |", md)


if __name__ == "__main__":
    unittest.main()
