#!/usr/bin/env python3
"""Find model files unreachable from the resource pack's item and block mappings.

Examples:
    python3 scripts/audit_unused_models.py --output /tmp/model-audit.csv
    python3 scripts/audit_unused_models.py --namespace civilization --list
    python3 scripts/audit_unused_models.py --textures --output /tmp/asset-audit.csv
    python3 scripts/audit_unused_models.py --vanilla-jar /path/to/1.21.11.jar --output /tmp/model-audit.csv

The audit never changes assets. It follows model/parent references, including nested item definitions,
blockstates, legacy Minecraft overrides, and pack.mcmeta overlays. Every item definition is an entry
point because servers can select custom item IDs. Unreachable means unused by the audited resource-pack
mappings. Texture references do not count as model references. Literal asset paths and unambiguous PNG
filenames in local scripts/integrations are retained as tooling dependencies as well.

Vanilla JARs are optional and repeatable. Their JSON assets supply fallback mappings and dependencies;
vanilla model replacements are conservatively retained for implicit game rendering. Without JARs,
unreachable minecraft models are marked unverified. Custom namespaces are still audited normally.
Use --textures to include PNG textures and their .png.mcmeta sidecars. This traces reachable models,
fonts, particles, equipment, item renderers, shader JSON, and explicit atlas sources. Directory atlas
inclusion alone is not proof of rendering. Vanilla texture replacements are conservatively retained.
Unreferenced textures are unused regardless of their folder. The unverified status is reserved for
minecraft assets when no vanilla JAR was supplied to check built-in replacements. Supply JARs for the
game versions you want checked. This is a static audit, not an automatic texture-deletion tool.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator


@dataclass
class Asset:
    kind: str
    identifier: str
    data: dict[str, Any]
    path: Path | None = None


def model_references(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            is_special_base = key == "base" and value.get("type", "").removeprefix("minecraft:") == "special"
            if (key in {"parent", "model"} or is_special_base) and isinstance(child, str):
                yield child if ":" in child else f"minecraft:{child}"
            elif isinstance(child, (dict, list)):
                yield from model_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from model_references(child)


def asset_key(relative: PurePosixPath, textures: bool = False) -> tuple[str, str] | None:
    parts = relative.parts
    if len(parts) < 3:
        return None
    if textures and parts[1] == "textures":
        suffix = ".png.mcmeta" if relative.name.endswith(".png.mcmeta") else ".png"
        if not relative.name.endswith(suffix):
            return None
        kind = "texture_metadata" if suffix == ".png.mcmeta" else "textures"
        return kind, f"{parts[0]}:{PurePosixPath(*parts[2:]).as_posix().removesuffix(suffix)}"
    if relative.suffix != ".json" or (not textures and parts[1] not in {"models", "items", "blockstates"}):
        return None
    return parts[1], f"{parts[0]}:{PurePosixPath(*parts[2:]).with_suffix('').as_posix()}"


def load_layer(directory: Path, textures: bool = False) -> dict[tuple[str, str], Asset]:
    assets = {}
    pattern = "*/*/**/*" if textures else "*/*/**/*.json"
    for path in sorted(directory.glob(pattern)):
        if not path.is_file():
            continue
        key = asset_key(PurePosixPath(path.relative_to(directory).as_posix()), textures)
        if key:
            data = {} if key[0] == "textures" else json.loads(path.read_text(encoding="utf-8"))
            assets[key] = Asset(*key, data, path)
    return assets


def format_range(data: dict[str, Any], fallback: int = 0) -> tuple[int, int]:
    formats = data.get("formats", data.get("supported_formats", data.get("pack_format", fallback)))
    if isinstance(formats, int):
        low = high = formats
    elif isinstance(formats, list):
        low, high = formats
    else:
        low, high = formats["min_inclusive"], formats["max_inclusive"]
    # Newer metadata permits [major, minor] versions. Overlay selection here uses the major format.
    low, high = data.get("min_format", low), data.get("max_format", high)
    return (low[0] if isinstance(low, list) else low, high[0] if isinstance(high, list) else high)


def load_vanilla(path: Path, textures: bool = False) -> tuple[int, dict[tuple[str, str], Asset]]:
    assets = {}
    with zipfile.ZipFile(path) as archive:
        version = json.loads(archive.read("version.json"))["pack_version"]
        pack_format = version.get("resource_major", version.get("resource"))
        if not isinstance(pack_format, int):
            raise ValueError(f"Cannot determine resource pack format from {path}")
        for name in archive.namelist():
            if not name.startswith("assets/"):
                continue
            key = asset_key(PurePosixPath(name.removeprefix("assets/")), textures)
            if key:
                assets[key] = Asset(*key, {} if key[0] == "textures" else json.loads(archive.read(name)))
    if not assets:
        raise ValueError(f"No vanilla JSON assets found in {path}")
    return pack_format, assets


def trace(assets: dict[tuple[str, str], Asset], vanilla_models: set[str], tooling: dict[str, str] | None = None) -> tuple[set[str], dict[str, str]]:
    models = {identifier: asset for (kind, identifier), asset in assets.items() if kind == "models"}
    reasons = {identifier: "vanilla model replacement (conservatively retained)" for identifier in vanilla_models}
    reasons.update(tooling or {})
    for (kind, identifier), asset in assets.items():
        if kind in {"items", "blockstates"}:
            for target in model_references(asset.data):
                reasons.setdefault(target, f"{kind}: {identifier}")
        elif kind == "models" and identifier.startswith("minecraft:") and asset.data.get("overrides"):
            reasons.setdefault(identifier, "legacy Minecraft overrides")
    pending = list(reasons)
    visited = set()
    while pending:
        identifier = pending.pop()
        if identifier in visited:
            continue
        visited.add(identifier)
        if identifier not in models:
            continue
        for target in model_references(models[identifier].data):
            reasons.setdefault(target, f"model dependency: {identifier}")
            if target not in visited:
                pending.append(target)
    return visited, reasons


def string_values(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from string_values(child)


def texture_id(value: str) -> str:
    namespace, _, name = value.partition(":") if ":" in value else ("minecraft", ":", value)
    return f"{namespace}:{name.removeprefix('textures/').removesuffix('.png')}"


def tooling_references(root: Path, files: dict[Path, Asset]) -> dict[tuple[str, str], str]:
    sources = []
    for directory in (root / "scripts", root / "integrations"):
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".ps1", ".sh", ".json", ".yml", ".yaml"}:
                source = path.read_text(encoding="utf-8")
                png_literals = set(re.findall(r'''["']([^"'\n]+\.png)["']''', source))
                sources.append((path, source, png_literals))
    texture_filenames = defaultdict(set)
    for asset in files.values():
        if asset.kind == "textures":
            texture_filenames[asset.path.name].add(asset.identifier)
    references = {}
    for asset in files.values():
        if asset.kind == "texture_metadata":
            continue
        _, resource = asset.identifier.split(":", 1)
        relative = f"{asset.kind}/{resource}{'.json' if asset.kind == 'models' else '.png'}"
        for path, source, png_literals in sources:
            # Match the full resource ID or path suffix; preserve templates even when namespace paths are assembled.
            unique_png_literal = (asset.kind == "textures" and len(texture_filenames[asset.path.name]) == 1
                                  and asset.path.name in png_literals)
            if asset.identifier in source or relative in source or unique_png_literal:
                references[(asset.kind, asset.identifier)] = f"local tooling reference: {path.relative_to(root)}"
                break
    return references


def trace_textures(assets: dict[tuple[str, str], Asset], reached: set[str], vanilla_textures: set[str]) -> dict[str, str]:
    textures = {identifier for kind, identifier in assets if kind == "textures"}
    reasons = {identifier: "vanilla texture replacement (conservatively retained)" for identifier in vanilla_textures}
    aliases = defaultdict(set)
    directories = []
    for (kind, identifier), asset in assets.items():
        if kind != "atlases":
            continue
        for source in asset.data.get("sources", []):
            source_type = source.get("type", "").removeprefix("minecraft:")
            if source_type == "single":
                aliases[texture_id(source.get("sprite", source["resource"]))].add(texture_id(source["resource"]))
            elif source_type == "unstitch":
                for region in source.get("regions", []):
                    aliases[texture_id(region["sprite"])].add(texture_id(source["resource"]))
            elif source_type == "directory":
                directories.append((source.get("prefix", ""), source["source"].rstrip("/") + "/"))

    def mark(value: str, reason: str) -> None:
        if value.startswith("#"):
            return
        identifier = texture_id(value)
        targets = {identifier} | aliases.get(identifier, set())
        namespace, name = identifier.split(":", 1)
        for prefix, source in directories:
            if name.startswith(prefix):
                targets.add(f"{namespace}:{source}{name[len(prefix):]}")
        for target in targets & textures:
            reasons.setdefault(target, reason)

    for (kind, identifier), asset in assets.items():
        if kind in {"textures", "texture_metadata", "lang"}:
            continue
        if kind == "models":
            if identifier not in reached:
                continue
            # Keep concrete inherited texture slots, even when a child overrides one: conservative retention.
            for value in string_values(asset.data.get("textures", {})):
                mark(value, f"reachable model: {identifier}")
            continue
        reason = f"{kind}: {identifier}"
        # Fonts can be selected directly. Scan resource strings in other JSON assets conservatively too.
        for value in string_values(asset.data):
            mark(value, reason)
        if kind == "equipment":
            for layer_type, layers in asset.data.get("layers", {}).items():
                for layer in layers:
                    namespace, name = texture_id(layer["texture"]).split(":", 1)
                    mark(f"{namespace}:entity/equipment/{layer_type}/{name}", reason)
        if kind == "items":
            def special_textures(node: Any) -> None:
                if isinstance(node, dict):
                    value = node.get("texture")
                    if isinstance(value, str):
                        namespace, name = texture_id(value).split(":", 1)
                        model_type = node.get("type", "").removeprefix("minecraft:")
                        directory = {"bed": "bed", "chest": "chest", "shulker_box": "shulker"}.get(model_type)
                        if directory:
                            mark(f"{namespace}:entity/{directory}/{name}", reason)
                    sprite = node.get("sprite")
                    if isinstance(sprite, str):
                        namespace, name = texture_id(sprite).split(":", 1)
                        mark(f"{namespace}:gui/sprites/{name}", reason)
                    for child in node.values():
                        special_textures(child)
                elif isinstance(node, list):
                    for child in node:
                        special_textures(child)
            special_textures(asset.data)
    for identifier in textures:
        if identifier.endswith(("_e", "_n", "_s")) and identifier[:-2] in reasons:
            reasons.setdefault(identifier, f"possible emissive/PBR companion of used texture: {identifier[:-2]}")
    return reasons


def audit(root: Path, vanilla_jars: list[Path], textures: bool = False) -> list[dict[str, str]]:
    metadata = json.loads((root / "pack.mcmeta").read_text(encoding="utf-8"))
    minimum, maximum = format_range(metadata["pack"])
    base = load_layer(root / "assets", textures)
    overlays = []
    for entry in metadata.get("overlays", {}).get("entries", []):
        directory = (root / entry["directory"]).resolve()
        if not directory.is_relative_to(root.resolve()):
            raise ValueError(f"Overlay directory escapes the resource pack: {entry['directory']}")
        overlays.append((entry["directory"], format_range(entry), load_layer(directory / "assets", textures)))
    files = {asset.path: asset for layer in [base, *(layer for _, _, layer in overlays)]
             for asset in layer.values() if asset.kind in {"models", "textures", "texture_metadata"}}
    tooling = tooling_references(root, files)
    # Evaluate every distinct overlay combination, including overlapping ranges and the base fallback.
    boundaries = {minimum}
    for _, (low, high), _ in overlays:
        boundaries.update(n for n in (low, high + 1) if minimum <= n <= maximum)
    scenarios = [(number, {}, f"pack format {number}") for number in sorted(boundaries)]
    for jar in vanilla_jars:
        number, vanilla = load_vanilla(jar, textures)
        if not minimum <= number <= maximum:
            raise ValueError(f"Vanilla JAR {jar} uses format {number}, outside supported range {minimum}–{maximum}")
        scenarios.append((number, vanilla, f"vanilla {jar.stem}, format {number}"))
    used = {}
    active = set()
    for number, vanilla, label in scenarios:
        effective = dict(vanilla)
        effective.update(base)
        for _, (low, high), layer in overlays:
            if low <= number <= high:
                effective.update(layer)
        vanilla_models = {identifier for kind, identifier in vanilla if kind == "models"}
        reached, reasons = trace(effective, vanilla_models, {identifier: reason for (kind, identifier), reason in tooling.items() if kind == "models"})
        texture_reasons = trace_textures(effective, reached, {identifier for kind, identifier in vanilla if kind == "textures"}) if textures else {}
        texture_reasons.update({identifier: reason for (kind, identifier), reason in tooling.items() if kind == "textures"})
        for (kind, identifier), asset in effective.items():
            if kind in {"models", "textures", "texture_metadata"} and asset.path is not None:
                active.add(asset.path)
                if kind == "models" and identifier in reached:
                    used.setdefault(asset.path, (label, reasons[identifier]))
                elif kind != "models" and identifier in texture_reasons:
                    used.setdefault(asset.path, (label, texture_reasons[identifier]))
    rows = []
    for path, asset in sorted(files.items()):
        namespace = asset.identifier.split(":", 1)[0]
        scenario, reason = used.get(path, ("", "No path from item definitions, blockstates, or legacy mappings"))
        status = "used" if path in used else "unused"
        if status == "unused" and path not in active:
            reason = "Never selected within the pack's supported overlay formats"
        elif status == "unused" and namespace == "minecraft" and not vanilla_jars:
            status, reason = "unverified", "Supply --vanilla-jar to check implicit vanilla usage"
        if asset.kind != "models" and status == "unused" and path in active:
            reason = "No reference from models, fonts, atlases, item/equipment/shader JSON, or local tooling"
            if vanilla_jars:
                reason += "; no matching vanilla texture in supplied game versions"
        rows.append({"kind": asset.kind, "status": status, "namespace": namespace, "resource": asset.identifier,
                     "file": path.relative_to(root).as_posix(), "reason": reason, "scenario": scenario})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Resource pack directory")
    parser.add_argument("--vanilla-jar", type=Path, action="append", default=[], help="Game JAR; repeat for multiple versions")
    parser.add_argument("--namespace", action="append", help="Filter report namespaces; dependencies are still traced globally")
    parser.add_argument("--textures", action="store_true", help="Include PNG textures and animation metadata in the audit")
    parser.add_argument("--output", type=Path, help="Write a CSV of all audited asset statuses (assets are never changed)")
    parser.add_argument("--list", action="store_true", help="Also print every unused or unverified asset path")
    args = parser.parse_args()
    try:
        rows = audit(args.root.resolve(), args.vanilla_jar, args.textures)
        if args.namespace:
            rows = [row for row in rows if row["namespace"] in args.namespace]
        if args.output:
            output = args.output.resolve()
            root = args.root.resolve()
            if output.is_relative_to(root) and ("assets" in output.relative_to(root).parts or output.suffix != ".csv"):
                raise ValueError("Report inside the pack must be a .csv outside asset directories")
            with output.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["kind", "status", "namespace", "resource", "file", "reason", "scenario"])
                writer.writeheader()
                writer.writerows(rows)
        counts = defaultdict(Counter)
        for row in rows:
            counts[(row["kind"], row["namespace"])][row["status"]] += 1
        print(f"{'Kind / namespace':<38} {'Used':>8} {'Unused':>8} {'Unverified':>12} {'Total':>8}")
        for (kind, namespace), count in sorted(counts.items()):
            print(f"{kind + ' / ' + namespace:<38} {count['used']:>8} {count['unused']:>8} {count['unverified']:>12} {sum(count.values()):>8}")
        total = Counter(row["status"] for row in rows)
        print(f"{'TOTAL':<38} {total['used']:>8} {total['unused']:>8} {total['unverified']:>12} {len(rows):>8}")
        print("Unused means unreachable in the audited mappings. Local tooling literals are retained; external or computed references are not resolved.")
        if not args.vanilla_jar:
            print("Vanilla fallback mappings were not checked. Add --vanilla-jar for each relevant game version.")
        if args.list:
            for row in rows:
                if row["status"] != "used":
                    print(f"{row['status']}: {row['file']}")
        if args.output:
            print(f"Report: {args.output.resolve()}")
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
