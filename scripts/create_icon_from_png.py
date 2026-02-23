#!/usr/bin/env python3
"""
Create a flat item/model/texture trio from a PNG file.

Default hierarchy (like blooddonate icons):
  assets/<namespace>/items/icons/<name>.json
  assets/<namespace>/models/item/icons/<name>.json
  assets/<namespace>/textures/item/icons/<name>.png
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

PACK_NAME_PATTERN = re.compile(r"[^a-z0-9_.]")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def to_pack_name(raw: str) -> str:
    return PACK_NAME_PATTERN.sub("_", raw.lower())


def sanitize_name(raw: str, label: str) -> str:
    cleaned = to_pack_name(raw).strip("._")
    if not cleaned:
        fail(f"Invalid {label}; sanitized value is empty.")
    return cleaned


def sanitize_group(raw: str) -> str:
    normalized = raw.replace("\\", "/").strip("/")
    if not normalized:
        fail("Group cannot be empty.")

    out_parts: list[str] = []
    for part in normalized.split("/"):
        if part in ("", ".", ".."):
            fail(f"Invalid group path segment: {part!r}")
        cleaned = sanitize_name(part, "group segment")
        out_parts.append(cleaned)
    return "/".join(out_parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create item/model JSON and copy a PNG texture into resource-pack "
            "hierarchy for icon-like assets."
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
        "--namespace",
        default="bloodstone",
        help="Destination namespace (default: bloodstone).",
    )
    parser.add_argument(
        "--group",
        default="icons",
        help=(
            "Path under items/, models/item/, textures/item/ "
            "(default: icons). Supports nested paths like 'ui/icons'."
        ),
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Output file/id base name. Defaults to source PNG stem.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination files if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned writes without writing files.",
    )
    return parser.parse_args()


def resolve_assets_root(root: str, namespace: str) -> Path:
    root_path = Path(root).resolve()
    if root_path.exists() and root_path.is_file():
        fail(f"--assets-root points to a file, expected directory: {root_path}")

    namespace_dir = root_path / namespace
    minecraft_dir = root_path / "minecraft"
    if namespace_dir.is_dir() or minecraft_dir.is_dir():
        return root_path

    nested_assets = root_path / "assets"
    if nested_assets.is_dir():
        return nested_assets.resolve()

    return root_path


def main() -> None:
    args = parse_args()

    src_png = Path(args.png).resolve()
    if not src_png.is_file():
        fail(f"PNG file does not exist: {src_png}")
    if src_png.suffix.lower() != ".png":
        fail(f"Input must be a .png file: {src_png.name}")

    namespace = sanitize_name(args.namespace, "namespace")
    group = sanitize_group(args.group)
    name = sanitize_name(args.name or src_png.stem, "name")
    assets_root = resolve_assets_root(args.assets_root, namespace)

    rel = Path(group) / f"{name}.json"
    item_path = assets_root / namespace / "items" / rel
    model_path = assets_root / namespace / "models" / "item" / rel
    texture_path = assets_root / namespace / "textures" / "item" / group / f"{name}.png"

    model_id = f"{namespace}:item/{group}/{name}"
    texture_id = f"{namespace}:item/{group}/{name}"

    item_json = {
        "model": {
            "type": "minecraft:model",
            "model": model_id,
        }
    }
    model_json = {
        "parent": "minecraft:item/generated",
        "textures": {
            "layer0": texture_id,
        },
    }

    collisions: list[Path] = []
    if item_path.exists():
        collisions.append(item_path)
    if model_path.exists():
        collisions.append(model_path)
    same_texture_file = src_png.resolve() == texture_path.resolve() if texture_path.exists() else False
    if texture_path.exists() and not same_texture_file:
        collisions.append(texture_path)
    if collisions and not args.force:
        preview = "\n".join(f"- {path}" for path in collisions)
        fail(
            "Destination files already exist. Use --force to overwrite.\n"
            f"{preview}"
        )

    print(f"Source PNG : {src_png}")
    print(f"Assets root: {assets_root}")
    print(f"Namespace  : {namespace}")
    print(f"Group path : {group}")
    print(f"Name       : {name}")
    print(f"{'DRY-RUN ' if args.dry_run else ''}WRITE {item_path}")
    print(f"{'DRY-RUN ' if args.dry_run else ''}WRITE {model_path}")
    if same_texture_file:
        print(f"SKIP texture copy (source already target): {texture_path}")
    else:
        print(f"{'DRY-RUN ' if args.dry_run else ''}COPY {src_png} -> {texture_path}")

    if args.dry_run:
        print("Done (dry-run).")
        return

    item_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    texture_path.parent.mkdir(parents=True, exist_ok=True)

    item_path.write_text(json.dumps(item_json, indent=2) + "\n", encoding="utf-8")
    model_path.write_text(json.dumps(model_json, indent=2) + "\n", encoding="utf-8")
    if not same_texture_file:
        shutil.copy2(src_png, texture_path)

    print("Done.")


if __name__ == "__main__":
    main()
