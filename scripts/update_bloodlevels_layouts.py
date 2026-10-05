#!/usr/bin/env python3
"""Update the three dynamic BloodLevels backgrounds from the preserved numbered layouts; never builds a ZIP."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from update_bloodlevels_arrows import load_buttons, update as update_navigation

ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = (198, 198, 198, 255)
# Preserve the original slot positions and controls; erase only the number strips inside the panel.
LAYOUTS = (
    ("levels", "levels_001", ((74, 81), (141, 148)), "menu-label-mask", 48, "\ue510"),
    ("levels_premium_end", "levels_012", ((74, 81), (103, 110), (141, 148)), "menu-label-mask-premium-end", 48, "\ue512"),
    ("levels_free_only", "levels_013", ((110, 117), (139, 146)), "menu-label-mask-free-only", 39, "\ue513"),
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def update(root: Path) -> None:
    assets = root / "assets/bloodlevels"
    buttons = load_buttons(assets / "textures/item")
    model_template = json.loads((assets / "models/item/levels_mask.json").read_text())
    menus_path = assets / "font/menus.json"
    menus = json.loads(menus_path.read_text())
    for name, source, strips, item, slot, glyph in LAYOUTS:
        with Image.open(assets / f"textures/gui/{source}.png") as image:
            assert image.size == (256, 256), source
            canvas = image.convert("RGBA")
        for top, bottom in strips:
            canvas.paste(BACKGROUND, (7, top, 169, bottom))
        canvas = update_navigation(canvas, None, buttons)
        canvas.save(assets / f"textures/gui/{name}.png")
        canvas.crop((0, 140, 176, 150)).save(assets / f"textures/item/{name}_mask.png")
        model = json.loads(json.dumps(model_template))
        model["textures"] = {"layer0": f"bloodlevels:item/{name}_mask", "particle": "#layer0"}
        model["display"]["gui"]["translation"] = [18, -17 if slot == 48 else -35, 0]
        write_json(assets / f"models/item/{name}_mask.json", model)
        write_json(assets / f"items/{item}.json", {
            "oversized_in_gui": True,
            "model": {"type": "minecraft:model", "model": f"bloodlevels:item/{name}_mask"},
        })
        provider = {"type": "bitmap", "file": f"bloodlevels:gui/{name}.png", "ascent": 25, "height": 256, "chars": [glyph]}
        matching = [p for p in menus["providers"] if glyph in "".join(p.get("chars", []))]
        assert len(matching) <= 1, f"Duplicate layout glyph: {glyph}"
        if matching:
            index = menus["providers"].index(matching[0])
            menus["providers"][index] = provider
        else:
            menus["providers"].append(provider)
    write_json(menus_path, menus)
    for name, y in (("menu_numbers_premium", 141), ("menu_numbers_free_only", 110), ("menu_numbers_free_only_lower", 139)):
        font = json.loads((assets / "font/menu_numbers_free.json").read_text())
        for provider in font["providers"]:
            if provider["type"] == "bitmap":
                provider["ascent"] = 25 - y
        write_json(assets / f"font/{name}.json", font)
    progress = json.loads((assets / "font/menu_progress.json").read_text())
    for provider in progress["providers"]:
        if provider["type"] == "bitmap":
            provider["ascent"] -= 36
    write_json(assets / "font/menu_progress_free_only.json", progress)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    update(args.root)
    print("Updated three unnumbered layouts, masks, number fonts and the free-only progress bar; no ZIP built.")
