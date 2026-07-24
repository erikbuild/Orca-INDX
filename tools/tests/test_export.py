# ABOUTME: Tests the standalone Prusa-INDX vendor bundle export: structure,
# ABOUTME: flattening (no inherits), index completeness, and asset presence.
import json
import tempfile
import unittest
from pathlib import Path
from tools.export import source_label, export
from tools.paths import SRC_INI

class TestExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.written = export(Path(cls.tmp.name))
        cls.root = Path(cls.tmp.name) / source_label(SRC_INI)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_source_label_from_vendor_section(self):
        self.assertEqual(source_label(SRC_INI), "prusa-fff-2.5.5")

    def test_bundle_layout(self):
        self.assertTrue((self.root / "Prusa-INDX.json").is_file())
        for sub in ("machine", "process", "filament"):
            self.assertTrue((self.root / "Prusa-INDX" / sub).is_dir())

    def test_index_lists_every_preset_and_paths_exist(self):
        idx = json.loads((self.root / "Prusa-INDX.json").read_text())
        self.assertEqual(idx["name"], "Prusa-INDX")
        self.assertEqual(len(idx["machine_model_list"]), 1)
        self.assertEqual(len(idx["machine_list"]), 1)
        self.assertEqual(len(idx["process_list"]), 4)
        self.assertEqual(len(idx["filament_list"]), 12)
        for section in ("machine_model_list", "machine_list", "process_list", "filament_list"):
            for entry in idx[section]:
                self.assertTrue((self.root / "Prusa-INDX" / entry["sub_path"]).is_file(),
                                entry["sub_path"])

    def test_presets_are_flattened(self):
        for path in (self.root / "Prusa-INDX").rglob("*.json"):
            data = json.loads(path.read_text())
            self.assertNotIn("inherits", data, path.name)

    def test_machine_is_self_contained(self):
        m = json.loads((self.root / "Prusa-INDX" / "machine" /
                        "Prusa CORE One INDX 8T 0.4 nozzle.json").read_text())
        self.assertEqual(m["nozzle_diameter"], ["0.4"] * 8)
        self.assertEqual(m["printable_height"], "270")          # from fdm_machine_common chain
        self.assertIn("machine_start_gcode", m)

    def test_assets_copied(self):
        for asset in ("coreone_indx.stl", "coreone_indx.svg",
                      "Prusa CORE One INDX 8T_cover.png"):
            self.assertTrue((self.root / "Prusa-INDX" / asset).is_file(), asset)

if __name__ == "__main__":
    unittest.main()
