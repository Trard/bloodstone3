---
name: bloodstone-resourcepack-tools
description: Use scripts/extract_bbmodel_1214.py, scripts/create_icon_from_png.py, and scripts/transfer_item_namespace.py to import Blockbench .bbmodel assets, generate icon assets from PNG files, and manage model/texture/item paths in the bloodstone namespace.
---

# Bloodstone Resourcepack Tools

## Use This Skill When
- A user asks to add a new model from `new/*.bbmodel`.
- A user asks to extract model JSON and textures from a Blockbench file.
- A user asks to create an icon item/model/texture from a `.png` file.
- A user asks to create or update `assets/<namespace>/items/...` files.
- A user asks to move an item asset family from one namespace to another.
- A user asks to rename extracted texture files and fix model texture references.

## Scripts
- `scripts/extract_bbmodel_1214.py`
- `scripts/create_icon_from_png.py`
- `scripts/transfer_item_namespace.py`

## Core Workflow
1. Identify the source file and target names.
2. Run extractor script to generate one model JSON plus textures.
3. Create or update the item JSON that points to the model.
4. If texture names are unclear (for example `texture.png`), rename files and update `models/item/.../*.json` `textures` entries.
5. Verify generated paths and references.

## Create Icon Assets From A PNG
Use this when you have a flat icon texture (for example `new/firework.png`) and want blooddonate-style icon structure.

1. Run generator:
```bash
python3 scripts/create_icon_from_png.py 'new/firework.png' \
  --assets-root assets \
  --namespace bloodstone \
  --group icons \
  --name firework \
  --force
```

2. Output hierarchy:
- `assets/bloodstone/items/icons/firework.json`
- `assets/bloodstone/models/item/icons/firework.json`
- `assets/bloodstone/textures/item/icons/firework.png`

3. Verify:
```bash
cat assets/bloodstone/items/icons/firework.json
cat assets/bloodstone/models/item/icons/firework.json
find assets/bloodstone/textures/item/icons -maxdepth 1 -type f | sort
```

## Add A New Model From `new/*.bbmodel`
Use this exact procedure for new imports.

1. Choose names:
- `asset`: folder under `models/item` and `textures/item` (example: `mirror_blade`)
- `variant`: usually `default`
- `model_name`: model file name without `.json` (often same as `asset`)

2. Run extraction:
```bash
python3 scripts/extract_bbmodel_1214.py 'new/<file>.bbmodel' \
  --assets-root assets \
  --namespace bloodstone \
  --asset <asset> \
  --variant <variant> \
  --model-name <model_name> \
  --force
```

3. Create item file:
- Path: `assets/bloodstone/items/<asset>/<variant>/<model_name>.json`
- Content:
```json
{
  "model": {
    "type": "minecraft:model",
    "model": "bloodstone:item/<asset>/<variant>/<model_name>"
  }
}
```

4. If needed, rename textures and update model references:
- Rename files under `assets/bloodstone/textures/item/<asset>/<variant>/`
- Update `textures` object in `assets/bloodstone/models/item/<asset>/<variant>/<model_name>.json`
- Keep `.png.mcmeta` paired with the renamed texture filename.

5. Verify:
```bash
jq '.textures' assets/bloodstone/models/item/<asset>/<variant>/<model_name>.json
cat assets/bloodstone/items/<asset>/<variant>/<model_name>.json
find assets/bloodstone/textures/item/<asset>/<variant> -maxdepth 1 -type f | sort
```

## Namespace Transfer Workflow
Use when existing files are already in a source namespace and should be moved/copied.

```bash
python3 scripts/transfer_item_namespace.py <asset> \
  --src-namespace <src_ns> \
  --dst-namespace bloodstone \
  --variant default \
  --force
```

Useful options:
- `--item-file <name>.json` for explicit item files.
- `--item-glob '<pattern>'` for batch matching.
- `--delete-source` to remove source files after transfer.
- `--dry-run` to preview actions.

## Operational Notes
- Quote file paths containing spaces or parentheses.
- Reuse `--force` only when overwriting is intended.
- Generated models are 1.21.4-style and may include animated texture `.mcmeta` files when needed.
