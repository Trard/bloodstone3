#!/usr/bin/env python3
"""
Build a clean resource-pack ZIP from the repo root.

Included by default:
  - pack.mcmeta
  - pack.png (if present)
  - assets/
  - overlay directories declared in pack.mcmeta
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the resource-pack ZIP using the system zip command."
    )
    parser.add_argument(
        "--root",
        default=".",
        help=(
            "Resource-pack root directory (default: current directory). "
            "Use a Linux/WSL path like /mnt/c/users/name/resourcepacks/pack."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output ZIP path (default: <root-name>.zip in the root directory).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory where <root-name>.zip should be written. "
            "Use a Linux/WSL path like /mnt/c/users/name/resourcepacks."
        ),
    )
    parser.add_argument(
        "--compression",
        type=int,
        default=0,
        choices=range(0, 10),
        metavar="0-9",
        help="zip compression level, where 0 is fastest and 9 is smallest (default: 0).",
    )
    return parser.parse_args()


def load_pack_mcmeta(root: Path) -> dict:
    pack_file = root / "pack.mcmeta"
    if not pack_file.is_file():
        raise SystemExit(f"ERROR: Missing pack.mcmeta: {pack_file}")
    return json.loads(pack_file.read_text(encoding="utf-8"))


def build_include_list(root: Path, pack_mcmeta: dict) -> list[str]:
    includes: list[str] = ["pack.mcmeta", "assets"]

    if (root / "pack.png").is_file():
        includes.append("pack.png")

    overlays = pack_mcmeta.get("overlays", {}).get("entries", [])
    if isinstance(overlays, list):
        for entry in overlays:
            if not isinstance(entry, dict):
                continue
            directory = entry.get("directory")
            if not isinstance(directory, str) or not directory:
                continue
            overlay_path = root / directory
            if not overlay_path.exists():
                raise SystemExit(
                    f"ERROR: Overlay directory declared in pack.mcmeta is missing: {directory}"
                )
            includes.append(directory)

    # Preserve order while dropping duplicates.
    return list(dict.fromkeys(includes))


def normalize_path(raw: str) -> Path:
    return Path(raw).expanduser().resolve()


def replace_output(src: Path, dest: Path) -> None:
    cp_bin = shutil.which("cp")
    if cp_bin is None:
        raise SystemExit("ERROR: cp command is not available in PATH.")
    subprocess.run([cp_bin, "-f", str(src), str(dest)], check=True)


def main() -> int:
    args = parse_args()
    root = normalize_path(args.root)
    if not root.is_dir():
        print(f"ERROR: Resource-pack root does not exist: {root}", file=sys.stderr)
        return 1

    zip_bin = shutil.which("zip")
    if zip_bin is None:
        print("ERROR: zip command is not available in PATH.", file=sys.stderr)
        return 1

    pack_mcmeta = load_pack_mcmeta(root)
    includes = build_include_list(root, pack_mcmeta)

    if args.output and args.output_dir:
        print("ERROR: Use either --output or --output-dir, not both.", file=sys.stderr)
        return 1

    if args.output:
        output = normalize_path(args.output)
    elif args.output_dir:
        output_dir = normalize_path(args.output_dir)
        output = output_dir / f"{root.name}.zip"
    else:
        output = root / f"{root.name}.zip"

    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"{root.name}-zip-") as temp_dir:
        temp_output = Path(temp_dir) / output.name
        cmd = [
            zip_bin,
            f"-{args.compression}",
            "-q",
            "-r",
            str(temp_output),
            *includes,
        ]
        subprocess.run(cmd, cwd=root, check=True)
        replace_output(temp_output, output)

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
