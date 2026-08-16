# Logo textures

Logo bitmap textures are kept at 255 pixels wide so every glyph stays within the resource pack's established size limit.
Wide logos are resized proportionally to a total width of `255 * fragment count`, split into equal 255-pixel fragments, and
rendered as adjacent font glyphs. Translation aliases join those glyphs with `U+E45C`, the pack's `-1`-pixel advance character.

## Split logos

| Logo | Source | Output | Assembled size | Translation key |
| --- | --- | --- | --- | --- |
| Mace Roulette (large) | `new/minecraft_title (3).png` | `textures/mace_roulette_big/logo_1.png`&ndash;`logo_3.png` | 765&times;204 | `bloodstone.logo.mace_roulette.large` |
| Mace Roulette (small) | `new/minecraft_title (3).png` | `textures/mace_roulette_small/logo_1.png`&ndash;`logo_3.png` | 765&times;204 | `bloodstone.logo.mace_roulette.small` |
| BedWars (large) | `new/Бладстоунбедру.png` | `textures/bedwars_big/logo_1.png`&ndash;`logo_4.png` | 1020&times;257 | `bloodstone.logo.bedwars.large` |
| BedWars (small) | `new/Бладстоунбедру.png` | `textures/bedwars_small/logo_1.png`&ndash;`logo_2.png` | 510&times;128 | `bloodstone.logo.bedwars.small` |

Large aliases use bitmap providers with `height: 36`; small aliases use `height: 28`. All providers use `ascent: 0`,
matching the split Meetups logos.

Mace Roulette uses three identical `255x204` glyph cells for both aliases. The proportional source is resized once to `765x202`,
centered on a transparent `765x204` canvas, and then split at x=255 and x=510. This makes every large cell exactly 45 rendered
pixels wide and every small cell exactly 35 rendered pixels wide, so `U+E45C` cancels the built-in 1-pixel glyph advance without
a gap or overlap. Keeping both cell dimensions at or below 256 pixels also lets the glyphs fit the vanilla font atlas.
