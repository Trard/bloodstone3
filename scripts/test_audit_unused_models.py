#!/usr/bin/env python3
"""Reference graph regression checks; run with python3 scripts/test_audit_unused_models.py."""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from audit_unused_models import audit


class ModelAuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write("pack.mcmeta", {"pack": {"pack_format": 46, "supported_formats": [46, 75]}})

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data), encoding="utf-8")

    def statuses(self, jars=None):
        return {row["file"]: row["status"] for row in audit(self.root, jars or [])}

    def texture(self, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"PNG contents are not needed for a reference audit")

    def test_nested_items_parents_dead_chains_cycles_and_texture_names(self):
        self.write("assets/test/items/weapon.json", {"model": {"type": "condition", "on_true": {"model": "test:item/live"}}})
        self.write("assets/test/models/item/live.json", {"parent": "test:item/base", "textures": {"0": "test:item/texture_only"}})
        self.write("assets/test/models/item/base.json", {})
        self.write("assets/test/models/item/texture_only.json", {})
        self.write("assets/test/models/item/preview.json", {"parent": "test:item/dead"})
        self.write("assets/test/models/item/dead.json", {})
        self.write("assets/test/models/item/cycle_a.json", {"parent": "test:item/cycle_b"})
        self.write("assets/test/models/item/cycle_b.json", {"parent": "test:item/cycle_a"})
        result = self.statuses()
        for name in ("live", "base"):
            self.assertEqual(result[f"assets/test/models/item/{name}.json"], "used")
        for name in ("texture_only", "preview", "dead", "cycle_a", "cycle_b"):
            self.assertEqual(result[f"assets/test/models/item/{name}.json"], "unused")

    def test_blockstates_and_legacy_overrides(self):
        self.write("assets/test/blockstates/block.json", {"multipart": [{"apply": [{"model": "test:block/custom"}]}]})
        self.write("assets/test/models/block/custom.json", {})
        self.write("assets/minecraft/models/item/stick.json", {"overrides": [{"model": "test:item/legacy"}]})
        self.write("assets/test/models/item/legacy.json", {})
        self.write("assets/minecraft/models/item/unmapped.json", {})
        result = self.statuses()
        self.assertEqual(result["assets/test/models/block/custom.json"], "used")
        self.assertEqual(result["assets/test/models/item/legacy.json"], "used")
        self.assertEqual(result["assets/minecraft/models/item/unmapped.json"], "unverified")

    def test_special_renderer_base_and_local_generation_template(self):
        self.write("assets/test/items/banner.json", {"model": {"type": "minecraft:special", "base": "test:item/banner",
                                                               "model": {"type": "minecraft:banner"}}})
        self.write("assets/test/models/item/banner.json", {})
        self.write("assets/test/models/item/template.json", {"textures": {"0": "test:item/template"}})
        self.texture("assets/test/textures/item/template.png")
        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "generate.py").write_text('template = assets / "models/item/template.json"', encoding="utf-8")
        result = {row["file"]: row["status"] for row in audit(self.root, [], textures=True)}
        self.assertTrue(all(status == "used" for status in result.values()))

    def test_overlays_preserve_base_usage_and_follow_overridden_dependencies(self):
        self.write("pack.mcmeta", {"pack": {"pack_format": 46, "supported_formats": [46, 75]},
                                  "overlays": {"entries": [{"directory": "new", "formats": 75}]}})
        self.write("assets/test/items/weapon.json", {"model": {"model": "test:item/weapon"}})
        self.write("assets/test/models/item/weapon.json", {"parent": "test:item/old_base"})
        self.write("assets/test/models/item/old_base.json", {})
        self.write("assets/test/models/item/new_base.json", {})
        self.write("new/assets/test/models/item/weapon.json", {"parent": "test:item/new_base"})
        self.assertTrue(all(status == "used" for status in self.statuses().values()))

    def test_overlapping_overlays_respect_order(self):
        self.write("pack.mcmeta", {"pack": {"pack_format": 75}, "overlays": {"entries": [
            {"directory": "first", "formats": 75}, {"directory": "second", "formats": 75}]}})
        self.write("assets/test/items/weapon.json", {"model": {"model": "test:item/weapon"}})
        self.write("first/assets/test/models/item/weapon.json", {})
        self.write("second/assets/test/models/item/weapon.json", {})
        result = self.statuses()
        self.assertEqual(result["first/assets/test/models/item/weapon.json"], "unused")
        self.assertEqual(result["second/assets/test/models/item/weapon.json"], "used")

    def test_vanilla_fallback_and_implicit_model_replacements(self):
        jar = self.root / "vanilla.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            for path, data in {
                "version.json": {"pack_version": {"resource_major": 75}},
                "assets/minecraft/items/stick.json": {"model": {"model": "minecraft:item/stick"}},
                "assets/minecraft/models/item/stick.json": {},
                "assets/minecraft/models/item/shield.json": {},
            }.items():
                archive.writestr(path, json.dumps(data))
        self.write("assets/minecraft/models/item/stick.json", {"parent": "test:item/base"})
        self.write("assets/test/models/item/base.json", {})
        self.write("assets/minecraft/models/item/shield.json", {})
        self.write("assets/minecraft/models/item/custom_orphan.json", {})
        result = self.statuses([jar])
        self.assertEqual(result["assets/minecraft/models/item/stick.json"], "used")
        self.assertEqual(result["assets/test/models/item/base.json"], "used")
        self.assertEqual(result["assets/minecraft/models/item/shield.json"], "used")
        self.assertEqual(result["assets/minecraft/models/item/custom_orphan.json"], "unused")

    def test_shared_textures_inherited_textures_and_dead_model_textures(self):
        self.write("assets/test/items/live.json", {"model": {"model": "test:item/live"}})
        self.write("assets/test/models/item/live.json", {"parent": "test:item/base", "textures": {"0": "test:item/shared"}})
        self.write("assets/test/models/item/base.json", {"textures": {"particle": "test:item/inherited"}})
        self.write("assets/test/models/item/dead.json", {"textures": {"0": "test:item/shared", "1": "test:item/dead"}})
        for name in ("shared", "inherited", "dead"):
            self.texture(f"assets/test/textures/item/{name}.png")
            self.write(f"assets/test/textures/item/{name}.png.mcmeta", {"animation": {}})
        self.texture("assets/test/textures/item/shared_e.png")
        result = {row["file"]: row["status"] for row in audit(self.root, [], textures=True)}
        for name in ("shared", "inherited"):
            for suffix in (".png", ".png.mcmeta"):
                self.assertEqual(result[f"assets/test/textures/item/{name}{suffix}"], "used")
        for suffix in (".png", ".png.mcmeta"):
            self.assertEqual(result[f"assets/test/textures/item/dead{suffix}"], "unused")
        self.assertEqual(result["assets/test/textures/item/shared_e.png"], "used")

    def test_fonts_atlases_equipment_and_unreferenced_gui(self):
        self.write("assets/test/font/default.json", {"providers": [{"type": "bitmap", "file": "test:font/icon.png"}]})
        self.write("assets/test/atlases/trims.json", {"sources": [
            {"type": "paletted_permutations", "textures": ["test:trims/pattern"], "palette_key": "test:trims/palette"}]})
        self.write("assets/test/equipment/suit.json", {"layers": {"humanoid": [{"texture": "test:suit"}]}})
        for name in ("font/icon", "trims/pattern", "trims/palette", "entity/equipment/humanoid/suit", "gui/dynamic"):
            self.texture(f"assets/test/textures/{name}.png")
        result = {row["file"]: row["status"] for row in audit(self.root, [], textures=True)}
        for name in ("font/icon", "trims/pattern", "trims/palette", "entity/equipment/humanoid/suit"):
            self.assertEqual(result[f"assets/test/textures/{name}.png"], "used")
        self.assertEqual(result["assets/test/textures/gui/dynamic.png"], "unused")

    def test_unused_custom_gui_font_and_entity_textures_have_no_folder_exemption(self):
        for name in ("gui/old_menu", "font/old_icons", "entity/old_mob"):
            self.texture(f"assets/test/textures/{name}.png")
            self.write(f"assets/test/textures/{name}.png.mcmeta", {"animation": {}})
        rows = audit(self.root, [], textures=True)
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(row["status"] == "unused" for row in rows))

    def test_vanilla_gui_requires_jar_and_old_path_is_unused_after_comparison(self):
        for name in ("gui/builtin", "trims/old_path", "trims/new_path"):
            self.texture(f"assets/minecraft/textures/{name}.png")
        self.assertTrue(all(row["status"] == "unverified" for row in audit(self.root, [], textures=True)))
        jar = self.root / "vanilla.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            archive.writestr("version.json", json.dumps({"pack_version": {"resource_major": 75}}))
            for name in ("gui/builtin", "trims/new_path"):
                archive.writestr(f"assets/minecraft/textures/{name}.png", b"PNG")
        result = {row["file"]: row["status"] for row in audit(self.root, [jar], textures=True)}
        self.assertEqual(result["assets/minecraft/textures/gui/builtin.png"], "used")
        self.assertEqual(result["assets/minecraft/textures/trims/new_path.png"], "used")
        self.assertEqual(result["assets/minecraft/textures/trims/old_path.png"], "unused")

    def test_unique_filename_in_local_tooling_retains_background_and_metadata(self):
        self.texture("assets/test/textures/gui/template_background.png")
        self.write("assets/test/textures/gui/template_background.png.mcmeta", {"animation": {}})
        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "generate.py").write_text('backgrounds = ("template_background.png",)', encoding="utf-8")
        rows = audit(self.root, [], textures=True)
        self.assertTrue(all(row["status"] == "used" for row in rows))
        self.assertTrue(all("local tooling reference" in row["reason"] for row in rows))

    def test_font_and_atlas_aliases_resolve_textures_outside_item_directory(self):
        self.write("assets/test/font/nested/menu.json", {"providers": [{"type": "bitmap", "file": "test:ui/menu.png"}]})
        self.write("assets/test/atlases/gui.json", {"sources": [
            {"type": "single", "resource": "test:ui/source", "sprite": "test:menu_alias"},
            {"type": "unstitch", "resource": "test:ui/sheet", "regions": [{"sprite": "test:sheet_alias"}]}]})
        self.write("assets/test/items/icon.json", {"model": {"model": "test:item/icon"}})
        self.write("assets/test/models/item/icon.json", {"textures": {"0": "test:menu_alias", "1": "test:sheet_alias"}})
        for name in ("menu", "source", "sheet", "unreferenced"):
            self.texture(f"assets/test/textures/ui/{name}.png")
        result = {row["file"]: row["status"] for row in audit(self.root, [], textures=True)}
        for name in ("menu", "source", "sheet"):
            self.assertEqual(result[f"assets/test/textures/ui/{name}.png"], "used")
        self.assertEqual(result["assets/test/textures/ui/unreferenced.png"], "unused")

    def test_atlas_directory_alias_does_not_make_every_texture_used(self):
        self.write("assets/test/atlases/blocks.json", {"sources": [{"type": "directory", "source": "item", "prefix": "alias/"}]})
        self.write("assets/test/items/live.json", {"model": {"model": "test:item/live"}})
        self.write("assets/test/models/item/live.json", {"textures": {"0": "test:alias/actual"}})
        for name in ("actual", "unused"):
            self.texture(f"assets/test/textures/item/{name}.png")
        result = {row["file"]: row["status"] for row in audit(self.root, [], textures=True)}
        self.assertEqual(result["assets/test/textures/item/actual.png"], "used")
        self.assertEqual(result["assets/test/textures/item/unused.png"], "unused")

    def test_vanilla_texture_replacement_and_overlay_textures(self):
        self.write("pack.mcmeta", {"pack": {"pack_format": 46, "supported_formats": [46, 75]},
                                  "overlays": {"entries": [{"directory": "new", "formats": 75}]}})
        self.write("assets/test/items/live.json", {"model": {"model": "test:item/live"}})
        self.write("assets/test/models/item/live.json", {"textures": {"0": "test:item/animated"}})
        for prefix in ("", "new/"):
            self.texture(f"{prefix}assets/test/textures/item/animated.png")
            self.write(f"{prefix}assets/test/textures/item/animated.png.mcmeta", {"animation": {}})
        self.texture("assets/minecraft/textures/gui/widgets.png")
        jar = self.root / "vanilla.jar"
        with zipfile.ZipFile(jar, "w") as archive:
            archive.writestr("version.json", json.dumps({"pack_version": {"resource_major": 75}}))
            archive.writestr("assets/minecraft/textures/gui/widgets.png", b"PNG")
        result = {row["file"]: row["status"] for row in audit(self.root, [jar], textures=True)}
        self.assertTrue(all(status == "used" for status in result.values()))


if __name__ == "__main__":
    unittest.main()
