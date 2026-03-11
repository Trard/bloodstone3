#!/usr/bin/env python3
"""
Add or update a suffix bitmap provider and copy its PNG into the resource pack.

Default outputs:
  assets/minecraft/textures/font/suffixes/<name>.png
  assets/minecraft/font/suffixes.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

PACK_NAME_PATTERN = re.compile(r"[^a-z0-9_.]")
OPAQUE_STEM_PATTERN = re.compile(r"^(image|img|photo|screenshot)[_-]?\d", re.IGNORECASE)
PRIVATE_USE_MIN = 0xE000
PRIVATE_USE_MAX = 0xF8FF


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def to_pack_name(raw: str) -> str:
    return PACK_NAME_PATTERN.sub("_", raw.lower())


def sanitize_name(raw: str, label: str) -> str:
    cleaned = to_pack_name(raw).strip("._")
    if not cleaned:
        fail(
            f"Invalid {label}; sanitized value is empty. "
            "Use a clear English asset name."
        )
    return cleaned


def parse_codepoint(raw: str) -> int:
    normalized = raw.strip().upper()
    for prefix in ("U+", "\\U", "\\u"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    try:
        value = int(normalized, 16)
    except ValueError as exc:
        raise SystemExit(f"ERROR: Invalid codepoint: {raw!r}") from exc

    if not (PRIVATE_USE_MIN <= value <= PRIVATE_USE_MAX):
        fail(
            f"Codepoint {raw!r} is outside the private-use range "
            f"U+{PRIVATE_USE_MIN:04X}-U+{PRIVATE_USE_MAX:04X}."
        )
    return value


def format_codepoint(value: int) -> str:
    return f"U+{value:04X}"


def iter_strings(value: Any) -> list[str]:
    out: list[str] = []
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            out.append(current)
        elif isinstance(current, list):
            stack.extend(reversed(current))
        elif isinstance(current, dict):
            for key, nested in reversed(list(current.items())):
                if isinstance(key, str):
                    out.append(key)
                stack.append(nested)
    return out


def resolve_assets_root(root: str) -> Path:
    root_path = Path(root).resolve()
    if root_path.exists() and root_path.is_file():
        fail(f"--assets-root points to a file, expected directory: {root_path}")

    if (root_path / "minecraft").is_dir():
        return root_path

    nested_assets = root_path / "assets"
    if nested_assets.is_dir():
        return nested_assets.resolve()

    return root_path


def build_codepoint_index(font_root: Path) -> dict[int, set[Path]]:
    index: dict[int, set[Path]] = {}
    if not font_root.is_dir():
        return index

    for path in sorted(font_root.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"Failed to parse JSON while scanning codepoints: {path}: {exc}")

        file_codepoints: set[int] = set()
        for text in iter_strings(data):
            for char in text:
                codepoint = ord(char)
                if PRIVATE_USE_MIN <= codepoint <= PRIVATE_USE_MAX:
                    file_codepoints.add(codepoint)

        for codepoint in file_codepoints:
            index.setdefault(codepoint, set()).add(path)

    return index


def provider_codepoint(provider: dict[str, Any]) -> int | None:
    chars = provider.get("chars")
    if not isinstance(chars, list) or not chars:
        return None

    char = chars[0]
    if not isinstance(char, str) or not char:
        return None

    return ord(char[0])


def find_provider(providers: list[dict[str, Any]], texture_id: str) -> tuple[int | None, dict[str, Any] | None]:
    for index, provider in enumerate(providers):
        if isinstance(provider, dict) and provider.get("file") == texture_id:
            return index, provider
    return None, None


def next_free_codepoint(start: int, used: set[int]) -> int:
    for value in range(start, PRIVATE_USE_MAX + 1):
        if value not in used:
            return value
    fail("No free private-use codepoints remain in the configured range.")


def next_suffix_codepoint(
    start: int,
    providers: list[dict[str, Any]],
    used: set[int],
) -> int:
    suffix_codepoints = [
        value
        for provider in providers
        if (value := provider_codepoint(provider)) is not None
    ]
    candidate = start if not suffix_codepoints else max(start, max(suffix_codepoints) + 1)
    return next_free_codepoint(candidate, used)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a suffix PNG into the resource pack and add or update its "
            "font provider entry."
        )
    )
    parser.add_argument("png", help="Source PNG file path.")
    parser.add_argument(
        "--assets-root",
        default="assets",
        help=(
            "Assets root directory. If this points to repo root and './assets' "
            "exists, './assets' is used automatically."
        ),
    )
    parser.add_argument(
        "--name",
        default=None,
        help=(
            "Output suffix name. Defaults to source stem when it is already a "
            "clear pack-safe English name."
        ),
    )
    parser.add_argument(
        "--ascent",
        type=int,
        default=7,
        help="Bitmap ascent value (default: 7).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=7,
        help="Bitmap height value (default: 7).",
    )
    parser.add_argument(
        "--codepoint",
        default=None,
        help=(
            "Explicit private-use codepoint like E016 or U+E016. "
            "Defaults to the next free codepoint across assets/minecraft/font/*.json."
        ),
    )
    parser.add_argument(
        "--start-codepoint",
        default="E000",
        help="Starting codepoint for automatic allocation (default: E000).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing texture/provider entry for the same suffix name.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    src_png = Path(args.png).resolve()
    if not src_png.is_file():
        fail(f"PNG file does not exist: {src_png}")
    if src_png.suffix.lower() != ".png":
        fail(f"Input must be a .png file: {src_png.name}")

    if args.name is None:
        if not src_png.stem.isascii() or OPAQUE_STEM_PATTERN.match(src_png.stem):
            fail(
                "Source filename is non-English or opaque. "
                "Provide --name with a clear English asset name."
            )
        raw_name = src_png.stem
    else:
        raw_name = args.name

    name = sanitize_name(raw_name, "name")
    assets_root = resolve_assets_root(args.assets_root)
    font_json = assets_root / "minecraft" / "font" / "suffixes.json"
    texture_dir = assets_root / "minecraft" / "textures" / "font" / "suffixes"
    texture_path = texture_dir / f"{name}.png"
    texture_id = f"minecraft:font/suffixes/{name}.png"

    if not font_json.is_file():
        fail(f"Suffix font JSON does not exist: {font_json}")

    try:
        suffix_data = json.loads(font_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Failed to parse {font_json}: {exc}")

    providers = suffix_data.get("providers")
    if not isinstance(providers, list):
        fail(f"{font_json} is missing a top-level 'providers' list.")

    existing_index, existing_provider = find_provider(providers, texture_id)
    current_codepoint = provider_codepoint(existing_provider) if existing_provider else None

    if existing_provider and not args.force:
        fail(
            f"Suffix provider already exists for {name!r}. "
            "Use --force to update it in place."
        )

    if texture_path.exists() and src_png != texture_path and not args.force:
        fail(
            f"Destination texture already exists: {texture_path}. "
            "Use --force to overwrite it."
        )

    font_root = font_json.parent
    codepoint_index = build_codepoint_index(font_root)
    used_codepoints = set(codepoint_index)
    unavailable_codepoints = used_codepoints - ({current_codepoint} if current_codepoint else set())

    if args.codepoint is not None:
        target_codepoint = parse_codepoint(args.codepoint)
        if target_codepoint in unavailable_codepoints:
            owners = ", ".join(str(path) for path in sorted(codepoint_index[target_codepoint]))
            fail(
                f"Codepoint {format_codepoint(target_codepoint)} is already used in: {owners}"
            )
    elif existing_provider and current_codepoint is not None:
        target_codepoint = current_codepoint
    else:
        start_codepoint = parse_codepoint(args.start_codepoint)
        target_codepoint = next_suffix_codepoint(
            start_codepoint,
            providers,
            unavailable_codepoints,
        )

    provider = {
        "type": "bitmap",
        "file": texture_id,
        "ascent": args.ascent,
        "height": args.height,
        "chars": [chr(target_codepoint)],
    }

    action = "UPDATE" if existing_provider else "ADD"

    print(f"Source PNG : {src_png}")
    print(f"Assets root: {assets_root}")
    print(f"Font JSON  : {font_json}")
    print(f"Name       : {name}")
    print(f"Texture    : {texture_path}")
    print(f"Action     : {action}")
    print(f"Codepoint  : {format_codepoint(target_codepoint)}")
    print(f"Symbol     : {chr(target_codepoint)}")
    print(
        f"{'DRY-RUN ' if args.dry_run else ''}"
        f"{'COPY' if src_png != texture_path else 'SKIP'} {src_png} -> {texture_path}"
    )
    print(
        f"{'DRY-RUN ' if args.dry_run else ''}"
        f"WRITE {font_json}"
    )

    if args.dry_run:
        print("Done (dry-run).")
        return

    texture_dir.mkdir(parents=True, exist_ok=True)
    if src_png != texture_path:
        shutil.copy2(src_png, texture_path)

    if existing_index is None:
        providers.append(provider)
    else:
        providers[existing_index] = provider

    font_json.write_text(json.dumps(suffix_data, indent=2) + "\n", encoding="utf-8")
    print("Done.")


if __name__ == "__main__":
    main()
