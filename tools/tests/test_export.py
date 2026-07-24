# ABOUTME: Tests the profile export: source-label derivation and copying the
# ABOUTME: branch's changed profile files into an output directory tree.
import tempfile
import unittest
from pathlib import Path
from tools.export import source_label, export
from tools.paths import SRC_INI

class TestExport(unittest.TestCase):
    def test_source_label_from_vendor_section(self):
        self.assertEqual(source_label(SRC_INI), "prusa-fff-2.5.5")

    def test_export_copies_changed_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = export(Path(tmp))
            dest = Path(tmp) / "prusa-fff-2.5.5"
            self.assertIn("Prusa.json", copied)
            self.assertTrue((dest / "Prusa.json").is_file())
            self.assertTrue(any("INDX" in c for c in copied))
            for rel in copied:
                self.assertTrue((dest / rel).is_file(), rel)

if __name__ == "__main__":
    unittest.main()
