"""Measure how your ring actually behaves, then suggest values for --gap and --lockout.

    python ring_writer.py --port /dev/cu.usbmodem101 --measure

Five short phases (about 70 seconds): flick around quickly, then press each button and scroll the wheel without touching the pad.
The analysis functions are plain (no hardware) so they can be tested.
"""
import statistics
import time

import settings
from flick import open_port
from hid_report import LEFT, MIDDLE, RIGHT, parse, split_ts


def _pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(p / 100 * len(values)))]


def analyze_flicks(times, quiet=0.10):
    """times: arrival times (s) of motion reports. Returns a dict about report spacing and the safe 'lift' pause."""
    gaps = [b - a for a, b in zip(times, times[1:])]
    inside = [g for g in gaps if g <= quiet]            # spacing between reports of the same flick
    lifts = [g for g in gaps if g > quiet]              # pauses between flicks
    if len(inside) < 10:
        return None
    interval = statistics.median(inside)
    p99 = _pct(inside, 99)
    # a lift pause must be longer than anything that happens inside a flick, with a margin, but short enough to be quick
    gap = min(0.12, max(0.05, round(max(1.5 * p99, 2.5 * interval), 3)))
    ambiguous = sum(1 for g in gaps if gap * 0.8 <= g <= gap * 1.5)
    return {"reports": len(times), "interval_ms": interval * 1000, "p95_ms": _pct(inside, 95) * 1000, "p99_ms": p99 * 1000,
            "max_inside_ms": max(inside) * 1000, "lifts": len(lifts), "shortest_lift_ms": (min(lifts) * 1000 if lifts else None),
            "gap": gap, "ambiguous": ambiguous}


def analyze_clicks(click_times, motion_times, window=0.8):
    """How long after a middle click does the pad keep jiggling? Returns {'settle_ms': [...], 'lockout': suggestion}."""
    settle = []
    for c in click_times:
        after = [m - c for m in motion_times if 0 <= m - c <= window]
        settle.append(max(after) if after else 0.0)
    if not settle:
        return None
    worst = max(settle)
    return {"clicks": len(click_times), "settle_ms": [round(s * 1000) for s in settle],
            "lockout": min(0.35, max(0.08, round(worst * 1.3 + 0.03, 2)))}


def _collect(ser, seconds):
    buf, events, end = b"", [], time.time() + seconds
    while time.time() < end:
        buf += ser.read(4096)
        *lines, buf = buf.split(b"\n")
        for line in lines:
            p = parse(split_ts(line.decode(errors="replace"))[1])
            if p:
                events.append((time.time(), *p))
        time.sleep(0.002)
    return events


def run(port):
    ser = open_port(port)
    print("Phase 1 (20 s): flick the pad around quickly, in all directions, lifting your finger between flicks. Starting in 3 s...")
    time.sleep(3)
    print("  GO")
    ev = _collect(ser, 20)
    motion = [t for t, btn, dx, dy, w in ev if (dx or dy) and not btn]
    f = analyze_flicks(motion)
    if f is None:
        print("  Not enough pad motion was seen. Is the ring awake and connected? (Touch it, then try again.)")
        return
    print(f"  {f['reports']} reports; the ring sends one about every {f['interval_ms']:.0f} ms (95%: {f['p95_ms']:.0f} ms, 99%: {f['p99_ms']:.0f} ms, longest inside a flick: {f['max_inside_ms']:.0f} ms)")
    if f["shortest_lift_ms"]:
        print(f"  {f['lifts']} pauses between flicks; the shortest was {f['shortest_lift_ms']:.0f} ms")

    lockouts = {}
    for name, bit in (("MIDDLE", MIDDLE), ("LEFT", LEFT), ("RIGHT", RIGHT), ("WHEEL", None)):
        what = "scroll the wheel up and down a few ticks" if bit is None else f"press the {name} button 4 times"
        print(f"\nPhase ({name.lower()}, 8 s): do NOT touch the pad. Please {what}, about a second apart. Starting in 3 s...")
        time.sleep(3)
        print("  GO")
        ev2 = _collect(ser, 8)
        times, prev = [], 0
        for t, btn, dx, dy, w in ev2:
            if bit is None:
                if w:
                    times.append(t)
            else:
                if btn & bit and not prev & bit:
                    times.append(t)
                prev = btn
        moves = [t for t, btn, dx, dy, w in ev2 if dx or dy]
        c = analyze_clicks(times, moves)
        if c is None:
            print(f"  No {name.lower()} events seen (skipped).")
            continue
        lockouts[name] = c["lockout"]
        print(f"  {c['clicks']} events; the pad kept moving for {c['settle_ms']} ms after each -> needs a lockout of about {c['lockout']} s")

    lockout = max(lockouts.values()) if lockouts else 0.35
    print()
    print(f"Suggested:  python ring_writer.py --port {port} --min-flick 150 --gap {f['gap']} --lockout {lockout}")
    print(f"  --gap {f['gap']}: a flick is accepted {f['gap'] * 1000:.0f} ms after your finger stops (default 120 ms).")
    if f["ambiguous"]:
        print(f"  Note: {f['ambiguous']} pauses were close to that value, so a flick might split in two. If letters get extra flicks, raise --gap a little.")
    print(f"  --lockout {lockout}: motion is ignored for {lockout * 1000:.0f} ms after a click or wheel tick (default 350 ms); the slowest control decided it.")
    print("  Your flicks may be slower than the ones measured: if letters sprout extra flicks, add 0.01-0.02 to --gap.")
    kept = settings.save({"port": port, "gap": f["gap"], "lockout": lockout, "debounce": 0.12})
    print(f"\nSaved to {settings.path()}:\n  {kept}")
    print("  ring_writer.py uses these automatically from now on (options on the command line still win; delete that file to undo).")
    if f["interval_ms"] > 25:
        print(f"  The ring reports slowly ({f['interval_ms']:.0f} ms apart), which limits how fast flicks can be read. The ESP32 firmware could ask the ring for a faster connection.")
