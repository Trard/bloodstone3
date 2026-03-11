---
name: bloodstone-resourcepack-tools
description: Use scripts/add_suffix.py, scripts/extract_bbmodel_1214.py, scripts/create_icon_from_png.py, and scripts/transfer_item_namespace.py to add bitmap font suffixes, import Blockbench .bbmodel assets, generate icon assets from PNG files, and manage model/texture/item paths in this resource pack's namespaces.
---

# Bloodstone Resourcepack Tools

## Use This Skill When
- A user asks to add or update a suffix PNG in `assets/minecraft/font/suffixes.json`.
- A user asks to add a new model from `new/*.bbmodel`.
- A user asks to extract model JSON and textures from a Blockbench file.
- A user asks to create an icon item/model/texture from a `.png` file.
- A user asks to create or update `assets/<namespace>/items/...` files.
- A user asks to move an item asset family from one namespace to another.
- A user asks to rename extracted texture files and fix model texture references.

## Scripts
- `scripts/add_suffix.py`
- `scripts/extract_bbmodel_1214.py`
- `scripts/create_icon_from_png.py`
- `scripts/transfer_item_namespace.py`

## Core Workflow
1. Identify the source file and target names.
2. Run extractor script to generate one model JSON plus textures.
3. Create or update the item JSON that points to the model.
4. If texture names are unclear (for example `texture.png`), rename files and update `models/item/.../*.json` `textures` entries.
5. Verify generated paths and references.

## Add Or Update A Font Suffix From PNG
Use this when you have a flat suffix image for `assets/minecraft/textures/font/suffixes/*.png`.

1. Choose a clear English suffix name.
- If the source filename is opaque like `image_2026...png`, inspect the image or ask the user for the intended English name.
- If the source name is non-English, translate it to an English asset name before running the script.

2. Run the generator:
```bash
python3 scripts/add_suffix.py 'new/builder.png' \
  --assets-root assets \
  --name builder
```

3. Useful options:
- `--dry-run` to preview the assigned codepoint and file writes.
- `--force` to replace an existing suffix texture/provider in place.
- `--codepoint E016` to pin an explicit private-use codepoint when needed.

4. What the script does:
- Copies the texture to `assets/minecraft/textures/font/suffixes/<name>.png`
- Adds or updates the provider in `assets/minecraft/font/suffixes.json`
- Auto-picks the next free private-use codepoint across `assets/minecraft/font/*.json`

5. After running it, always report both:
- the symbol code (for example `\uE016`)
- the rendered symbol character (for example ``)

## Create Icon Assets From A PNG
Use this when you have a flat icon texture (for example `new/firework.png`) and want blooddonate-style icon structure.

Default for this pack: icon assets live in the `minecraft` namespace unless the user explicitly asks for a different namespace.

1. Run generator:
```bash
python3 scripts/create_icon_from_png.py 'new/firework.png' \
  --assets-root assets \
  --namespace minecraft \
  --group icons \
  --name firework \
  --force
```

2. Output hierarchy:
- `assets/minecraft/items/icons/firework.json`
- `assets/minecraft/models/item/icons/firework.json`
- `assets/minecraft/textures/item/icons/firework.png`

3. Verify:
```bash
cat assets/minecraft/items/icons/firework.json
cat assets/minecraft/models/item/icons/firework.json
find assets/minecraft/textures/item/icons -maxdepth 1 -type f | sort
```

## Add A New Model From `new/*.bbmodel`
Use this exact procedure for new imports.

1. Choose names:
- `asset`: folder under `models/item` and `textures/item` (example: `mirror_blade`)
- `variant`: usually `default`
- `model_name`: model file name without `.json` (often same as `asset`)
- `group` (optional): folder between `item/` and `<asset>` (example: `tools`)

2. Run extraction:
```bash
python3 scripts/extract_bbmodel_1214.py 'new/<file>.bbmodel' \
  --assets-root assets \
  --namespace bloodstone \
  --group <group> \
  --asset <asset> \
  --variant <variant> \
  --model-name <model_name> \
  --item-mode create \
  --item-name <model_name> \
  --force
```

3. Item file is created automatically when `--item-mode create` is used.

4. If needed, rename textures and update model references:
- Rename files under `assets/bloodstone/textures/item/<group>/<asset>/<variant>/`
- Update `textures` object in `assets/bloodstone/models/item/<group>/<asset>/<variant>/<model_name>.json`
- Keep `.png.mcmeta` paired with the renamed texture filename.

5. Verify:
```bash
jq '.textures' assets/bloodstone/models/item/<group>/<asset>/<variant>/<model_name>.json
cat assets/bloodstone/items/<group>/<asset>/<variant>/<model_name>.json
find assets/bloodstone/textures/item/<group>/<asset>/<variant> -maxdepth 1 -type f | sort
```

## Update Existing Model In Place
Use this to overwrite an existing model file (for example `harpoon`) and update its existing item JSON, without creating a new model name.

```bash
python3 scripts/extract_bbmodel_1214.py 'new/blood_harpoon_pull (2).bbmodel' \
  --assets-root assets \
  --namespace bloodstone \
  --group tools \
  --asset bloodsword \
  --variant default \
  --update-existing-model harpoon \
  --item-mode update \
  --item-name harpoon \
  --force
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
