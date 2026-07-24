# ABOUTME: Tests the fidelity checker's mapping and comparison logic.
# ABOUTME: Uses synthetic preset dicts; the real INDX comparison is exercised via CLI in Tasks 4-6.
import unittest
from tools.keymap import MACHINE_MAP, PROCESS_MAP, FILAMENT_MAP, ALLOWLIST
from tools.check_fidelity import compare, normalize

class TestCheckFidelity(unittest.TestCase):
    def test_every_dropped_key_has_allowlist_reason(self):
        for m in (MACHINE_MAP, PROCESS_MAP, FILAMENT_MAP):
            for ps_key, orca_key in m.items():
                if orca_key is None:
                    self.assertIn(ps_key, ALLOWLIST, f"{ps_key} dropped without reason")

    def test_normalize_scalar_vs_list(self):
        self.assertEqual(normalize(["0.4", "0.4"]), ["0.4", "0.4"])
        self.assertEqual(normalize("0.4,0.4"), ["0.4", "0.4"])
        self.assertEqual(normalize("80%"), ["80%"])
        self.assertEqual(normalize(["1"]), ["1"])
        self.assertEqual(normalize("#F58231;#1F77B4"), ["#F58231", "#1F77B4"])

    def test_compare_reports_mismatch(self):
        ps = {"retract_length": "0.8,0.8"}
        orca = {"retraction_length": ["0.8", "0.9"]}
        diffs = compare(ps, orca, {"retract_length": "retraction_length"})
        self.assertEqual(len(diffs), 1)
        self.assertIn("retract_length", diffs[0])

    def test_compare_passes_on_match(self):
        ps = {"retract_length": "0.8,0.8", "silent_mode": "1"}
        orca = {"retraction_length": ["0.8", "0.8"]}
        diffs = compare(ps, orca, {"retract_length": "retraction_length", "silent_mode": None})
        self.assertEqual(diffs, [])

    def test_compare_applies_value_transforms(self):
        ps = {"filament_shrinkage_compensation_xy": "0.22%"}
        orca = {"filament_shrink": ["99.78%"]}
        diffs = compare(ps, orca, {"filament_shrinkage_compensation_xy": "filament_shrink"})
        self.assertEqual(diffs, [])

if __name__ == "__main__":
    unittest.main()
