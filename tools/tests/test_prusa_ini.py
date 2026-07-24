# ABOUTME: Tests for the PrusaSlicer INI bundle parser and inheritance resolver.
# ABOUTME: Uses the real PrusaSlicer_2.5.5.ini as fixture; asserts known INDX values.
import unittest
from tools.prusa_ini import load_bundle, resolve
from tools.paths import SRC_INI

class TestPrusaIni(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle(SRC_INI)

    def test_sections_loaded(self):
        self.assertIn("printer:*C1_INDX_8T_common*", self.bundle)
        self.assertIn("printer_model:COREONE_INDX8T", self.bundle)

    def test_comment_lines_skipped(self):
        # filament:*INDX_common* has "; filament_notes = INDX" commented out
        sec = self.bundle["filament:*INDX_common*"]
        self.assertNotIn("filament_notes", sec)

    def test_resolve_printer(self):
        p = resolve(self.bundle, "printer", "Prusa CORE One INDX 8T HF0.4 nozzle")
        self.assertEqual(p["printer_variant"], "HF0.4")           # own key wins
        self.assertEqual(p["bed_shape"], "0x0,248x0,248x205,0x205")
        self.assertEqual(p["retract_length"], "0.8,0.8,0.8,0.8,0.8,0.8,0.8,0.8")
        self.assertEqual(p["machine_max_feedrate_x"], "350,160")
        self.assertNotIn("inherits", p)

    def test_resolve_filament_diamond(self):
        f = resolve(self.bundle, "filament", "Prusament PLA @COREONEINDX HF0.4")
        self.assertEqual(f["temperature"], "225")                 # own key
        self.assertEqual(f["first_layer_temperature"], "230")     # from parents
        self.assertEqual(f["chamber_temperature"], "20")          # *C1INDX_CH_PLA*
        self.assertEqual(f["filament_minimal_purge_on_wipe_tower"], "12")  # *C1INDX_common*
        self.assertEqual(f["idle_temperature"], "nil")            # *C1INDX_common* overrides *C1_CH_PLA*

if __name__ == "__main__":
    unittest.main()
