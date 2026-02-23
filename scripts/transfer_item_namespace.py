#!/usr/bin/env python3
"""
Transfer an item asset family from one namespace to another and place it in a
variant subfolder (default: "default").

Example:
  python3 assets/scripts/transfer_item_namespace.py laser \
    --src-namespace minecraft \
    --dst-namespace bloodstone \
    --variant default \
    --item-glob 'laser*.json' \
    --delete-source
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlannedCopy:
    src: Path
    dst: Path
    rewrite_json_refs: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Move/copy item JSON, model JSON, and textures for an asset family "
            "from one namespace to another and rewrite model/texture references."
        )
    )
    parser.add_argument("asset", help="Asset family name, e.g. laser")
    parser.add_argument("--src-namespace", default="minecraft")
    parser.add_argument("--dst-namespace", default="bloodstone")
    parser.add_argument(
        "--variant",
        default="default",
        help="Subfolder name to create under target asset paths (default: default).",
    )
    parser.add_argument(
        "--root",
        default=".",
        help=(
            "Assets root containing namespace folders. If omitted and './assets' "
            "contains the namespaces, that path is auto-selected."
        ),
    )
    parser.add_argument(
        "--item-glob",
        default=None,
        help=(
            "Glob under <src>/items for selecting item json files. "
            "Defaults to '<asset>*.json' when --item-file is not used."
        ),
    )
    parser.add_argument(
        "--item-file",
        action="append",
        default=[],
        help=(
            "Explicit item json filename under <src>/items. "
            "Can be passed multiple times."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination files if they already exist.",
    )
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete source files after successful copy/rewrite.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing changes.",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve_root(root: str, src_namespace: str, dst_namespace: str) -> Path:
    root_path = Path(root).resolve()
    if not root_path.exists():
        fail(f"Root path does not exist: {root_path}")
    if not root_path.is_dir():
        fail(f"Root path is not a directory: {root_path}")

    if (root_path / src_namespace).is_dir() or (root_path / dst_namespace).is_dir():
        return root_path

    nested_assets = root_path / "assets"
    if nested_assets.is_dir() and (
        (nested_assets / src_namespace).is_dir() or (nested_assets / dst_namespace).is_dir()
    ):
        return nested_assets

    return root_path


def sorted_files(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*") if p.is_file())


def collect_item_files(src_items_dir: Path, asset: str, args: argparse.Namespace) -> list[Path]:
    if args.item_file:
        item_paths: list[Path] = []
        src_items_dir_resolved = src_items_dir.resolve()
        for name in args.item_file:
            path = (src_items_dir / name).resolve()
            try:
                path.relative_to(src_items_dir_resolved)
            except ValueError:
                fail(f"--item-file must stay within source items dir: {name}")
            if not path.is_file():
                fail(f"Missing --item-file under source items dir: {path}")
            item_paths.append(path)
        return sorted(set(item_paths))

    pattern = args.item_glob or f"{asset}*.json"
    return sorted(p for p in src_items_dir.glob(pattern) if p.is_file())


def build_plan(root: Path, args: argparse.Namespace) -> tuple[list[PlannedCopy], dict[str, Path]]:
    src_items_dir = root / args.src_namespace / "items"
    src_models_dir = root / args.src_namespace / "models" / "item" / args.asset
    src_textures_dir = root / args.src_namespace / "textures" / "item" / args.asset

    dst_items_dir = root / args.dst_namespace / "items" / args.asset / args.variant
    dst_models_dir = root / args.dst_namespace / "models" / "item" / args.asset / args.variant
    dst_textures_dir = root / args.dst_namespace / "textures" / "item" / args.asset / args.variant

    item_files = collect_item_files(src_items_dir, args.asset, args)
    model_files = sorted_files(src_models_dir)
    texture_files = sorted_files(src_textures_dir)

    if not item_files and not model_files and not texture_files:
        fail(
            "No files found. Checked:\n"
            f"- items: {src_items_dir}\n"
            f"- models: {src_models_dir}\n"
            f"- textures: {src_textures_dir}"
        )

    plan: list[PlannedCopy] = []

    for src in item_files:
        plan.append(
            PlannedCopy(
                src=src,
                dst=dst_items_dir / src.name,
                rewrite_json_refs=True,
            )
        )

    for src in model_files:
        rel = src.relative_to(src_models_dir)
        plan.append(
            PlannedCopy(
                src=src,
                dst=dst_models_dir / rel,
                rewrite_json_refs=src.suffix.lower() == ".json",
            )
        )

    for src in texture_files:
        rel = src.relative_to(src_textures_dir)
        plan.append(
            PlannedCopy(
                src=src,
                dst=dst_textures_dir / rel,
                rewrite_json_refs=False,
            )
        )

    meta = {
        "src_items_dir": src_items_dir,
        "src_models_dir": src_models_dir,
        "src_textures_dir": src_textures_dir,
        "dst_items_dir": dst_items_dir,
        "dst_models_dir": dst_models_dir,
        "dst_textures_dir": dst_textures_dir,
    }
    return plan, meta


def rewrite_refs(text: str, args: argparse.Namespace) -> str:
    new_base = f"{args.dst_namespace}:item/{args.asset}/{args.variant}"
    source_patterns = (
        re.compile(
            rf'"{re.escape(args.src_namespace)}:item/{re.escape(args.asset)}(?P<suffix>/[^"]*)?"'
        ),
        re.compile(rf'"item/{re.escape(args.asset)}(?P<suffix>/[^"]*)?"'),
    )
    for pattern in source_patterns:
        text = pattern.sub(lambda m: f'"{new_base}{m.group("suffix") or ""}"', text)
    return text


def ensure_destinations(plan: list[PlannedCopy], force: bool) -> None:
    if force:
        return
    collisions = [step.dst for step in plan if step.dst.exists()]
    if collisions:
        preview = "\n".join(f"- {p}" for p in collisions[:10])
        suffix = "" if len(collisions) <= 10 else f"\n... and {len(collisions) - 10} more"
        fail(
            "Destination files already exist. Use --force to overwrite.\n"
            f"{preview}{suffix}"
        )


def execute_copy(plan: list[PlannedCopy], args: argparse.Namespace) -> None:
    copied = 0
    rewritten = 0

    for step in plan:
        updated_text: str | None = None
        if step.rewrite_json_refs and step.src.suffix.lower() == ".json":
            raw = step.src.read_text(encoding="utf-8")
            maybe_updated = rewrite_refs(raw, args)
            if maybe_updated != raw:
                updated_text = maybe_updated
                rewritten += 1

        print(f"{'DRY-RUN ' if args.dry_run else ''}COPY {step.src} -> {step.dst}")
        if args.dry_run:
            if updated_text is not None:
                print(f"DRY-RUN REWRITE {step.dst}")
            copied += 1
            continue

        step.dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(step.src, step.dst)
        copied += 1

        if updated_text is not None:
            step.dst.write_text(updated_text, encoding="utf-8")

    print(f"Copied files: {copied}")
    print(f"Rewritten JSON files: {rewritten}")


def prune_empty_dirs(start_dirs: list[Path], stop_at: Path, dry_run: bool) -> None:
    for path in sorted(set(start_dirs), key=lambda p: len(p.parts), reverse=True):
        current = path
        while current != stop_at and current.exists():
            try:
                next(current.iterdir())
                break
            except StopIteration:
                print(f"{'DRY-RUN ' if dry_run else ''}RMDIR {current}")
                if not dry_run:
                    current.rmdir()
                current = current.parent


def delete_sources(plan: list[PlannedCopy], args: argparse.Namespace, root: Path) -> None:
    deleted = 0
    source_files = sorted(set(step.src for step in plan))
    for src in source_files:
        print(f"{'DRY-RUN ' if args.dry_run else ''}DELETE {src}")
        if not args.dry_run and src.exists():
            src.unlink()
        deleted += 1

    source_dirs = [p.parent for p in source_files]
    namespace_root = root / args.src_namespace
    prune_empty_dirs(source_dirs, namespace_root, args.dry_run)
    print(f"Deleted source files: {deleted}")


def main() -> None:
    args = parse_args()
    root = resolve_root(args.root, args.src_namespace, args.dst_namespace)

    if args.src_namespace == args.dst_namespace:
        fail("--src-namespace and --dst-namespace must be different.")

    plan, meta = build_plan(root, args)
    ensure_destinations(plan, args.force)

    print("Source:")
    print(f"- items   : {meta['src_items_dir']}")
    print(f"- models  : {meta['src_models_dir']}")
    print(f"- textures: {meta['src_textures_dir']}")
    print("Target:")
    print(f"- items   : {meta['dst_items_dir']}")
    print(f"- models  : {meta['dst_models_dir']}")
    print(f"- textures: {meta['dst_textures_dir']}")
    print(f"Planned file copies: {len(plan)}")

    execute_copy(plan, args)

    if args.delete_source:
        delete_sources(plan, args, root)

    print("Done.")


if __name__ == "__main__":
    main()
