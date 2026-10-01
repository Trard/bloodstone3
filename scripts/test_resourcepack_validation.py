#!/usr/bin/env python3
"""Regression checks: inject broken resources into temporary fixtures, never into the real pack."""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from check_font_symbols import FontResolver, PackView, ValidationError, check_fonts, read_json
from check_bloodlevels import Assets, source_bytes_match, validate_assets, validate_contract

ROOT = Path(__file__).resolve().parents[1]


class FontChecks(unittest.TestCase):
    def test_source_comparison_accepts_git_json_line_endings(self):
        self.assertTrue(source_bytes_match("model.json", b'{\n"a": 1\n}', b'{\r\n"a": 1\r\n}'))
        self.assertFalse(source_bytes_match("model.json", b'{"a": 2}', b'{"a": 1}'))

    def test_source_comparison_keeps_png_bytes_exact(self):
        self.assertFalse(source_bytes_match("image.png", b"\r\n", b"\n"))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("pack.mcmeta", {"pack": {"pack_format": 75}})

    def write(self, relative, data):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
        return p

    def font(self, name, providers):
        return self.write(f"assets/test/font/{name}.json", {"providers": providers})

    @staticmethod
    def space(char="\ue060"):
        return {"type": "space", "advances": {char: -1}}

    def test_independent_fonts_can_reuse_codes(self):
        self.font("a", [self.space()]); self.font("b", [self.space()])
        self.assertEqual(check_fonts(PackView(self.root)), (2, []))

    def test_reference_collision_is_reported(self):
        self.font("a", [self.space()])
        self.font("b", [self.space(), {"type": "reference", "id": "test:a"}])
        _, errors = check_fonts(PackView(self.root), ["test:b"])
        self.assertTrue(any("U+E060" in e and "assigned 2 times" in e for e in errors))

    def test_reference_cycle_is_reported(self):
        self.font("a", [{"type": "reference", "id": "test:b"}])
        self.font("b", [{"type": "reference", "id": "test:a"}])
        _, errors = check_fonts(PackView(self.root))
        self.assertTrue(any("cycle" in e for e in errors))

    def test_missing_reference_is_reported(self):
        self.font("a", [{"type": "reference", "id": "test:missing"}])
        self.assertTrue(check_fonts(PackView(self.root))[1])

    def test_missing_and_bad_bitmap_grid(self):
        for chars in [[], ["a", "bc"], [""]]:
            with self.subTest(chars=chars):
                self.font("a", [{"type": "bitmap", "file": "test:a.png", "ascent": 8, "chars": chars}])
                self.assertTrue(check_fonts(PackView(self.root))[1])

    def test_null_cells_are_not_duplicates(self):
        self.font("a", [{"type": "bitmap", "file": "test:a.png", "ascent": 8, "chars": ["\0\0a"]}])
        self.assertEqual(check_fonts(PackView(self.root))[1], [])

    def test_overlay_is_used_only_for_matching_format(self):
        self.font("a", [self.space()])
        self.write("pack.mcmeta", {"pack": {"pack_format": 75}, "overlays": {"entries": [{"directory": "new", "formats": 75}]}})
        self.write("new/assets/test/font/a.json", {"providers": [self.space(), self.space()]})
        self.assertEqual(check_fonts(PackView(self.root, 74))[1], [])
        self.assertTrue(check_fonts(PackView(self.root, 75))[1])

    def test_duplicate_json_keys_are_rejected(self):
        p = self.root / "bad.json"
        p.write_text('{"providers": [], "providers": []}')
        with self.assertRaisesRegex(ValidationError, "duplicate JSON key"):
            read_json(p)


class BloodLevelsChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "assets/bloodlevels", self.root / "assets/bloodlevels")
        (self.root / "pack.mcmeta").write_text('{"pack":{"pack_format":75}}')
        self.default = self.root / "assets/minecraft/font/default.json"
        self.default.parent.mkdir(parents=True)
        self.default.write_text('{"providers":[{"type":"reference","id":"bloodlevels:icons_default"}]}')
        self.config = yaml.safe_load((ROOT / "integrations/bloodlevels/resource-pack.yml").read_text())
        self.pack = PackView(self.root)

    def test_valid_import(self):
        resolver = validate_contract(self.pack, self.config)
        self.assertEqual(validate_assets(self.pack, resolver, Assets(self.pack))["png"], 253)

    def test_new_default_collision_rejected(self):
        d = read_json(self.default)
        d["providers"].append({"type": "space", "advances": {"\ue060": 1}})
        self.default.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValidationError, "exactly once"):
            validate_contract(self.pack, self.config)

    def test_old_icon_font_cannot_leak_to_default(self):
        self.default.write_text('{"providers":[{"type":"reference","id":"bloodlevels:icons"}]}')
        with self.assertRaisesRegex(ValidationError, "Unexpected BloodLevels glyph"):
            validate_contract(self.pack, self.config)

    def test_stale_server_config_is_rejected(self):
        bad = copy.deepcopy(self.config)
        bad["badges"]["gray"] = bad["badges"]["gray"].replace("\ue060", "\ue520")
        with self.assertRaisesRegex(ValidationError, "badges.gray"):
            validate_contract(self.pack, bad)

    def test_changed_glyph_metrics_rejected(self):
        p = self.root / "assets/bloodlevels/font/icons_default.json"
        d = read_json(p); d["providers"][1]["ascent"] = 5; p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValidationError, "changed glyph/metrics"):
            validate_contract(self.pack, self.config)

    def test_missing_texture_rejected(self):
        (self.root / "assets/bloodlevels/textures/font/gray.png").unlink()
        resolver = validate_contract(self.pack, self.config)
        with self.assertRaisesRegex(ValidationError, "missing textures"):
            validate_assets(self.pack, resolver, Assets(self.pack))

    def test_model_texture_alias_cycle_rejected(self):
        assets = Assets(self.pack)
        with self.assertRaisesRegex(ValidationError, "alias cycle"):
            assets.texture("#a", {"a": "#b", "b": "#a"})

    def test_missing_model_rejected(self):
        (self.root / "assets/bloodlevels/models/item/claimed.json").unlink()
        resolver = validate_contract(self.pack, self.config)
        with self.assertRaisesRegex(ValidationError, "missing models"):
            validate_assets(self.pack, resolver, Assets(self.pack))

    def test_corrupt_png_rejected(self):
        from PIL import UnidentifiedImageError
        (self.root / "assets/bloodlevels/textures/font/gray.png").write_bytes(b"not a PNG")
        resolver = validate_contract(self.pack, self.config)
        with self.assertRaises(UnidentifiedImageError):
            validate_assets(self.pack, resolver, Assets(self.pack))

    def test_incorrect_page_mask_rejected(self):
        p = self.root / "assets/bloodlevels/items/menu-label-mask-2.json"
        d = read_json(p)
        d["model"]["model"] = "bloodlevels:item/levels_001_mask"
        p.write_text(json.dumps(d))
        resolver = validate_contract(self.pack, self.config)
        with self.assertRaisesRegex(ValidationError, "page 2: incorrect mask"):
            validate_assets(self.pack, resolver, Assets(self.pack))

    def test_model_parent_cycle_rejected(self):
        p = self.root / "assets/bloodlevels/models/item/claimed.json"
        p.write_text('{"parent":"bloodlevels:item/claimed"}')
        with self.assertRaisesRegex(ValidationError, "model parent cycle"):
            Assets(self.pack).model("bloodlevels:item/claimed")


if __name__ == "__main__":
    unittest.main()
