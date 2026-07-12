#!/usr/bin/env python3
"""Build a Windows .ico from assets/logo.jpg for desktop shortcuts."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "logo.jpg"
OUT = ROOT / "assets" / "logo.ico"
SIZES = (256, 128, 64, 48, 32, 16)


def main() -> int:
    if not SRC.exists():
        print(f"Logo not found: {SRC}")
        return 1

    img = Image.open(SRC).convert("RGBA")
    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    img = img.crop((left, top, left + side, top + side))

    icons = []
    for size in SIZES:
        icons.append(img.resize((size, size), Image.Resampling.LANCZOS))

    icons[0].save(
        OUT,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=icons[1:],
    )
    print(f"Icon written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
