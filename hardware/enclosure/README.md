# Wrist unit enclosure (3D-printable)

Parametric CAD for the wearable: a "watch head" holding the ESP32-S3 Super Mini, battery, OLED and SD module, built as one big link of a
print-in-place chain band with enclosed hinge pins and a snap-buckle clasp. Python + [build123d](https://github.com/gumyr/build123d); no CAD program needed.

> **Status: designed and checked by computer, not yet printed.** Every dimension in `parts.py` is a placeholder (typical sizes), except the
> ESP32-S3 Super Mini footprint (22.52 x 18 mm) and the SD module footprint (18.5 x 17.5 mm). Measure your parts and edit `parts.py`.
> Hinge and clasp clearances are untested until you print `prints/test_strip.stl` and `prints/clasp_test.stl`.

```bash
cd hardware/enclosure
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python fitcheck.py                        # lay the parts out, size the case: fitcheck.png, fitcheck.html, layout.json
python band_assembly.py --test-strip      # 4 links, 3 joints with different clearances: PRINT THIS FIRST
python band_assembly.py --clasp-test      # just the two halves of the snap buckle (+ clasp_closed.html, clasp_section.html)
python band_assembly.py --wrist-circ 165  # the whole band: links + head + links -> band_flat.stl / band_flat.html
```

Open any generated `*.html` in a browser for an interactive 3D view (drag to rotate; loads three.js from a CDN). Open the `.stl` files in your slicer.
Generated files are written to the current folder and are git-ignored; `prints/` holds copies of the STL files from the last build.

## Files

| File | What it does |
|:--|:--|
| `parts.py` | **the dimensions to edit**, wall thicknesses and clearances |
| `fitcheck.py` | packs the parts into a skin-side layer and a top layer, sizes the case, writes a picture and `layout.json` |
| `zen.py` | one print-in-place link with a fully enclosed pin (13 x 4 mm band, 7.5 mm pitch), plus the clasp (enclosed sleeve with hidden detent pockets, or `open` with side windows) |
| `band_assembly.py` | the head as one big link, the test strip, the clasp test, the whole band |
| `preview.py`, `viewer.py` | tiny renderers (matplotlib picture, three.js page) used by the scripts |

## Design notes

- Axes: x = around the wrist (band direction), y = along the arm, z = up from the skin. Everything prints flat, in place, with the skin side on the bed.
- Links: 13 mm wide, 4 mm thick, 7 mm plates with a 0.5 mm gap; a slot on the left of each link, a tongue on the right, pin 2.7 mm. Default clearances 0.35 mm around the pin and 0.30 mm each side of the tongue (`--clr`, `--side`).
- Checked with boolean operations: no overlap between neighbours, the designed gaps, 60 degrees of bend per joint (a 165 mm wrist needs about 17).
- Clasp, enclosed: the prongs (12 mm, 1.4 % strain) click into hidden pockets in a closed sleeve and release with a firm pull (rough estimate 15 N, **untested**). `--clasp open` gives the squeeze-to-release version.
- Printing: PETG recommended; no supports expected (check your slicer's preview, especially the 6.2 mm bridge over the clasp tunnel). In Bambu Studio, import the STL as ONE object with several parts, or the chain falls apart.
- Safety (wearing a LiPo on the wrist): protected cell of about 300 mAh or less, resettable fuse, no charging while worn, thick skin-side wall, padded cell pocket, vent path away from the skin.
