"""Parse the mouse reports that the ESP32 host firmware (firmware/ring_host) prints over USB serial.

A report line looks like   [id 3 h45] 00 07 00 20 00 00 -> btn=00 dx=7 dy=32 wheel=0
or, in a saved capture, a bare   00 07 00 20 00 00   optionally preceded by a timestamp in seconds.
The six bytes are: buttons, dx (int16 little-endian), dy (int16 little-endian), wheel (int8).
Button bits: 0x01 left, 0x02 right, 0x04 middle.
"""
import re

LOG_LINE = re.compile(r"^\[id 3 h\d+\]\s+((?:[0-9a-f]{2}\s+){5}[0-9a-f]{2})")
RAW_LINE = re.compile(r"^\s*((?:[0-9a-f]{2}\s+){5}[0-9a-f]{2})\s*$")
TS_LINE = re.compile(r"^(\d+\.\d+)\s+(.*)$")

LEFT, RIGHT, MIDDLE = 0x01, 0x02, 0x04


def split_ts(line):
    """'1.234 [id 3 h45] 00 ...' -> (1.234, '[id 3 h45] 00 ...'); lines without a timestamp give (None, line)."""
    m = TS_LINE.match(line.strip())
    return (float(m.group(1)), m.group(2)) if m else (None, line.strip())


def parse(line):
    """-> (buttons, dx, dy, wheel), or None if the line is not a mouse report."""
    m = LOG_LINE.match(line) or RAW_LINE.match(line)
    if not m:
        return None
    b = [int(t, 16) for t in m.group(1).split()]
    s16 = lambda lo, hi: ((hi << 8 | lo) ^ 0x8000) - 0x8000
    return b[0], s16(b[1], b[2]), s16(b[3], b[4]), (b[5] ^ 0x80) - 0x80
