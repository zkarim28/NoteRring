# Development log: a conversation, step by step

This project was built in one long working session between a person and an AI coding assistant (Claude), from 2026-10-01 to 2026-10-10. This is the running record: what was asked, what was done, what came out of it, and what went wrong.
It is a curated record, not a raw transcript: prompts are shortened and lightly cleaned up, outputs are summarized, and personal material the person pasted along the way (a private to-do list, contact details, hostnames) is left out on purpose.
For the current state of the project, see [PROGRESS.md](../PROGRESS.md); for how to use it, the [README](../README.md).

Legend: **Asked** = the person's request. **Did** = what the assistant built or ran. **Result** = what was actually observed. Anything marked *simulated* was tested only against a fake ring, not a real one.

## Decisions the person made along the way

- Use an ESP32-S3 as a Bluetooth host for the D06 ring; keep everything offline; eventually run on the ESP32 with an SD card and a small screen.
- Drop handwriting recognition and predictive typing in favour of a fixed, user-designed alphabet of direction flicks, one letter at a time.
- Corrections must be approved with a middle click, never applied silently.
- Punctuation goes on the wheel (scroll down), numbers on scroll up.
- Wearable: a watch-style head on a chain-link band with enclosed pins, printed flat in one piece, with a fully enclosed snap clasp.
- Do not worry about temperature measurements for now; keep the on-board decoder experiment in its own folder.

## Timeline

### Day 1, 2026-10-01: first contact and the first input ideas

1. **Asked:** "I have an ESP32-S3 connected right now but am not sure how to use it."
   **Did:** found the board's serial port, saw `arduino-cli` and Python installed, gave a getting-started path. **Result:** board detected on a USB serial port.
2. **Asked:** "just run the stuff for me" (a screenshot showed commands pasted with stray characters, and an empty-flash error from the serial monitor).
   **Did:** compiled and flashed a hello-world sketch (`esp32s3`, `CDCOnBoot=cdc`) and read its output through a raw serial read. **Result:** "Hello from ESP32-S3!" every second; the earlier error was just an empty flash.
3. **Asked:** how to make the ESP32-S3 a Bluetooth host for a D06 TikTok ring (a BLE HID device).
   **Did:** installed NimBLE-Arduino and wrote a host sketch that scans for the ring, bonds, and prints every HID report. **Result:** compiled and flashed; the first scans found nothing (the ring was still connected to the laptop).
4. **Asked:** "check now" after freeing the ring.
   **Did:** read the output; found a "Failed to allocate buffer" flood caused by reading a descriptor inside the notification callback; moved that read to subscribe time. **Result:** the ring connected, bonded, and streamed. Mouse report layout confirmed: buttons, dx (int16), dy (int16), wheel (int8); **relative motion only**.
5. **Asked:** how to turn this tiny pad into note-taking; attached a capture of "mock shaadi" written with a click between letters.
   **Did:** segmented the capture at each click and drew each letter as ASCII; built a live ASCII writing pad with the $P recognizer. **Result:** some letters readable (m, c, s, d), others distorted by pointer acceleration; a simulated run recognized letters, but that test was circular.
6. **Asked:** why the A runs off the screen and everything is capital; can the pad map to absolute positions?
   **Did:** found the cause (after each lift the pen continued from the end of the last stroke, so multi-stroke letters drifted); added a "return home after a lift" mode and timestamped recording. **Result:** absolute position is impossible with this ring; drift fixed in simulation.
   **Mistake found and fixed here:** the assistant had been calling the middle button the right button (HID bit `0x04` is middle).
7. **Asked:** should the ASCII screen have higher resolution?
   **Did:** measured by squashing recorded letters onto coarser grids. **Result:** resolution is not the limit (10/10 still matched at 36 and 18 cells across, 9/10 at 9); consistency is.
8. **Asked:** forget recognition, use four swipe directions to pick from menus.
   **Did:** built `swipe_menu.py` (group, pair, letter in 3 swipes). **Result:** reachable and tested with a simulated ring.
9. **Asked:** scroll through letters and click one at a time, with middle click to select; right click does not work, so left = backspace.
   **Did:** built `scroll_type.py`; fixed an inverted wheel direction found by its own simulated test. **Result:** typed a test string *(simulated)*.

### Day 1 to 2: predictive flick typing, then back to letters

10. **Asked:** what is really the fastest way to take notes? Then: no recording, it should be quiet, ideally faster than a phone or laptop.
    **Did:** answered honestly: voice is fastest, a ring pad realistically 15 to 25 words per minute at best; proposed T9-style flicks with word prediction. **Result:** the person agreed to try it.
11. **Asked:** build the T9-flick typer; then, "hard to type a lot of words, I thought autocomplete might help."
    **Did:** built `flick_type.py` (8 directions = 8 letter groups, a 10,000-word frequency list); agreed the first version only completed single words; added a next-word table (272 KB from public word-pair counts), learning from typed text, and note saving. The person chose fully offline, runnable on the ESP32 later (SD card, small screen). **Result:** about 11% fewer actions per word on ordinary sentences; typing whole words was still laborious.
12. **Asked:** custom words when suggestions are missing; use an existing note file as vocabulary; numbers; keep the display very small; change the letter groups to a compass layout.
    **Did:** added spell mode, a free-character mode, capital-letter memory for names; measured that importing a small personal note file helps only when limited to new words and capitalization (importing everything made ordinary sentences about 8% harder); added number mode and a 21x4 character display; remapped the groups. **Result:** all tested offline and with a simulated ring.
13. **Asked:** can I type my thoughts without looking at a screen? Then: can I type all 26 letters with some flick system?
    **Did:** laid out eyes-free options honestly; built `letter_flick.py`, two flicks per character with the same compass groups. **Result:** 32 unique codes; simulated live run typed and saved text.
14. **Asked (the design that stuck):** a self-designed alphabet where each letter is a short path of the eight directions (for example A = `bl br r`), lifting the finger between strokes; middle click accepts, left = backspace, right = space, wheel = number 0 to 9.
    **Did:** built `scribe_type.py` and `scribe_alphabet.json`, with a check against duplicate sequences. Over the next prompts: A also as `bl br l`, H also as `d r d`, J also as `r l d tl`, S also as `l d r d l`. **Result:** about 3.4 flicks per letter plus a click; 98% of letters decoded from noisy simulated flicks.
15. **Asked:** package the scribe typer with its alphabet into its own folder, no autocomplete, with a reference guide of direction pictograms, as a new repo for GitHub.
    **Did:** created `ring-writer/` (writer, flick detector, alphabet loader, firmware, 24 unit tests, `docs/alphabet.svg` and `GUIDE.md` generated from the alphabet, a keyboard-only `--demo` mode); committed locally. **Result:** the person later pushed it.

### Day 2: the wearable

16. **Asked:** what battery? Is it safe on the wrist with a PLA bracelet? (Then: the board is an ESP32-S3 Super Mini; it does have battery pads on the back.)
    **Did:** advice on tiny protected LiPo cells, charge rates, wrist-safety measures, and PETG over rigid PLA; corrected an earlier claim about the board's pads after the person's correction; asked for a board photo to check the pads. **Result:** general guidance only, nothing measured.
17. **Asked:** help with 3D modelling to package everything.
    **Did:** found the OpenSCAD Homebrew package disabled (it fails macOS's security check) and did not bypass that; set up Python CAD (build123d) with a small renderer and a browser 3D viewer; laid out the board, battery, OLED and SD module into a case. **Result:** about 47.7 x 36.2 x 17.7 mm with placeholder sizes (the board and SD footprints are the person's real values).
18. **Asked:** a chain-link wrist band; then "like this ZenLink STL" (a file of a print-in-place bracelet with enclosed pins).
    **Did:** inspected the file (140.6 x 19 x 4 mm, 76 solids, hourglass-shaped captive pins), then built **our own** equivalent links rather than editing someone else's design. The head became one big link of the chain.
19. **Asked:** where are the clips to close the loop? then: make the clip fully enclosed.
    **Did:** designed a snap buckle, first with side windows, then a fully enclosed sleeve with hidden detent pockets; fixed a bug found on the way (barbs extruded the wrong way). **Result:** no overlaps, 0.2 mm closed gap, prongs flex about 0.8 mm (about 1.4% strain), rough estimates of 3 N to close and 16 N to pull open. **Not printed; the forces are guesses.**

### Day 5, 2026-10-05: the real ring, corrections, speed

20. **Asked:** run the stroke test in Python; make sure the plugged-in ESP32 has the firmware.
    **Did:** found the board on a new port, confirmed the host firmware was already running, waited for the ring to wake and connect, calibrated, ran the writer live. **Result (real ring):** L, I and H decoded correctly with no ghost flicks; space and backspace worked; the wheel's number once ran 1, 2, 3, then back to 0 (still unexplained).
21. **Asked:** an autocorrect: if I complete almost all of W but end on the wrong direction, it is probably W; any pitfalls?
    **Did:** tested the idea on the real alphabet before building. **Result:** most one-step slips map to a unique letter (164 of 181), but three pairs are one slip apart (A and P, D and H, U and Y), and a lost flick silently turns 17 of 30 letters into other valid letters. Recommended: show a suggestion, never apply silently.
22. **Asked:** corrections only after a middle click; punctuation on the wheel (scroll down), numbers on scroll up.
    **Did:** built both: guesses shown as `~W?`, applied only on middle click, ties shown but not applied, approved fixes logged; wheel walks punctuation and numbers; arrows shown on the terminal; `--raw` mode that types the stroke pictograms; 43 tests. **Result:** simulated: letters typed right rose from 67% to 93% with sloppy flicks (about 14 degrees of wobble). Not yet measured on real hands.
23. **Asked:** how to read the ring faster?
    **Did:** found the app's own waiting was the cost (a 120 ms wait after each flick, a 350 ms lockout after clicks); added `--gap`, `--lockout`, `--debounce` and a `--measure` tool. **Result (real ring):** reports every about 15 ms, longest pause inside a flick 23 ms, shortest lift 225 ms, no pad jiggle after any button or the wheel; measured values saved to a git-ignored `settings.json`.
24. **Asked:** keep a progress log in the repo.
    **Did:** wrote `PROGRESS.md` and linked it from the README; scanned the repo for personal strings before committing.

### Day 10, 2026-10-10: heat, then the OLED and SD card

25. **Asked:** the ESP32 is getting hot (also before the speed-up); is that fine?
    **Did:** confirmed the board was streaming normally, and that the speed-up only changed the Mac side; changed the firmware to run at 80 MHz, print the chip temperature every 10 s, and write each report once; flashed and confirmed it still connects. **Result:** works; the first reading was 52.2 C and no before/after comparison was made. The person declined a longer temperature watch.
26. **Asked:** can the ring decoding run on the ESP32 itself and print letters straight to serial, as an isolated experiment? **Status: not started.** The alphabet is only a few hundred bytes, so it fits easily.
27. **Asked:** commit and push, and which pins to use for the OLED and SD module.
    **Did:** committed; the push failed because the assistant's shell has no SSH key for the person's account (the person pushes from their own terminal). Looked up the board's pinout, found the sources disagree on defaults, and chose pins from those with no boot or USB role.
    Then the person gave their SD module's pin names (3V3, CS, MOSI, CLK, MISO, GND), confirming it is 3.3 V only, and wired it.
28. **Asked:** whether the printed pad numbers equal GPIO numbers.
    **Did:** said usually yes but unverified for a clone, and told the person how to check. **Result:** the wiring worked when tested.
29. **Asked:** what next? then: flash the firmware.
    **Did:** wrote and flashed `firmware/hardware_test`. **Result (real hardware):** the OLED answered at I2C 0x3C; the first SD run said "NOT FOUND" until the card was reseated with power off; then **SD write and read-back passed**. Safe card handling explained (insert and remove with USB unplugged; eject in Finder on the Mac).
30. **Asked:** record this whole conversation in the repo, to push. **Did:** this file.

## Mistakes and corrections (kept on purpose)

- Called the middle button "right click" for several steps (HID bit `0x04` is middle). Found when the person said right click did not work; tools and docs corrected.
- A wheel direction was inverted in the scroll typer; the assistant's own simulated test caught it.
- The first clasp barbs were extruded the wrong way, so the clasp model briefly overlapped; found by a numerical check and fixed.
- A first autocorrect plan was to apply guesses automatically; the person chose middle-click approval instead, which is also what the analysis (silent wrong fixes, lost flicks) argued for.
- Early on the assistant guessed the Super Mini had no battery pads; the person corrected it.
- Several things were tested only in simulation (suggestions, arrows and raw mode, the clasp, all of the CAD). They are marked as such everywhere; real-ring accuracy over longer use is still unmeasured.
- The assistant cannot push to the person's GitHub (no SSH key in its shell); pushes are done by the person.

## What is open

- Run the writer on the real ring for a few days and collect real accuracy; look at the wheel's number jump; decide about noisy guesses while a letter is half drawn.
- Print the small test pieces (test strip, clasp test) before the band; measure the real part sizes.
- The on-board decoder experiment (letters decided on the ESP32), then show text on the OLED and save notes to the SD card from the board.

*Not included here, on purpose:* the original pasted messages, a personal to-do list, contact details, and the local file layout. A verbatim record can be kept privately outside the repo.
