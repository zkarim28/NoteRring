"""Part dimensions in millimetres: (length x, width y, height z). EDIT THESE with your measured values.

!! Everything below is a PLACEHOLDER, a typical size for that kind of part, not a measurement of yours. !!
Measure each part with calipers (include the tallest thing: USB-C shell, pin headers, solder blobs) and replace it.
"""

# layer: "bottom" = the skin side, "top" = the side you look at
PARTS = {
    # name:            (x,    y,    z,   layer,    colour,    note)
    "ESP32-S3 Super Mini": (22.52, 18.0, 5.0, "top", "#2b7bd1", "22.52 x 18 mm is from the seller; the HEIGHT (5.0) is still a guess, measure it with the USB-C shell"),
    "OLED 0.91in module":  (30.0, 11.5, 4.0, "top", "#222222", "128x32; the visible screen is about 22.4 x 5.6 mm"),
    "LiPo 502030":         (30.0, 20.0, 5.5, "bottom", "#d9a521", "5 x 20 x 30 mm cell + a little for its protection board"),
    "SD card module":      (18.5, 17.5, 3.5, "top", "#7a3fb0", "18.5 x 17.5 mm is from the user; the HEIGHT (3.5) is a guess"),
    "Power slide switch":  (8.0, 4.0, 3.5, "top", "#888888", "optional"),
}

# parts left out of the layout (set a name to False to leave it out)
ENABLED = {}

# set to True if you use a separate charger module (a Super Mini with charger pads may not need one)
USE_CHARGER_MODULE = False
CHARGER = ("Charger module", (26.0, 17.0, 4.0, "bottom", "#c0392b", "TP4056 USB-C style board"))

WALL = 2.0              # case wall thickness
SKIN_WALL = 2.5         # thicker floor between the cell and your wrist
CLEARANCE = 0.6         # gap around every part (printed parts are never exact)
GAP = 1.5               # space between neighbouring parts (wires!)
MAX_LENGTH = 44.0       # longest the parts may run around the wrist (x), before walls; the other direction (y) runs along your arm and should stay under ~38 mm
