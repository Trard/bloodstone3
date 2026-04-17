#!/usr/bin/env python3
"""
Fail when multiple font providers reuse the same symbol.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SymbolUse:
    file: Path
    provider_index: int
    provider_type: str
    source: str
    row: int | None
    advance: int | None
    char: str

    @property
    def codepoint(self) -> str:
        value = ord(self.char)
        width = 6 if value > 0xFFFF else 4
        return f"U+{value:0{width}X}"


def iter_provider_uses(font_file: Path, provider: dict, provider_index: int) -> Iterable[SymbolUse]:
    provider_type = str(provider.get("type", ""))
    source = str(provider.get("file", ""))

    advances = provider.get("advances")
    if isinstance(advances, dict):
        for key, value in advances.items():
            if not isinstance(key, str) or not isinstance(value, int):
                continue
            for char in key:
                yield SymbolUse(
                    file=font_file,
                    provider_index=provider_index,
                    provider_type=provider_type,
                    source=source,
                    row=None,
                    advance=value,
                    char=char,
                )

    chars = provider.get("chars")
    if isinstance(chars, list):
        for row, entry in enumerate(chars):
            if not isinstance(entry, str):
                continue
            for char in entry:
                yield SymbolUse(
                    file=font_file,
                    provider_index=provider_index,
                    provider_type=provider_type,
                    source=source,
                    row=row,
                    advance=None,
                    char=char,
                )


def describe_use(use: SymbolUse, root: Path) -> str:
    rel_file = use.file.relative_to(root)
    if use.provider_type == "space":
        return (
            f"{rel_file}: provider[{use.provider_index}] "
            f"space advance={use.advance}"
        )
    row = f" row={use.row}" if use.row is not None else ""
    source = f" file={use.source}" if use.source else ""
    return (
        f"{rel_file}: provider[{use.provider_index}] "
        f"type={use.provider_type}{source}{row}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check assets/minecraft/font/*.json for duplicate symbol assignments."
    )
    parser.add_argument(
        "--font-root",
        default="assets/minecraft/font",
        help="Font JSON root directory (default: assets/minecraft/font).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    font_root = Path(args.font_root).resolve()
    if not font_root.is_dir():
        print(f"ERROR: font root does not exist: {font_root}", file=sys.stderr)
        return 1

    symbol_map: dict[str, list[SymbolUse]] = defaultdict(list)

    for font_file in sorted(font_root.rglob("*.json")):
        data = json.loads(font_file.read_text(encoding="utf-8"))
        providers = data.get("providers")
        if not isinstance(providers, list):
            continue
        for provider_index, provider in enumerate(providers):
            if not isinstance(provider, dict):
                continue
            for use in iter_provider_uses(font_file, provider, provider_index):
                symbol_map[use.codepoint].append(use)

    duplicates = {
        codepoint: uses
        for codepoint, uses in symbol_map.items()
        if len(uses) > 1
    }

    if duplicates:
        print("Duplicate font symbols found:", file=sys.stderr)
        for codepoint, uses in sorted(duplicates.items()):
            rendered = uses[0].char
            print(f"- {codepoint} ({rendered})", file=sys.stderr)
            for use in uses:
                print(f"  {describe_use(use, font_root.parent.parent)}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(symbol_map)} unique symbol assignments across "
        f"{len(list(font_root.rglob('*.json')))} font JSON files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
