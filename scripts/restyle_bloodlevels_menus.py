#!/usr/bin/env python3
"""Apply the root levels_013.png layout to later menu pages, preserving their original level numbers.

Requires Pillow. Run without arguments to update pages 13–112 and their inventory-label masks in place.
Use --output-dir to preview only the menu backgrounds in another directory.
Already converted pages are supported, so repeated runs preserve the numbers and do not rewrite identical images.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SIZE = (256, 256)
SHIFT_Y = 36
HEADER = (42, 37, 133, 63)
# Full-width strips retain the original pixel font, spacing, and even four-digit level numbers.
NUMBER_STRIPS = ((0, 74, 256, 81), (0, 103, 256, 110))


def shifted(box: tuple[int, int, int, int], dy: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    return left, top + dy, right, bottom + dy


def read_image(path: Path) -> Image.Image:
    with Image.open(path) as source:
        if source.size != SIZE:
            raise ValueError(f"{path}: expected {SIZE}, got {source.size}")
        return source.convert("RGBA")


def restyle(source: Image.Image, template: Image.Image) -> Image.Image:
    header = template.crop(shifted(HEADER, SHIFT_Y)).tobytes()
    if source.crop(HEADER).tobytes() == header:
        source_offset = 0
    elif source.crop(shifted(HEADER, SHIFT_Y)).tobytes() == header:
        source_offset = SHIFT_Y
    else:
        raise ValueError("Unrecognized basic reward header; expected the original or converted menu layout")

    result = template.copy()
    for strip in NUMBER_STRIPS:
        numbers = source.crop(shifted(strip, source_offset))
        result.paste(numbers, (strip[0], strip[1] + SHIFT_Y))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=ROOT / "levels_013.png", help="Single-row menu template")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "assets/bloodlevels/textures/gui")
    parser.add_argument("--output-dir", type=Path, help="Preview backgrounds here without changing the pack or its masks")
    parser.add_argument("--first-page", type=int, default=13)
    parser.add_argument("--last-page", type=int, default=112)
    parser.add_argument("--dry-run", action="store_true", help="Validate all inputs and report changes without writing")
    args = parser.parse_args()
    if not 13 <= args.first_page <= args.last_page <= 112:
        parser.error("Expected 13 <= first-page <= last-page <= 112")

    output_dir = args.output_dir or args.source_dir
    pending = []
    masks = []
    models = []
    try:
        template = read_image(args.template)
        # Prepare every page before writing anything, so missing or incompatible inputs fail without partial updates.
        for page in range(args.first_page, args.last_page + 1):
            name = f"levels_{page:03}.png"
            source = read_image(args.source_dir / name)
            result = restyle(source, template)
            destination = output_dir / name
            if destination.resolve() == args.template.resolve():
                raise ValueError(f"Refusing to overwrite the template: {destination}")
            if not destination.exists() or read_image(destination).tobytes() != result.tobytes():
                pending.append((destination, result))
            if args.output_dir is None:
                mask_path = args.source_dir.parent / "item" / f"levels_{page:03}_mask.png"
                mask = result.crop((0, 140, 176, 150))
                with Image.open(mask_path) as previous:
                    if previous.size != mask.size or previous.convert("RGBA").tobytes() != mask.tobytes():
                        masks.append((mask_path, mask))
                model_path = args.source_dir.parent.parent / "models/item" / f"levels_{page:03}_mask.json"
                original = model_path.read_bytes()
                model = json.loads(original)
                # Anchor at slot 39 instead of 48, compensating for its 18 px higher position.
                translation = [18, -35, 0]
                if model["display"]["gui"]["translation"] != translation:
                    model["display"]["gui"]["translation"] = translation
                    data = (json.dumps(model, indent=2, ensure_ascii=False) + "\n").encode()
                    if b"\r\n" in original:
                        data = data.replace(b"\n", b"\r\n")
                    models.append((model_path, data))
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for destination, result in pending + masks:
            result.save(destination)
        for destination, data in models:
            destination.write_bytes(data)
    action = "Would update" if args.dry_run else "Updated"
    print(f"{action} {len(pending)} menu textures (pages {args.first_page}–{args.last_page}) in {output_dir}")
    if args.output_dir is None:
        print(f"{action} {len(masks)} label-mask textures and {len(models)} mask models for slot 39")


if __name__ == "__main__":
    main()
