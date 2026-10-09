# PracticeRTP / PPK menu sources

Current revision: **v3**, described in `README-v3.md`; see `practice-menus-v3.bbmodel` and `quality-preview-v3-ru.png`.
The v2 source and assets below remain available for compatibility.

## Background-only menus, v2

The editable project is `practice-menus.bbmodel`. Source frames come from
`assets/bloodstone/textures/ui/gui/practice/practice_menu_ru.png`, which is not modified.
All panel artwork and the title atlas were edited/exported using Blockbench MCP.

## Geometry

- GUI width 176 px; height `114 + 18 * rows`.
- Top item origins: `(8 + 18 * column, 18 + 18 * row)`; cell borders are one pixel above/left.
- Player inventory origins: `(8 + 18 * column, 31 + 18 * menuRows + 18 * row)`; hotbar adds 4 px.
- Header is at y=2, 15 px tall. Title pixels at y=6 are 5 px tall, with fixed measured advances.
- Titles use private-use glyphs, not replacements for ASCII/Cyrillic in the global font.
- Visible controls use ordinary Minecraft items. Old v1 icon assets are retained only for older JAR compatibility; v2 uses none of them except the invisible locked filler.

## Regenerate

In the existing Blockbench project, call MCP `risky_eval` with the function from
`scripts/practice-menus-blockbench.js`, passing parsed `title-glyphs.json` as its argument.
The function updates only its named practice textures with a native Undo entry.
Then run `scripts/export-practice-menus.ps1 -SessionId <active-session> -Refresh`,
followed by `scripts/build_practice_menu_assets.py`.
Do not execute unrelated project reset/deletion commands.

`scripts/check_practice_menus.py --client-jar <1.21.11-client.jar> --plugin-source <MenuSkin.java>`
checks bitmap geometry and Java title metrics. Repeat `--plugin-source` for PPK/RTP.
`scripts/check_font_symbols.py` checks references and per-font uniqueness.
`scripts/preview_practice_menus.py --client-jar <1.21.11-client.jar>` creates a layout proof,
not an in-game capture. Block thumbnails in that proof are approximate vanilla-face projections.

## Symbols

All codepoints and copyable characters are in `symbols.tsv`.
Examples: settings panel U+E1B1 ``; tiny A U+E265 ``.
Panels occupy U+E1A8–U+E1B5; positioning uses U+E1B6/U+E1B7;
title letters occupy U+E265–U+E2BA, spaces use U+E2E3/U+E2E4.

## Verification boundary

21 PPK tests and 20 focused PracticeRTP tests pass. Full PPK JAR builds on the local toolchain.
Full PracticeRTP build still requires the private BloodLevels API. No client/server smoke test
was performed for this revision; inspect RU/EN titles, native item placement and GUI scales in-game.
