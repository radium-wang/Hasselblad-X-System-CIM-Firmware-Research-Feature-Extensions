# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate alpha >=20 hit-test runs from explicit local character PNGs."""
import argparse
import json
from pathlib import Path
from PySide6.QtGui import QImage

def generate(image_dir):
    masks = {}
    for path in sorted(Path(image_dir).glob("*.png")):
        img = QImage(str(path))
        if img.isNull():
            raise ValueError("Unreadable PNG: " + path.name)
        rows = []
        for y in range(img.height()):
            runs, start = [], None
            for x in range(img.width() + 1):
                solid = x < img.width() and img.pixelColor(x, y).alpha() >= 20
                if solid and start is None:
                    start = x
                elif not solid and start is not None:
                    runs.extend([start, x]); start = None
            rows.append(runs)
        masks["/" + path.name] = {"w": img.width(), "h": img.height(), "rows": rows}
    if not masks:
        raise ValueError("No PNG frames in character/img")
    return masks

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("images", type=Path); p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.write_text(json.dumps(generate(a.images), separators=(",", ":")) + "\n")
