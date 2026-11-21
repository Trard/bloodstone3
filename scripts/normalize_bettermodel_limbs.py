"""Normalize generated BetterModel player_limb geometry IDs for vanilla Minecraft."""

import argparse
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile


PREFIX = "bettermodel:player_limb/"


def normalize_references(node, model_names, item):
    changed = 0
    if isinstance(node, list):
        for child in node:
            changed += normalize_references(child, model_names, item)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key == "model" and isinstance(value, str) and value.startswith(PREFIX):
                name = value[len(PREFIX):].lower()
                if name not in model_names:
                    raise ValueError(f"{item}: missing model {value}")
                if value != PREFIX + name:
                    node[key] = PREFIX + name
                    changed += 1
            else:
                changed += normalize_references(value, model_names, item)
    return changed


def normalize_bettermodel_limbs(root: Path) -> None:
    assets = root / "assets/bettermodel"
    models = assets / "models/player_limb"
    names = {}
    for path in sorted(models.glob("*.json")):
        name = path.stem.lower()
        if not re.fullmatch(r"[a-z0-9._-]+", name):
            raise ValueError(f"Invalid BetterModel geometry name: {path}")
        names.setdefault(name, []).append(path)

    renames = []
    duplicates = []
    for name, paths in names.items():
        target = models / (name + ".json")
        imported = [path for path in paths if path.name != target.name]
        if len(imported) == 1 and len(paths) == 1:
            renames.append((imported[0], target))
        elif imported:
            # Importing over a previously normalized pack can leave both copies.
            if len(paths) != 2 or len(imported) != 1 or imported[0].read_bytes() != target.read_bytes():
                raise ValueError(f"Conflicting BetterModel geometry names: {', '.join(p.name for p in paths)}")
            duplicates.append(imported[0])

    edits = {}
    for item in sorted((assets / "items/player_limb").glob("*.json")):
        data = json.loads(item.read_bytes())
        if normalize_references(data, names, item):
            edits[item] = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    # Validate all names and references before changing any files.
    for source, target in renames:
        source.rename(target)
    for duplicate in duplicates:
        duplicate.unlink()
    for item, content in edits.items():
        tmp = NamedTemporaryFile(dir=item.parent, delete=False)
        temporary = Path(tmp.name)
        try:
            with tmp:
                tmp.write(content)
            temporary.chmod(item.stat().st_mode)
            temporary.replace(item)
        finally:
            temporary.unlink(missing_ok=True)
    if renames or duplicates or edits:
        print(f"BetterModel player_limb: renamed {len(renames)} models, removed {len(duplicates)} identical copies, updated {len(edits)} items")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Resource pack root (default: current directory)")
    try:
        normalize_bettermodel_limbs(parser.parse_args().root)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
