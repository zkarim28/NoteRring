"""Flick detection and calibration.

The D06's pad reports only relative motion, so a "flick" is a burst of motion ended by a pause (the finger
lifting). Its direction is decided from the whole burst, in 45-degree sectors, after correcting for how the pad
is rotated and stretched (calibration.json, made by `python ring_writer.py --calibrate`).
"""
import json
import math
import os
import time

from hid_report import parse, split_ts

HERE = os.path.dirname(os.path.abspath(__file__))
CALIB_FILE = os.path.join(HERE, "calibration.json")


def load_calibration(path=CALIB_FILE):
    cal = {"rot": 0.0, "gy": 1.0}
    if os.path.exists(path):
        with open(path) as f:
            cal.update(json.load(f))
    return cal


class Flick:
    """One finger flick -> direction 0..7 (0 = up, then clockwise in 45-degree steps), or None if too short.

    When a flick lands within (22.5 - soft) degrees of the boundary with the next sector, the neighbouring direction
    is kept as `last_alt` (the runner-up), which the writer uses as evidence when suggesting a correction."""

    def __init__(self, thresh, rot=0.0, gy=1.0, gap=0.12, lockout=0.35, soft=12.0):
        self.thresh, self.rot, self.gy, self.gap, self.lockout, self.soft = thresh, rot, gy, gap, lockout, soft
        self.last_alt = None
        self.ax = self.ay = 0
        self.last = None
        self.locked_until = 0.0

    def click(self, t):
        """A button press jiggles the pad: forget the burst in progress and ignore motion for a moment."""
        self.locked_until = t + self.lockout
        self.ax = self.ay = 0
        self.last = None

    def vector(self):
        """(angle in radians clockwise from up, length) of the burst so far, after calibration."""
        raw = math.atan2(self.ax, -self.ay) - self.rot
        mag = math.hypot(self.ax, self.ay)
        x, y = mag * math.sin(raw), -mag * math.cos(raw) * self.gy
        return math.atan2(x, -y), math.hypot(x, y)

    def _finish(self):
        result = None
        self.last_alt = None
        if self.last is not None:
            ang, mag = self.vector()
            if mag >= self.thresh:
                deg = math.degrees(ang)
                result = round(deg / 45) % 8
                off = deg - 45 * round(deg / 45)          # -22.5 .. +22.5 degrees from the sector centre
                if abs(off) >= self.soft:
                    self.last_alt = (result + (1 if off > 0 else -1)) % 8
        self.ax = self.ay = 0
        self.last = None
        return result

    def feed(self, dx, dy, t):
        """Add one motion report. Returns the direction of the PREVIOUS burst if this report starts a new one."""
        if t < self.locked_until:
            return None
        done = self._finish() if self.last is not None and t - self.last > self.gap else None
        self.ax += dx
        self.ay += dy
        self.last = t
        return done

    def poll(self, t):
        """Call regularly with the current time: returns the direction once the finger has lifted."""
        if self.last is not None and t - self.last > self.gap:
            return self._finish()
        return None


def open_port(port):
    import serial
    return serial.Serial(port, 115200, timeout=0)


def calibrate(port, path=CALIB_FILE):
    """Flick up, right, down, left three times each; stores the pad's rotation and vertical gain."""
    ser, det, buf = open_port(port), Flick(thresh=0), b""
    names = ["UP", "RIGHT", "DOWN", "LEFT"]
    expected = [0, 90, 180, 270]
    samples = []
    print("Calibration: flick the pad as asked, pausing between flicks. Ctrl-C to abort.")
    for round_ in range(3):
        for e, name in zip(expected, names):
            print(f"  flick {name} ({round_ + 1}/3) ... ", end="", flush=True)
            got = None
            while got is None:
                buf += ser.read(4096)
                *lines, buf = buf.split(b"\n")
                for line in lines:
                    p = parse(split_ts(line.decode(errors="replace"))[1])
                    if p and (p[1] or p[2]) and not p[0]:
                        det.feed(p[1], p[2], time.time())
                if det.last is not None and time.time() - det.last > det.gap and math.hypot(det.ax, det.ay) > 60:
                    got = (det.ax, det.ay)
                    det.ax = det.ay = 0
                    det.last = None
                time.sleep(0.01)
            print(f"got angle {math.degrees(math.atan2(got[0], -got[1])):5.0f} deg, length {math.hypot(*got):.0f}")
            samples.append((e, got))
            time.sleep(0.4)
    err = [math.radians(((math.degrees(math.atan2(x, -y)) - e + 180) % 360) - 180) for e, (x, y) in samples]
    rot = math.atan2(sum(map(math.sin, err)) / len(err), sum(map(math.cos, err)) / len(err))
    horiz, vert = [], []
    for e, (x, y) in samples:
        raw = math.atan2(x, -y) - rot
        mag = math.hypot(x, y)
        (horiz if e in (90, 270) else vert).append((abs(mag * math.sin(raw)), abs(mag * math.cos(raw))))
    gx = sum(h[0] for h in horiz) / len(horiz)
    gv = sum(v[1] for v in vert) / len(vert)
    gy = gx / gv if gv else 1.0
    with open(path, "w") as f:
        json.dump({"rot": rot, "gy": gy, "typical": gx}, f)
    print(f"\nsaved {path}: rotation {math.degrees(rot):.1f} deg, vertical gain {gy:.2f}, typical flick {gx:.0f} units")
    print(f"suggested --min-flick about {gx * 0.4:.0f}")
