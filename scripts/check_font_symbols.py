#!/usr/bin/env python3
"""Check each effective font separately, following references and selected pack overlays."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


class ValidationError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValidationError(f"invalid number: {value}")))
    except (OSError, ValueError) as error:
        raise ValidationError(f"{path}: {error}") from error


def resource_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"resource ID must be a string: {value!r}")
    value = value if ":" in value else f"minecraft:{value}"
    if not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+", value) or any(part in (".", "..", "") for part in value.split(":")[1].split("/")):
        raise ValidationError(f"invalid resource ID: {value!r}")
    return value


def major(value):
    return value[0] if isinstance(value, list) else value


class PackView:
    def __init__(self, root: Path, pack_format: int = 75):
        self.root = root.resolve()
        self.pack_format = pack_format
        self.layers = [self.root]
        metadata = read_json(self.root / "pack.mcmeta")
        for entry in metadata.get("overlays", {}).get("entries", []):
            formats = entry.get("formats", {})
            low = entry.get("min_format", formats.get("min_inclusive") if isinstance(formats, dict) else formats)
            high = entry.get("max_format", formats.get("max_inclusive") if isinstance(formats, dict) else formats)
            if low is None or high is None:
                raise ValidationError(f"overlay has no supported range: {entry}")
            directory = self.root / entry["directory"]
            if not directory.resolve().is_relative_to(self.root) or not directory.is_dir():
                raise ValidationError(f"missing or unsafe overlay directory: {directory}")
            if major(low) <= pack_format <= major(high):
                self.layers.append(directory)

    def path(self, key: str, category: str, suffix: str) -> Path:
        namespace, name = resource_id(key).split(":")
        relative = Path("assets") / namespace / category / (name + suffix)
        for layer in reversed(self.layers):
            candidate = layer / relative
            if candidate.is_file():
                return candidate
        raise ValidationError(f"missing {category} resource: {key}{suffix}")

    def files(self, category: str, namespace: str = "*") -> dict[str, Path]:
        result = {}
        for layer in self.layers:
            for folder in (layer / "assets").glob(f"{namespace}/{category}"):
                for path in folder.rglob("*.json"):
                    result[f"{folder.parent.name}:{path.relative_to(folder).with_suffix('').as_posix()}"] = path
        return result


@dataclass(frozen=True)
class Glyph:
    font: str
    path: Path
    provider: int
    definition: dict
    cell: tuple[int, int] | None = None

    def signature(self):
        value = {key: item for key, item in self.definition.items() if key not in ("chars", "advances")}
        return value, self.cell


class FontResolver:
    def __init__(self, pack: PackView):
        self.pack = pack
        self.cache = {}

    def resolve(self, key: str, stack=()) -> dict[str, list[Glyph]]:
        key = resource_id(key)
        if key in stack:
            raise ValidationError("font reference cycle: " + " -> ".join((*stack, key)))
        if key in self.cache:
            return self.cache[key]
        path = self.pack.path(key, "font", ".json")
        data = read_json(path)
        providers = data.get("providers")
        if not isinstance(providers, list):
            raise ValidationError(f"{path}: providers must be an array")
        result = defaultdict(list)
        for index, provider in enumerate(providers):
            if not isinstance(provider, dict):
                raise ValidationError(f"{path}: provider[{index}] must be an object")
            kind = provider.get("type", "").removeprefix("minecraft:")
            if provider.get("filter"):
                raise ValidationError(f"{path}: conditional provider filters need a separate option-aware check")
            if kind == "reference":
                for char, uses in self.resolve(provider.get("id"), (*stack, key)).items():
                    result[char].extend(uses)
            elif kind == "space":
                advances = provider.get("advances")
                if not isinstance(advances, dict):
                    raise ValidationError(f"{path}: space advances must be an object")
                for char, advance in advances.items():
                    if len(char) != 1 or isinstance(advance, bool) or not isinstance(advance, (int, float)) or not math.isfinite(advance):
                        raise ValidationError(f"{path}: invalid space advance {char!r}: {advance!r}")
                    result[char].append(Glyph(key, path, index, {"type": "space", "advance": advance}))
            elif kind == "bitmap":
                resource_id(provider.get("file"))
                rows = provider.get("chars")
                if not isinstance(rows, list) or not rows or not all(isinstance(row, str) and row for row in rows) or len(set(map(len, rows))) != 1:
                    raise ValidationError(f"{path}: bitmap chars must be a nonempty rectangular grid")
                height, ascent = provider.get("height", 8), provider.get("ascent")
                if type(height) is not int or height <= 0 or type(ascent) is not int or ascent > height:
                    raise ValidationError(f"{path}: invalid bitmap height/ascent: {height}/{ascent}")
                for y, row in enumerate(rows):
                    for x, char in enumerate(row):
                        if char != "\0":  # Empty bitmap cells are not glyph assignments.
                            result[char].append(Glyph(key, path, index, provider, (y, x)))
            else:
                raise ValidationError(f"{path}: unsupported provider type {kind!r}; coverage cannot be confirmed")
        self.cache[key] = dict(result)
        return self.cache[key]


def check_fonts(pack: PackView, selected=None):
    resolver = FontResolver(pack)
    keys = selected or sorted(pack.files("font"))
    errors = []
    for key in keys:
        try:
            for char, uses in resolver.resolve(key).items():
                if len(uses) > 1:
                    locations = ", ".join(f"{use.font} provider[{use.provider}]" for use in uses)
                    errors.append(f"{key}: U+{ord(char):04X} ({char}) is assigned {len(uses)} times: {locations}")
        except ValidationError as error:
            errors.append(f"{key}: {error}")
    return len(keys), errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", type=int, default=75, help="Integer pack format used to select overlays (default: 75).")
    parser.add_argument("--font", action="append", help="Font resource ID; repeat to select fonts (default: all pack fonts).")
    parser.add_argument("--font-root", type=Path, help="Compatibility option: select fonts under this assets/<namespace>/font directory.")
    args = parser.parse_args()
    try:
        selected = args.font
        if args.font_root:
            folder = args.font_root.resolve()
            if not folder.is_dir() or folder.name != "font" or folder.parent.parent.name != "assets":
                raise ValidationError("--font-root must point to an existing assets/<namespace>/font directory")
            args.root = folder.parents[2]
            selected = [f"{folder.parent.name}:{path.relative_to(folder).with_suffix('').as_posix()}" for path in folder.rglob("*.json")]
            if not selected:
                raise ValidationError("--font-root contains no fonts")
        pack = PackView(args.root, args.format)
        count, errors = check_fonts(pack, selected)
        if not count:
            raise ValidationError("No fonts found; nothing was checked")
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if errors:
            return 1
        print(f"OK: {count} effective fonts, references and per-font symbol uniqueness; format {args.format}.")
        print("Independent fonts may reuse symbols. Vanilla fallback fonts and client rendering are outside this check.")
        return 0
    except (ValidationError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
