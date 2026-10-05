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
import measure                             # noqa: E402
import settings                            # noqa: E402
import ring_writer                         # noqa: E402


def writer():
    return App(al.load_alphabet(), tempfile.mkdtemp())


def draw(app, ch):
    """Write one character the way the user does: its flicks, then middle click."""
    entries = dict(al.load_entries())
    app.seq = list(entries[ch][0])
    app.accept()


class AlphabetTests(unittest.TestCase):
    def test_close_pairs_are_the_known_three(self):
        pairs = {frozenset((a, b)) for a, _, b, _ in al.near_collisions(al.load_entries())}
        self.assertEqual(pairs, {frozenset("AP"), frozenset("DH"), frozenset("UY")})

    def test_punctuation_list(self):
        marks = al.load_punctuation()
        self.assertEqual(marks[:5], [".", ",", "?", "!", "'"])
        self.assertEqual(len(marks), len(set(marks)))

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

    def test_runner_up_only_near_a_boundary(self):
        det = Flick(100, soft=12)
        self.burst(det, 0)                                        # dead centre of "up"
        self.assertIsNone(det.last_alt)
        self.burst(det, 20, t0=5.0)                               # 20 degrees clockwise of up: nearly "up-right"
        self.assertEqual(det.last_alt, 1)
        self.burst(det, -20, t0=10.0)                             # 20 degrees the other way: nearly "up-left"
        self.assertEqual(det.last_alt, 7)
        self.burst(det, 198, t0=15.0)                             # well past "down", toward "down-left"
        self.assertEqual(det.last_alt, 5)

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
        draw(app, "H"); draw(app, "I")
        app.wheel(-1); app.accept()                               # wheel down from rest = the first mark, "."
        self.assertEqual(app.text, "Hi.")
        app.space(); draw(app, "A")
        self.assertEqual(app.text, "Hi. A")

    def test_unknown_sequence_keeps_flicks(self):
        app = writer()
        app.seq = ["u", "u", "u", "u"]
        app.accept()
        self.assertEqual((app.text, app.note), ("", "no such letter"))
        self.assertEqual(len(app.seq), 4)

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
        app.wheel(1); app.wheel(-1)                               # up then down: reaches 0 and stays a number
        self.assertEqual((app.num, app.punct), (0, None))
        app.wheel(-1)                                             # clamps at 0, does NOT switch to punctuation
        self.assertEqual((app.num, app.punct), (0, None))
        for _ in range(20):
            app.wheel(1)
        self.assertEqual(app.num, 9)
        app.undo()                                                # cancels the number, text untouched
        self.assertEqual((app.num, app.text), (None, "2"))

    def test_wheel_down_walks_the_punctuation(self):
        app = writer()
        draw(app, "H"); draw(app, "I")
        marks = app.marks
        self.assertEqual(marks[:5], [".", ",", "?", "!", "'"])
        app.wheel(-1); self.assertEqual(app.punct, 0)             # from rest, down shows the first mark
        app.wheel(-1); app.wheel(-1)
        self.assertEqual(marks[app.punct], "?")
        app.wheel(1)                                              # up goes back one mark
        self.assertEqual(marks[app.punct], ",")
        app.accept()
        self.assertEqual((app.text, app.punct), ("Hi,", None))
        app.wheel(-1); app.wheel(1)                               # up past the first mark cancels
        self.assertEqual(app.punct, None)

    def test_punctuation_wraps_and_attaches_only_where_it_should(self):
        app = writer()
        draw(app, "H"); draw(app, "I"); app.space()
        for _ in range(len(app.marks) + 1):                       # a full lap: down len(marks) times lands on the first mark again
            app.wheel(-1)
        self.assertEqual(app.punct, 0)
        app.undo()
        self.assertEqual(app.punct, None)
        app.wheel(-1)
        for _ in range(app.marks.index("(")):
            app.wheel(-1)
        app.accept()
        self.assertEqual(app.text, "Hi (")                         # "(" keeps the space before it
        app.space()
        app.wheel(-1); app.accept()
        self.assertEqual(app.text, "Hi (.")                       # "." sticks to what is before it

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
        for state in ([], ["d", "r"], ["bl", "br", "r"], ["br", "u", "br", "tr"], ["d", "br", "r"]):
            app.seq, app.alts = state, [None] * len(state)
            lines = app.render(21, 4).splitlines()
            self.assertEqual(len(lines), 6)
            self.assertTrue(all(len(ln) == 23 for ln in lines), lines)
        app.seq, app.alts = [], []
        app.wheel(-1)
        app.wheel(-1)
        lines = app.render(21, 4).splitlines()
        self.assertEqual(len(lines), 6)
        self.assertTrue(all(len(ln) == 23 for ln in lines), lines)
        self.assertIn("SYM", lines[3])


class SuggestionTests(unittest.TestCase):
    def feed(self, app, text, alts=None):
        for i, t in enumerate(text.split()):
            app.add(t, (alts or {}).get(i))

    def test_your_example_w_ending_on_u(self):
        app = writer()
        self.feed(app, "br tr br u")
        self.assertIsNone(app.exact())
        self.assertEqual(app.suggest(), ("W", "slip"))
        self.assertEqual(app.text, "")                            # nothing applied yet
        app.accept()                                              # the middle click approves it
        self.assertEqual(app.text, "W")
        self.assertEqual(app.note, "+ W (fixed)")
        self.assertEqual(app.seq, [])

    def test_every_one_slip_variant_of_every_unambiguous_letter_is_suggested_correctly(self):
        table = al.load_alphabet()
        names = al.NAMES
        ok = total = 0
        for seq, ch in table.items():
            for i, tok in enumerate(seq):
                for step in (1, -1):
                    v = seq[:i] + (names[(names.index(tok) + step) % 8],) + seq[i + 1:]
                    if v in table or len(v) < 2:
                        continue
                    app = writer()
                    self.feed(app, " ".join(v))
                    s = app.suggest()
                    total += 1
                    ok += bool(s and s[0] == ch) or bool(s and s[0] == "?" and ch in s[1])
        self.assertGreater(total, 100)
        self.assertGreater(ok / total, 0.95)                       # the rest are slips that really point at another letter

    def test_exact_letters_are_never_replaced(self):
        app = writer()
        self.feed(app, "d br l")                                  # P exactly (one slip from A's alternate)
        self.assertIsNone(app.suggest())
        app.accept()
        self.assertEqual(app.text, "P")

    def test_ambiguous_guess_is_not_applied(self):
        app = writer()
        self.feed(app, "d br r")                                  # one slip from A, F and H
        s = app.suggest()
        self.assertEqual(s[0], "?")
        self.assertEqual(sorted(s[1]), ["A", "F", "H"])
        app.accept()
        self.assertTrue(app.note.startswith("unsure:"), app.note)
        self.assertEqual(app.text, "")
        self.assertEqual(len(app.seq), 3)                          # the flicks are kept so you can undo or add

    def test_runner_up_direction_outranks_a_blind_slip(self):
        app = writer()
        self.feed(app, "br tr br u", alts={3: "tr"})
        self.assertEqual(app.suggest(), ("W", "angle"))

    def test_extra_and_missing_flicks_need_three_or_more(self):
        app = writer()
        self.feed(app, "br tr br tr d")                           # W plus a stray flick
        self.assertEqual(app.suggest(), ("W", "edit"))
        app = writer()
        self.feed(app, "br tr tr")                                # V with a stray flick, or W with one missing: honestly ambiguous
        s = app.suggest()
        self.assertEqual((s[0], sorted(s[1])), ("?", ["V", "W"]))
        app = writer()
        self.feed(app, "d")                                       # one flick is never guessed at
        self.assertIsNone(app.suggest())

    def test_nothing_close_gives_nothing(self):
        app = writer()
        self.feed(app, "u u u u u u")
        self.assertIsNone(app.suggest())
        app.accept()
        self.assertEqual(app.note, "no such letter")

    def test_can_be_turned_off(self):
        app = App(al.load_alphabet(), tempfile.mkdtemp(), suggest=False)
        self.feed(app, "br tr br u")
        self.assertIsNone(app.suggest())

    def test_approved_corrections_are_logged(self):
        app = writer()
        self.feed(app, "br tr br u")
        app.accept()
        with open(os.path.join(app.notes_dir, "corrections.log")) as f:
            self.assertIn("br tr br u\tW\tslip", f.read())

    def test_undo_removes_the_runner_up_too(self):
        app = writer()
        self.feed(app, "br tr br u", alts={3: "tr"})
        app.undo()
        self.assertEqual((len(app.seq), len(app.alts)), (3, 3))


class GlyphAndRawTests(unittest.TestCase):
    def test_arrows_on_screen(self):
        app = writer()
        for tok in "br tr br u".split():
            app.add(tok)
        names = app.render(21, 4, "names").splitlines()
        arrows = app.render(21, 4, "arrows").splitlines()
        self.assertIn("br tr br u", names[2])
        self.assertIn("↘ ↗ ↘ ↑", arrows[2])
        self.assertIn("~W? ↘↗↘↗ mid=ok", arrows[3])                 # the guessed letter's pictogram too
        self.assertTrue(all(len(ln) == 23 for ln in arrows), arrows)

    def test_raw_mode_types_pictograms_not_letters(self):
        app = App(al.load_alphabet(), tempfile.mkdtemp(), raw=True)
        for tok in "br tr br tr".split():
            app.add(tok)
        self.assertEqual(app.text, "↘↗↘↗")                          # each flick appears at once
        self.assertEqual(app.exact(), "W")                          # ...and is still decoded alongside
        app.accept()
        self.assertEqual((app.text, app.note, app.seq), ("↘↗↘↗ ", "= W", []))
        for tok in "d r".split():
            app.add(tok)
        app.accept()
        self.assertEqual((app.text, app.note), ("↘↗↘↗ ↓→ ", "= L"))

    def test_raw_mode_undo_removes_the_arrow(self):
        app = App(al.load_alphabet(), tempfile.mkdtemp(), raw=True)
        for tok in "d r r".split():
            app.add(tok)
        app.undo()
        self.assertEqual((app.text, app.seq), ("↓→", ["d", "r"]))
        for tok in "u u u u".split():
            app.add(tok)
        app.accept()
        self.assertEqual(app.note, "= ?")                           # no letter matches and nothing is guessed

    def test_raw_mode_saves_the_arrows(self):
        app = App(al.load_alphabet(), tempfile.mkdtemp(), raw=True)
        app.add("d"); app.add("r")
        with open(app.path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "↓→")


class MeasureTests(unittest.TestCase):
    def synthetic_times(self, interval, flicks=40, lift=(0.25, 0.6), dur=(0.12, 0.3)):
        import random
        rnd = random.Random(1)
        t, times = 0.0, []
        for _ in range(flicks):
            end = t + rnd.uniform(*dur)
            while t < end:
                times.append(t)
                t += max(interval * 0.5, rnd.gauss(interval, interval * 0.25))
            t += rnd.uniform(*lift)
        return times

    def test_fast_ring_gets_a_short_gap(self):
        r = measure.analyze_flicks(self.synthetic_times(0.015))
        self.assertAlmostEqual(r["interval_ms"], 15, delta=2)
        self.assertLess(r["gap"], 0.08)
        self.assertGreater(r["gap"], r["max_inside_ms"] / 1000)      # never shorter than a pause inside a flick

    def test_slow_ring_gets_a_longer_gap(self):
        fast = measure.analyze_flicks(self.synthetic_times(0.015))["gap"]
        slow = measure.analyze_flicks(self.synthetic_times(0.045))["gap"]
        self.assertGreater(slow, fast)
        self.assertLessEqual(slow, 0.12)

    def test_not_enough_data(self):
        self.assertIsNone(measure.analyze_flicks([0.0, 0.02, 0.04]))

    def test_click_jiggle_sets_the_lockout(self):
        r = measure.analyze_clicks([1.0, 3.0], [1.05, 1.2, 3.04])
        self.assertEqual(r["settle_ms"], [200, 40])
        self.assertAlmostEqual(r["lockout"], 0.29, delta=0.01)
        calm = measure.analyze_clicks([1.0, 3.0], [])
        self.assertEqual(calm["lockout"], 0.08)                      # no jiggle: the smallest allowed lockout


class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_merge(self):
        p = os.path.join(tempfile.mkdtemp(), "s.json")
        self.assertEqual(settings.load(p), {})
        settings.save({"gap": 0.06, "lockout": 0.1}, p)
        settings.save({"gap": 0.07, "bogus": 1, "port": None}, p)           # merges; unknown keys and None are dropped
        self.assertEqual(settings.load(p), {"gap": 0.07, "lockout": 0.1})

    def test_bad_file_is_ignored(self):
        p = os.path.join(tempfile.mkdtemp(), "s.json")
        with open(p, "w") as f:
            f.write("{not json")
        self.assertEqual(settings.load(p), {})

    def test_saved_values_become_defaults_and_the_command_line_wins(self):
        saved = {"port": "/dev/cu.usbmodem101", "gap": 0.06, "lockout": 0.1, "debounce": 0.12, "min_flick": 150}
        a = ring_writer.build_parser(saved).parse_args([])
        self.assertEqual((a.port, a.gap, a.lockout, a.debounce, a.min_flick), ("/dev/cu.usbmodem101", 0.06, 0.1, 0.12, 150))
        b = ring_writer.build_parser(saved).parse_args(["--gap", "0.09", "--port", "/dev/x"])
        self.assertEqual((b.port, b.gap, b.lockout), ("/dev/x", 0.09, 0.1))
        c = ring_writer.build_parser(None).parse_args([])
        self.assertEqual((c.port, c.gap, c.lockout, c.debounce), (None, 0.12, 0.35, 0.25))     # built-in defaults


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
