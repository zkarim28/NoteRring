# Ring Writer

Write with a cheap Bluetooth "TikTok scroll" ring (the **D06**) by flicking its tiny touchpad one direction at a time.
No screen to look at, no autocomplete: every letter is a short, fixed sequence of direction flicks that you choose.

```
D06 ring ──BLE──▶ ESP32-S3 (firmware/ring_host) ──USB serial──▶ ring_writer.py ──▶ text + notes/
```

The ESP32-S3 is a Bluetooth LE host: it pairs with the ring and prints every mouse report over USB serial.
`ring_writer.py` turns those reports into flicks, flicks into letters, and saves what you write.

![Alphabet](docs/alphabet.svg)

Full reference with arrow pictograms: [docs/GUIDE.md](docs/GUIDE.md)

## How you write

1. Flick the pad in one direction (8 directions: `u tr r br d bl l tl`), then **lift your finger**.
2. Flick the next direction, lift, and so on. For example **Z** is `r`, `bl`, `r` (right, down-left, right).
3. **Middle click** to accept the letter. The display shows what you have drawn so far (`d r =L`) and which letters it could still become.

| Control | Does |
|:--|:--|
| Flick | adds a direction to the letter |
| Middle click | accepts the letter, else the selected number, else inserts a space |
| Left click | undoes the last flick, else backspace |
| Right click | space |
| Wheel | number 0-9: each tick up adds one, each tick down subtracts one; middle click accepts it |

The first letter of the text, and the first after `. ? !`, is a capital. Punctuation sticks to the word before it.

## Quick start

Needs a D06 ring, an ESP32-S3 board with native USB, and macOS or Linux (the terminal UI uses `termios`).

**1. Flash the ESP32-S3**
```bash
arduino-cli core install esp32:esp32
arduino-cli lib install NimBLE-Arduino
arduino-cli compile --fqbn esp32:esp32:esp32s3 --board-options CDCOnBoot=cdc firmware/ring_host
arduino-cli upload  --fqbn esp32:esp32:esp32s3 --board-options CDCOnBoot=cdc -p /dev/cu.usbmodemXXXX firmware/ring_host
```
`CDCOnBoot=cdc` is what makes serial output appear over the native USB port. If an upload fails, hold BOOT, tap RESET, release BOOT.

**2. Free the ring.** A BLE ring talks to one device at a time. Turn Bluetooth off on your computer (or forget the D06), wake the ring,
and let the ESP32 connect. Watch it with `arduino-cli monitor -p /dev/cu.usbmodemXXXX -c baudrate=115200`; you should see `Connected`
and then lines like `[id 3 h45] 00 07 00 20 00 00 -> btn=00 dx=7 dy=32 wheel=0` as you use the pad. The first connect after a reset
sometimes needs a retry; the firmware rescans by itself. **Close the monitor before step 4**: only one program can hold the port.

**3. Python**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python ring_writer.py --cheatsheet          # print the alphabet
python ring_writer.py --demo                # try it with the keyboard, no hardware (numpad keys are flicks)
```

**4. Calibrate once, then write**
```bash
python ring_writer.py --port /dev/cu.usbmodemXXXX --calibrate    # flick up, right, down, left, three times each
python ring_writer.py --port /dev/cu.usbmodemXXXX
```
Calibration measures how the pad is rotated and stretched (the ring's axes are not square) and saves it to `calibration.json`.
Without it, diagonals are often misread.

## Make the alphabet yours

[alphabet.json](alphabet.json) is the whole alphabet. Each character maps to one or more sequences:

```json
"A": ["bl br r", "bl br l"],
"Z": "r bl r"
```

- Directions are `u d l r tl tr bl br`. A character may list several sequences and all are accepted.
- Two characters may not share an exact sequence (the file is rejected with a clear message).
- A sequence may be the start of a longer one (`d r` is **L**, and also the start of **F** = `d r r`). That is fine because you accept the letter yourself.
- Add symbols under `"symbols"`. The single flicks are free, so they are good for punctuation.

After editing, regenerate the guide and picture: `python tools/make_guide.py`.

## Tuning

| Option | Meaning |
|:--|:--|
| `--min-flick N` | shortest flick that counts, in ring units (default 100). Raise it if you get ghost flicks, lower it if flicks are missed. `--calibrate` suggests a value. |
| `--gap S` | pause that counts as lifting your finger (default 0.12 s). |
| `--flip` | reverse which wheel direction adds to the number. |
| `--screen COLSxROWS` | size of the display drawn in the terminal (default `21x4`, a 128x32 OLED with a 6x8 font). Plain ASCII, so what you see is what a tiny display would show. |
| `--notes-dir DIR` | where notes are saved (default `notes/`, one file per session, rewritten after every change). |
| `--alphabet FILE` | use a different alphabet file. |

If it says `Resource busy`, another program (usually a serial monitor) has the port.

## Status

A working prototype.
- Verified on hardware: the ring pairs with the ESP32-S3 and its raw reports (motion, wheel, buttons) stream over USB serial.
- Verified in software: alphabet loading, flick detection with calibration, the writer, notes saving, the guide generator (`python -m unittest discover -s tests`), and the live loop against simulated ring input.
- **Not yet done:** tuning against real handwriting-by-flick on a real hand. Expect to adjust `--min-flick` and the alphabet as you learn what is comfortable.
- The pad reports relative motion only, so there is no absolute position; that is why letters are built from direction flicks.

## Roadmap

- Port the writer from Python to the ESP32-S3 itself, so it runs without a computer.
- A small OLED/LCD for the 4-row display, and an SD card for notes.
- Haptic confirmation for each flick, for writing without looking.
- Optional extras later (word shortcuts, more symbols), kept out of the core on purpose.

## Layout

```
ring_writer.py     the app: writer state, terminal UI, command line
flick.py           flick detector and calibration
alphabet.py        loads alphabet.json
hid_report.py      parses the mouse reports printed by the firmware
alphabet.json      your alphabet
firmware/ring_host the ESP32-S3 BLE host sketch
tools/make_guide.py  builds docs/GUIDE.md and docs/alphabet.svg from alphabet.json
tests/             unit tests (no hardware needed)
```
