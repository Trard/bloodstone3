# SMP Mechanism crate

Cubic copper case for BloodDonate's SMP `mechanism` crate, simplified to match the coarse pixel-art style of the resource pack's civilization weapons and hats. The copper palette follows `copper_golem_mask/normal`, and the muted gold/turquoise accent follows `midas_sword`. One large winding gear serves as the lock; the shell has a simple lid seam and sparse broad color patches. No rivets, pipework, small fittings, noise or scratches.

17 cubes, 84 exported quads / 168 triangles, two opaque textures of exactly 16×16 pixels. No animation or shader dependency. The earlier detailed design had 74 cubes and a 256×256 texture.

`mechanism_crate.bbmodel` is the editable Java Block/Item source. `preview.png` shows the model; `display_views.png` contains the Blockbench review views. These are editor renders, not Minecraft screenshots.

The existing plugin issues `CHEST` with CustomModelData `3333` in `SmpHatCrate.getItem()` and `smp_crates.yml`. The resource pack now maps that value to `blooddonate:item/crates/mechanism/default/mechanism` in both chest dispatch files. Existing higher thresholds are preserved. The separate store/menu icon `blooddonate:icons/crates/mechanism` remains independent.

The direct item model ID is `blooddonate:crates/mechanism/default/mechanism`. Its runtime files are under `assets/blooddonate/{items,models/item,textures/item}/crates/mechanism/default/`.

The approved source and runtime files are also saved in the BloodDonate project under `src/main/resources/crates/mechanism/`: `smp_item.bbmodel`, `smp_item_model.json`, `smp_item.json`, `mechanism_copper.png`, and `mechanism_metal.png`. The existing `model.bbmodel` in that directory is the separate animated minigame crate used by BetterModel. When editing this SMP item again, synchronize the five copies explicitly after extraction.

All eight display contexts were inspected in Blockbench: GUI, dropped item, fixed/frame, head, and left/right first/third person. First-person transforms show the winding face above the screen edge; third-person and fixed transforms face the gear outwards. The previously reviewed transforms were retained. Native Java codec export and asset-reference checks pass. In-game rendering and performance have not been measured.

The shell and gear front use one texture pixel per model unit. The seam, base and spindle sample small solid-color swatches intentionally. The ten-pixel cog silhouette uses full-unit steps, with its front UVs continuous across adjacent geometry strips.

To regenerate the authored source and extract the runtime model from the resource-pack root:

```sh
python3 scripts/create_mechanism_crate.py
python3 scripts/extract_bbmodel_1214.py integrations/blooddonate/mechanism/mechanism_crate.bbmodel --assets-root assets --namespace blooddonate --group crates --asset mechanism --variant default --model-name mechanism --item-mode update --item-name mechanism --force
```

Regeneration replaces manual source changes with the procedural design. It does not build or publish the resource pack or compile the plugin.
