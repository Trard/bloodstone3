#!/usr/bin/env python3
"""Align navigation on 112 numbered BloodLevels pages and three shared backgrounds using Pillow; never builds the pack.

Run without arguments to update the textures in place. Use --output-dir for a preview or --dry-run to validate inputs.
Uses the existing BloodLevels item buttons without redrawing them. Placement and disabled colors follow
levels_menu_55-63.png; the first Back and last Next buttons are disabled on numbered pages.
Shared backgrounds have both buttons active because they do not represent a fixed page number.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SIZE = (256, 256)
PAGE_COUNT = 112
SHARED_BACKGROUNDS = ("levels.png", "levels_free_only.png", "levels_premium_end.png")
BACKGROUND = (198, 198, 198, 255)
BLACK = (0, 0, 0, 255)
ROW = (0, 210, 176, 226)
BUTTON_Y = 213
BUTTON_X = (8, 140)
BUTTON_SIZE = (28, 13)


def gray(value: int) -> tuple[int, int, int, int]:
    return value, value, value, 255


def load_buttons(directory: Path) -> dict[tuple[str, bool], Image.Image]:
    buttons = {}
    # Recolor the original pixels for the disabled state, retaining the existing outline, glyph and transparency.
    disabled_colors = {gray(198): gray(139), gray(255): gray(55), gray(85): gray(212), gray(139): gray(102)}
    for name in ("previous", "next"):
        path = directory / f"{name}.png"
        with Image.open(path) as image:
            if image.size != BUTTON_SIZE:
                raise ValueError(f"{path}: expected {BUTTON_SIZE}, got {image.size}")
            active = image.convert("RGBA")
        disabled = active.copy()
        disabled.putdata([disabled_colors.get(pixel, pixel) for pixel in active.get_flattened_data()])
        buttons[name, True] = active
        buttons[name, False] = disabled
    return buttons


def read_image(path: Path) -> Image.Image:
    with Image.open(path) as source:
        if source.size != SIZE:
            raise ValueError(f"{path}: expected {SIZE}, got {source.size}")
        return source.convert("RGBA")


def update(source: Image.Image, page: int | None, buttons: dict[tuple[str, bool], Image.Image]) -> Image.Image:
    result = source.copy()
    # Extend the clean panel row over the old controls, restoring the frame beneath the old left button as well.
    panel = source.crop((0, 209, 176, 210))
    if panel.crop((3, 0, 173, 1)).tobytes() != Image.new("RGBA", (170, 1), BACKGROUND).tobytes():
        raise ValueError("Unrecognized panel background above the navigation buttons")
    for y in range(ROW[1], ROW[3]):
        result.paste(panel, (0, y))
    draw = ImageDraw.Draw(result)
    draw.rectangle((43, BUTTON_Y, 132, BUTTON_Y + 12), fill=gray(139), outline=BLACK)
    result.alpha_composite(buttons["previous", page is None or page > 1], (BUTTON_X[0], BUTTON_Y))
    result.alpha_composite(buttons["next", page is None or page < PAGE_COUNT], (BUTTON_X[1], BUTTON_Y))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/bloodlevels/textures/gui")
    parser.add_argument("--button-dir", type=Path, default=ROOT / "assets/bloodlevels/textures/item")
    parser.add_argument("--output-dir", type=Path, help="Write the updated backgrounds to a separate directory")
    parser.add_argument("--dry-run", action="store_true", help="Validate all pages and report changes without writing")
    args = parser.parse_args()
    output_dir = args.output_dir or args.source_dir
    pending = []
    pages = [(f"levels_{page:03}.png", page) for page in range(1, PAGE_COUNT + 1)]
    pages.extend((name, None) for name in SHARED_BACKGROUNDS)
    try:
        buttons = load_buttons(args.button_dir)
        # Prepare every page before writing so missing or incompatible input cannot leave a partial update.
        for name, page in pages:
            source = read_image(args.source_dir / name)
            result = update(source, page, buttons)
            destination = output_dir / name
            if not destination.exists() or read_image(destination).tobytes() != result.tobytes():
                pending.append((destination, result))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for destination, result in pending:
            result.save(destination)
    action = "Would update" if args.dry_run else "Updated"
    print(f"{action} {len(pending)} of {len(pages)} menu textures in {output_dir}")
    print("Disabled navigation: Back on page 1; Next on page 112.")


if __name__ == "__main__":
    main()
