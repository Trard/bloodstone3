#!/usr/bin/env python3
"""Reuse the Bloodstone logo and Minecraft pixel letters for the compact corner HUD."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font",type=Path,default=Path("C:/Windows/Fonts/segoeuib.ttf"))
    args = parser.parse_args()
    canvas = Image.new("RGBA", (1020, 324))
    for index in range(4):
        tile = Image.open(ROOT / f"assets/logo/textures/bloodstone_big/logo_{index+1}.png").convert("RGBA")
        assert tile.size == (255, 153)
        canvas.alpha_composite(tile, (index*255, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(args.font), 96)
    draw.text((510, 193), "bloodstone.gg", font=font, anchor="mt", fill=(244,244,244,255))
    canvas.resize((255,81),Image.Resampling.LANCZOS).save(ROOT / "assets/logo/textures/invasion_corner.png", optimize=True)


if __name__ == "__main__":
    main()
