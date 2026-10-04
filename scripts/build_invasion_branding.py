#!/usr/bin/env python3
"""Downsample the original HD Bloodstone logo for the centered Invasion HUD."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    canvas = Image.new("RGBA", (1020, 156))
    for index in range(4):
        tile = Image.open(ROOT / f"assets/logo/textures/bloodstone_big/logo_{index+1}.png").convert("RGBA")
        assert tile.size == (255, 153)
        canvas.alpha_composite(tile, (index*255, 0))
    canvas.resize((255,39),Image.Resampling.LANCZOS).save(ROOT / "assets/logo/textures/invasion_logo.png", optimize=True)


if __name__ == "__main__":
    main()
