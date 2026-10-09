# Bloodstone Practice menus v3

Editable Blockbench MCP source: `practice-menus-v3.bbmodel`.
Layout contract: `v3-layouts.json`; title glyph masks: `title-glyphs.json`.
The original `practice_menu_ru.png` provides panel/header/card edges and inventory cells.
Old menu textures, models and font codepoints are preserved.

Visual refinement (2026-10-08): individual item captions and abbreviated names are removed from cooldowns, biomes, arenas and presets. Item names/descriptions remain in the existing hover tooltips. Section headings, navigation and kit/chest slot numbers remain. Unlabelled cards are centered on their native item slots; settings category cards retain one heading each, without subtitles. This is resource-pack-only: plugin slot mappings, glyph IDs and the existing v3 PPK JAR are unchanged.

## Workflow

1. Call Blockbench MCP `risky_eval` with the function from `scripts/practice-menus-v3-blockbench.js`, passing parsed title-glyphs and v3-layouts JSON. This validates label widths before modifying textures and uses native Undo.
2. Run `scripts/export-practice-menus.ps1 -SessionId <active-session> -V3 -Refresh`.
3. Run `scripts/build_practice_menus_v3.py` to register isolated background glyphs and merge only the `bloodstone.practice_ui.*` translation family.
4. Run `scripts/check_practice_menus_v3.py --practice-source <PracticeRTP-root> --ppk-source <PPK-root>` and `scripts/check_font_symbols.py`.
5. Run `scripts/preview_practice_menus_v3.py --client-jar <vanilla-1.21.11-client.jar>` to assemble proofs. This is not the artwork generator and does not change pack PNGs.

## Geometry and performance

Native item origins remain `x=8+18*column`, `y=18+18*row`. Player inventory item origins are `y=31+18*menuRows+18*row` with the usual hotbar gap. No polling/timers were added. Layouts use static textures and the title is resolved only when the menu is opened/redrawn. Visible items keep their native models; the only presentation model still used is the invisible locked filler, retaining inventory protections.

The 15 layouts have separate RU/EN variants. V3 panels use U+E46E–U+E48B; title letters and negative spacing use the existing isolated menu font. Settings examples: RU U+E480 ``, EN U+E481 ``. Complete copyable mapping: `symbols-v3.tsv`.

## Verification boundary

The previous plugin build passed 22 PPK tests and 24 focused RTP tests; complete PPK JAR built. RTP still needs the private BloodLevels API for a full build. After the resource-pack-only refinement, geometry validation passes for 30 panel PNGs, 1080 bottom cells, 76 remaining localized text placements and source slot constants. Existing v2 menu texture hashes are unchanged. Minecraft client rendering/clicks were not tested; proof block/entity icons are approximations.
