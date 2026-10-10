# Project log

What has been built, tried, measured and decided so far, and what is still open. Kept honest: each claim says how it was checked.
*Last updated: 2026-10-10. Work started 2026-10-01.*

For the prompt-by-prompt story of how it was built (what was asked, done and observed, plus mistakes), see [docs/DEVLOG.md](docs/DEVLOG.md).

## Where things stand

| Area | Status | Checked how |
|:--|:--|:--|
| Ring to ESP32-S3 over Bluetooth LE, raw reports over USB serial | works | real ring |
| Flick detection, calibration, timing measurement | works | real ring |
| Writing letters from flick sequences, numbers, punctuation, space, undo | works | real ring (L, I, H, number, space, backspace); unit tests; simulated ring |
| Correction suggestions (approved by middle click) | built | unit tests and simulation only; not yet used on a real ring |
| Terminal display (arrows or names), raw stroke mode | built | unit tests; simulated ring |
| 3D-printable wrist unit (case, chain band, snap clasp) | designed | computer checks only; **nothing printed yet**; most part sizes are placeholders |
| OLED and SD card on the ESP32 | wired and verified | real hardware: OLED found, SD write and read-back OK |
| Writer running on the ESP32 itself | not started | |

## Timeline

### 2026-10-01: getting the ring to talk

- Wrote an ESP32-S3 Bluetooth LE host (NimBLE-Arduino) that pairs with the D06 ring and prints each HID report as a line over USB serial (`firmware/ring_host`).
- Learned the ring's reports: four HID report characteristics (keyboard, consumer, mouse, and a feature report). The mouse report is
  `[buttons][dx lo][dx hi][dy lo][dy hi][wheel]`: buttons `0x01` left, `0x02` right, `0x04` middle; **motion is relative only, there is no absolute finger position**.
- Bug found and fixed: reading a descriptor inside the notification callback blocked the BLE stack ("Failed to allocate buffer"). The report IDs are now read once when subscribing.
- Quirks: the ring sleeps when idle and has to be woken; it talks to one host at a time (turn Bluetooth off on the computer); the first connect after a reset sometimes needs a retry.

### 2026-10-01 to 10-02: finding an input method that works with a relative-only pad

Each step below was built and tested before moving on.

1. **Handwriting recognition** ($P point-cloud recognizer, drawing in an ASCII box). Letters came out distorted: pointer acceleration, drift after every lift, and no way to know where the next stroke starts.
   Measured that screen resolution was *not* the limit (quantizing recorded letters to a coarse grid still matched: 10/10 at 36 and 18 cells across, 9/10 at 9, 7/10 at 6). Consistency matters more than fidelity.
2. **Swipe menus and scroll-and-click.** Reliable but slow.
3. **T9-style flicks with offline word prediction.** One flick per letter (8 directions = 8 letter groups), a 10,000-word list, a next-word table and learning from what you type, all small enough for an ESP32.
   Measured on ordinary sentences: 3.57 to 3.16 actions per word from the next-word table (about 11% less); importing a small personal note file helped only when limited to new words and capitalization.
   It worked, but typing whole words this way was still laborious, and the choice was made to go letter by letter instead. This work is not in this repo.
4. **Two-flick letters** (first flick picks a compass group, second picks the item). Unambiguous and about 2 flicks per character.
5. **A user-designed scribe alphabet (current).** Each letter is a short sequence of direction flicks (`u d l r tl tr bl br`), lifting the finger between flicks; middle click accepts.
   Average 3.4 flicks per letter plus one click. Chosen because it is easier to remember than the grouped codes.

### 2026-10-02: the alphabet and the writer take shape

- `alphabet.json` is the whole alphabet, with several accepted sequences per letter (alternates for A, H, J, S were added) and a check that no two letters share a sequence.
- Fixed a labelling mistake: the HID bit `0x04` is the **middle** button, not right. Right click did not work in early tests (it works now: later measurements and a writing session used it), so space is also reachable by middle-clicking with nothing drawn.
- Reference sheet with arrow pictograms generated from the alphabet (`docs/alphabet.svg`, `docs/GUIDE.md`, `tools/make_guide.py`).
- Packaged as a self-contained repo: writer, firmware, unit tests, guide, and `--demo` (keyboard-only, no hardware).

### 2026-10-02: the wearable (3D design)

- Fit-check script that packs the ESP32-S3 Super Mini, battery, OLED and SD module into a case and sizes it (placeholder sizes except the board and SD footprints): about **47.7 x 36.2 x 17.7 mm**.
- Band: our own print-in-place chain links with **fully enclosed hinge pins** (13 x 4 mm, 7.5 mm pitch), in the style of Zen Link bracelets but our own geometry. The head is one big link of the chain, so head and band print flat as one piece.
- Clasp: a printed snap buckle built into the band ends. Default is a **fully enclosed sleeve** with hidden detent pockets (pull to release); an open version with side windows (squeeze to release) is also there.
- Checked by boolean operations only: no overlap between neighbouring parts, the designed gaps, 60 degrees of bend per joint (a 165 mm wrist needs about 17), clasp closes and holds. Rough estimates of about 3 N to close and 16 N to pull open are **guesses, not measurements**.
- Bambu Studio note: import the multi-body STL as one object with several parts, or the chain falls apart.
- Safety notes gathered for a lithium cell worn on the wrist (advice, not tested): protected pouch cell of about 300 mAh or less, resettable fuse, charge at 0.5 C or less and never while worn, thick skin-side wall, padded cell pocket, vent path away from the skin, PETG rather than rigid PLA links.

### 2026-10-05: first real-ring sessions and new features

- **Real ring, calibration:** flicks measured 247 to 584 units long. Up and down flicks lean left (up about 8 to 20 degrees off, down about 4 to 21), giving a pad rotation of 6.0 degrees and a vertical gain of 1.14.
- **Real ring, writing:** L (`d r`), I (`d l l`) and H (`d d r`) decoded correctly with no ghost flicks; space and backspace worked. The number selector worked, but once climbed 1, 2, 3 and then dropped to 0 before being accepted (see open issues).
- **Correction suggestions.** When the flicks spell no letter, the best guess is shown (`~W?`) and **nothing is typed until you middle-click**. Evidence, strongest first: a flick that landed near a direction boundary keeps its runner-up direction; any one flick off by 45 degrees; one stray or missing flick (3+ flicks).
  A tie is shown, not applied; an exact letter is never replaced; approved corrections are logged to `notes/corrections.log`. In simulation with flicks as sloppy as the calibration suggested (about 14 degrees of wobble), letters typed right went from **67% to 93%**; with 5% dropped and 5% stray flicks, 61% to 87%. Simulation, not real data.
- **Punctuation moved to the wheel:** scroll down from rest to walk through the marks, middle click inserts; scroll up still counts numbers.
- **Terminal display:** flicks drawn as arrows (`↘ ↗ ↘ ↑`); `--glyphs names` keeps plain ASCII for a small display. `--raw` types the stroke pictograms instead of letters, for checking what the ring really sends.
- **Speed:** `--measure` records the ring for about 70 seconds and suggests `--gap` and `--lockout`.
  Measured on this ring: reports every about 15 ms (99% under 23 ms), longest pause inside a flick 23 ms, shortest lift 225 ms, **no pad jiggle after any button or the wheel**.
  So the defaults (120 ms wait after a flick, 350 ms ignore after a click) were far too cautious; measured values are saved per device in `settings.json` (git-ignored) and loaded automatically.

- **Heat:** the ESP32-S3 felt warm (also before the speed changes; those were Python-side only). The host firmware now runs the CPU at 80 MHz instead of 240, prints the chip's own temperature every 10 s as a `# temp ...` comment line (the Python side ignores it), and writes each report with one USB write instead of about twenty.
  Flashed and confirmed it still pairs and streams; the first reading was 52.2 C at 80 MHz right after connecting. No before/after comparison was made, so the size of the improvement is unknown.

### 2026-10-10: OLED and SD card wired and verified

- Wired the 0.91 inch OLED (I2C) and a microSD module (SPI) to the ESP32-S3 Super Mini; pins and notes in [firmware/hardware_test/WIRING.md](firmware/hardware_test/WIRING.md).
- `firmware/hardware_test` initializes both and reports on the OLED and serial. Real hardware result: the OLED answered at 0x3C, and the SD card mounted, wrote a file and read it back. (The first run said "SD: NOT FOUND" until the card was reseated with power off.)
- Still to do on this front: show the writer's text on the OLED, save notes to the SD card from the ESP32, and run the letter decoding on the board.

## How this was tested

- `python -m unittest discover -s tests`: 50 tests, no hardware needed (alphabet, flick detection and calibration, writer, suggestions, punctuation, display, timing analysis, settings, guide generation).
- A simulated ring (fake serial port feeding timed reports) drives the live loop end to end.
- The real ring and an ESP32-S3 were used for the data path, calibration, timing measurement and a first writing session.

## Known issues and open questions

- **Wheel:** the number once ran 1, 2, 3 and then back to 0 before accepting. Unclear whether that was the user scrolling back or the wheel sending a tick on release. Needs a look with `--raw`-style logging of wheel reports.
- **Lost flicks are the main risk, not wrong directions.** If one flick is too short to register, 17 of 30 letters silently become another valid letter (C, D, F, H become L; E becomes F; I becomes T; M becomes N, and so on). Letters with a repeated direction (E, F, H, I) are the most fragile.
- **Letters one slip apart** (`python ring_writer.py --check`): A and P, D and H, U and Y. A slip between them cannot be noticed by any correction. Two of the three pairs exist because of added alternate sequences.
- **Guesses flicker while a letter is half drawn** (for example `br tr br` shows `~U?` on its way to W). Harmless, since nothing applies without a middle click, but noisy.
- **No accuracy numbers from real hands yet,** only simulation. Diagonal letters are the thing to test first.
- **Hardware:** nothing is printed, so hinge clearances and the clasp's stiffness are unknown; the head is about 60 mm of rigid length on a curved wrist (may need a curved underside or a 90 degree turn); component heights are guesses; the board's battery pads have not been inspected; the writer does not run on the ESP32 yet.

## Next steps

1. Use the writer on the real ring for a few days, with `--raw` and the corrections log, and collect real accuracy numbers (especially diagonals and repeated directions).
2. Resolve the wheel behavior; decide whether to hide guesses until the flicks pause.
3. Print the small test pieces (`hardware/enclosure/prints/test_strip.stl`, `clasp_test.stl`) and tune clearances before printing the band.
4. Measure the real parts, replace the placeholder sizes, then build the real case: lid, display window, USB-C opening, switch, strap fit.
5. Port the writer to the ESP32-S3 so it runs without a computer; add the OLED and SD card.
6. Optional later: haptic feedback per flick, a faster Bluetooth connection interval if needed, early commit of flicks.
