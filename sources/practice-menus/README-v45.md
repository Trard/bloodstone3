# v4.5 — slot outlines only beneath controls

The previous full kit/cooldown grid was a misinterpretation of the requested
button slots. Kit settings now have 16 outlines, cooldown settings 12; positions
and actions remain exactly as in PPK 1.7.0-menus4.4. Empty cells have a plain
background. The three category buttons use the same 18px recessed slot border,
replacing their faint oversized frames.

Biome selection returns to three rows: slots 11–15 and 22. Arenas return to
11, 12, 14, 15. These menus also draw native 18px slots only under controls,
without white cards or item-model overrides. Their materials are unchanged.
Use PracticeRTP 1.1-menus4.5 with this pack for the restored positions/height.
PPK does not need another update after menus4.4.

Only ten runtime PNGs differ from v4.4: biomes, arenas, settings, kit_settings
and cooldowns, in RU/EN. Queue, kit numbers, home-menu bottom slots, font files,
translations, hats and every other resource remain byte-identical.

Rendered and exported through the Blockbench MCP into practice-menus-v4.bbmodel.
Reproduce using prepare_practice_menus_v4.py --layout-only followed by
Invoke-PracticeBlockbench.ps1 -Task Menus -Refresh -SessionId <id>.
Validation: check_practice_menus_v4.py checks every used AND unused top-menu cell;
verify_practice_pack_v41.py --controls-v45 compares the ZIP to v4.4.
No live Minecraft client/server test was performed.
