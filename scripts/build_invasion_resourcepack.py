#!/usr/bin/env python3
import argparse
import os
import tempfile
import zipfile
from pathlib import Path

from build_resourcepack_zip import build_include_list, load_pack_mcmeta


def main():
    parser = argparse.ArgumentParser(description="Build the full resource pack for Invasion.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    entries = {}
    for name in build_include_list(root, load_pack_mcmeta(root)):
        source = root / name
        for path in sorted(source.rglob("*")) if source.is_dir() else [source]:
            if path.is_file():
                entries[path.relative_to(root).as_posix()] = path
    variant = root / "variants/invasion"
    expected = {
        "assets/minecraft/textures/gui/sprites/boss_bar/white_background.png",
        "assets/minecraft/textures/gui/sprites/boss_bar/white_progress.png",
    }
    overrides = {
        path.relative_to(variant).as_posix(): path
        for path in variant.rglob("*") if path.is_file()
    }
    if overrides.keys() != expected:
        raise SystemExit("The Invasion variant must contain only the two white boss-bar textures.")
    if output in entries.values() or output in overrides.values():
        raise SystemExit("Output must not overwrite a resource.")
    entries.update(overrides)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(suffix=".zip", dir=output.parent)
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, path in sorted(entries.items()):
                archive.write(path, name)
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(output)


if __name__ == "__main__":
    main()
