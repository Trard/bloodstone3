#!/usr/bin/env python3
"""Validate the BloodLevels import without building a ZIP or modifying the pack."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

from check_font_symbols import FontResolver, PackView, ValidationError, check_fonts, major, read_json, resource_id, unique_object

SOURCE_SHA1 = "93f17b457b4d78e5bcce9fa2b8bf181089847b4c"
OLD_CODES = list(range(0xE520, 0xE52A)) + list(range(0xE530, 0xE536))
MAPPING = {chr(code): chr(code - 0x4C0) for code in OLD_CODES}
FONTS = ["bloodlevels:icons", "bloodlevels:icons_default", "bloodlevels:menus",
         "bloodlevels:menu_progress", "bloodlevels:menu_premium_progress"]


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def source_bytes_match(name, actual, expected):
    # Git normalizes JSON line endings; PNGs must remain byte-for-byte identical.
    if name.endswith(".json"):
        actual, expected = actual.replace(b"\r\n", b"\n"), expected.replace(b"\r\n", b"\n")
    return actual == expected


def single(glyphs, char, label):
    uses = glyphs.get(char, [])
    require(len(uses) == 1, f"{label}: U+{ord(char):04X} must resolve exactly once, found {len(uses)}")
    return uses[0]


def validate_contract(pack: PackView, config: dict):
    resolver = FontResolver(pack)
    _, errors = check_fonts(pack, FONTS)
    require(not errors, "\n".join(errors))
    icons, exported, default = [resolver.resolve(key) for key in (FONTS[0], FONTS[1], "minecraft:default")]
    require(set(exported) == set(MAPPING.values()), "icons_default must export exactly the 16 allocated symbols")
    for old, new in MAPPING.items():
        expected = single(icons, old, "original private icon").signature()
        for label, glyphs in [("new private icon", icons), ("exported icon", exported), ("default", default)]:
            require(single(glyphs, new, label).signature() == expected, f"{label}: remapped U+{ord(new):04X} changed glyph/metrics")
    for char, uses in default.items():
        if char not in MAPPING.values():
            require(all(not use.font.startswith("bloodlevels:") for use in uses), f"Unexpected BloodLevels glyph in default: U+{ord(char):04X}")
    for key in FONTS[3:]:
        glyphs = resolver.resolve(key)
        for old in set(glyphs) & MAPPING.keys():
            require(single(glyphs, old, key).signature() == single(glyphs, MAPPING[old], key).signature(), f"{key}: old/new bar glyph mismatch")

    def check_text(value, expected, label):
        require(isinstance(value, str), f"{label}: expected a string")
        codes = [char for char in value if 0xE000 <= ord(char) <= 0xF8FF]
        require(codes == expected, f"{label}: expected {[f'U+{ord(c):04X}' for c in expected]}, found {[f'U+{ord(c):04X}' for c in codes]}")
        require("<font:bloodlevels:icons>" in value and "</font>" in value, f"{label}: missing explicit BloodLevels font")
        for char in codes:
            require(single(icons, char, label).signature() == single(default, char, label).signature(), f"{label}: legacy and explicit font differ")

    colors = ["gray", "white", "yellow", "orange", "green", "pink", "cyan", "blue", "purple", "red", "rainbow"]
    require(set(config.get("badges", {})) == set(colors), "Unexpected or missing badge categories in companion config")
    require(config.get("prefix") == "%badge% ", "Unexpected prefix template")
    for i, color in enumerate(colors):
        check_text(config["badges"][color], [chr(0xE060 + min(i, 9))], f"badges.{color}")
    bar = config.get("progress-bar", {})
    require(type(bar.get("length")) is int and bar["length"] == 10, "Expected progress bar length 10")
    for i, key in enumerate(["empty", "filled", "half", "premium-filled", "premium-half"]):
        codes = [chr(0xE070 + i), chr(0xE075)]
        check_text(bar.get(key), codes, f"progress-bar.{key}")
        target = FONTS[4] if key.startswith("premium-") else FONTS[3]
        for char in codes:
            single(resolver.resolve(target), char, target)
    return resolver


class Assets:
    def __init__(self, pack, vanilla=None):
        self.pack, self.vanilla = pack, vanilla
        self.assumed = set()

    def data(self, key, category, suffix):
        try:
            return self.pack.path(key, category, suffix).read_bytes()
        except ValidationError:
            namespace, name = resource_id(key).split(":")
            archive_path = f"assets/{namespace}/{category}/{name}{suffix}"
            if self.vanilla and archive_path in self.vanilla.namelist():
                return self.vanilla.read(archive_path)
            # The only external model used by this import; callers are told when it was not verified.
            if not self.vanilla and category == "models" and key == "minecraft:item/generated":
                self.assumed.add(key)
                return b'{"parent":"minecraft:builtin/generated"}'
            raise

    def model(self, key, stack=()):
        key = resource_id(key)
        if key in ("minecraft:builtin/generated", "minecraft:builtin/entity"):
            return {}
        require(key not in stack, "model parent cycle: " + " -> ".join((*stack, key)))
        d = json.loads(self.data(key, "models", ".json"), object_pairs_hook=unique_object)
        parent = self.model(d["parent"], (*stack, key)) if "parent" in d else {}
        merged = {**parent, **d}
        merged["textures"] = {**parent.get("textures", {}), **d.get("textures", {})}
        return merged

    def texture(self, value, textures, stack=()):
        require(isinstance(value, str), "Texture reference must be a string")
        if value.startswith("#"):
            alias = value[1:]
            require(alias not in stack, "texture alias cycle: " + " -> ".join((*stack, alias)))
            require(alias in textures, f"undefined texture alias: #{alias}")
            return self.texture(textures[alias], textures, (*stack, alias))
        return self.data(value, "textures", ".png")


def validate_assets(pack, resolver, assets):
    from PIL import Image
    counts = Counter()
    for category in ("font", "items", "models"):
        files = pack.files(category, "bloodlevels")
        require(files, f"No BloodLevels {category} found")
        for key, path in files.items():
            d = read_json(path)
            counts[category] += 1
            if category == "font":
                for p in d.get("providers", []):
                    if p["type"].removeprefix("minecraft:") == "bitmap":
                        with Image.open(io.BytesIO(assets.data(p["file"], "textures", ""))) as im:
                            rows = p["chars"]
                            require(im.width % len(rows[0]) == 0 and im.height % len(rows) == 0, f"{key}: image not divisible by glyph grid")
                            im.load()
            elif category == "items":
                model = d.get("model", {})
                require(model.get("type") in ("minecraft:model", "minecraft:empty"), f"{key}: unsupported item type; extend validator")
                if "oversized_in_gui" in d:
                    require(type(d["oversized_in_gui"]) is bool, f"{key}: oversized_in_gui must be boolean")
                if model["type"] == "minecraft:model":
                    assets.model(model["model"])
            else:
                model = assets.model(key)
                textures = model.get("textures", {})
                for value in textures.values():
                    assets.texture(value, textures)
                for element in model.get("elements", []):
                    for name in ("from", "to"):
                        point = element.get(name)
                        require(isinstance(point, list) and len(point) == 3 and all(type(x) in (int, float) and -16 <= x <= 32 for x in point), f"{key}: invalid element {name}: {point}")
                    for face in element.get("faces", {}).values():
                        assets.texture(face["texture"], textures)
    effective_pngs = {}
    for layer in pack.layers:
        for p in (layer / "assets/bloodlevels/textures").rglob("*.png"):
            effective_pngs[p.relative_to(layer)] = p
    require(effective_pngs, "No BloodLevels PNG textures found")
    for path in effective_pngs.values():
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            im.load()
        counts["png"] += 1
    # The imported menu has 112 pages, each with a matching title glyph and label mask.
    menus = resolver.resolve("bloodlevels:menus")
    for page in range(1, 113):
        use = single(menus, chr(0xE600 + page - 1), "menu page")
        require(use.definition.get("file") == f"bloodlevels:gui/levels_{page:03}.png", f"menu page {page}: incorrect background")
        item = read_json(pack.path(f"bloodlevels:menu-label-mask-{page}", "items", ".json"))
        require(item["model"]["model"] == f"bloodlevels:item/levels_{page:03}_mask", f"menu page {page}: incorrect mask")
    return counts


def validate_source(pack, source):
    require(hashlib.sha1(source.read_bytes()).hexdigest() == SOURCE_SHA1, "Source ZIP SHA-1 differs from the audited devtest archive")
    changed = {"font/icons.json", "font/menu_progress.json", "font/menu_premium_progress.json"}
    with zipfile.ZipFile(source) as archive:
        require(archive.testzip() is None, "Source ZIP CRC failure")
        originals = {name for name in archive.namelist() if name.startswith("assets/bloodlevels/") and not name.endswith("/")}
        for name in originals:
            relative = name.removeprefix("assets/bloodlevels/")
            category, rest = relative.split("/", 1)
            key = "bloodlevels:" + (rest.removesuffix(".json") if category != "textures" else rest)
            target = pack.path(key, category, ".json" if category != "textures" else "")
            if relative not in changed:
                require(source_bytes_match(name, target.read_bytes(), archive.read(name)), f"Imported resource differs from source: {name}")
            else:
                original = json.loads(archive.read(name))["providers"]
                current = read_json(target)["providers"]
                require(current[:len(original)] == original, f"Original font providers changed: {name}")
        actual = {str(p.relative_to(pack.root)) for p in (pack.root / "assets/bloodlevels").rglob("*") if p.is_file()}
        require(actual == originals | {"assets/bloodlevels/font/icons_default.json"}, "Unexpected or missing imported files")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", type=int, default=75)
    parser.add_argument("--config", type=Path, help="Default: <root>/integrations/bloodlevels/resource-pack.yml")
    parser.add_argument("--source-zip", type=Path, help="Also verify original archive hash, file set and unchanged resources.")
    parser.add_argument("--vanilla-jar", type=Path, help="Verify external vanilla resources against this local client JAR.")
    args = parser.parse_args()
    vanilla = None
    try:
        import yaml
        pack = PackView(args.root, args.format)
        config = yaml.safe_load((args.config or pack.root / "integrations/bloodlevels/resource-pack.yml").read_text())
        require(isinstance(config, dict), "Companion config must be a YAML mapping")
        resolver = validate_contract(pack, config)
        if args.vanilla_jar:
            vanilla = zipfile.ZipFile(args.vanilla_jar)
            version = json.loads(vanilla.read("version.json"))
            declared = version["pack_version"].get("resource_major", version["pack_version"].get("resource"))
            require(major(declared) == args.format or isinstance(declared, dict) and declared.get("major") == args.format, f"Vanilla JAR resource format {declared} does not match {args.format}")
        assets = Assets(pack, vanilla)
        counts = validate_assets(pack, resolver, assets)
        if args.source_zip:
            validate_source(pack, args.source_zip)
            print("OK: audited source ZIP hash, original assets and backwards-compatible font providers.")
        else:
            print("NOTE: source ZIP not supplied; archive fidelity was not checked.")
        print(f"OK: BloodLevels format {args.format}, {dict(counts)}, 112 menu page/mask pairs.")
        print("OK: 16 exported glyphs without collisions, old/private aliases and companion YAML match.")
        if assets.assumed:
            print("NOTE: assumed vanilla model(s), not inspected: " + ", ".join(sorted(assets.assumed)))
        print("Client rendering, server configuration and compatibility with other client packs still require in-game verification.")
        return 0
    except ImportError as error:
        print(f"ERROR: {error}. Install Pillow and PyYAML to run this checker.", file=sys.stderr)
        return 1
    except (ValidationError, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    finally:
        if vanilla:
            vanilla.close()


if __name__ == "__main__":
    raise SystemExit(main())
