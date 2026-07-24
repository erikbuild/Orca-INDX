# ABOUTME: Tests the Orca vendor profile loader and single-parent inheritance resolver.
# ABOUTME: Uses real shipped Prusa profiles (XL 5T, Prusament PLA) as fixtures.
import unittest
from pathlib import Path
from tools.orca_json import resolve_orca

PROFILES = Path("/Users/erik/Code/orca-indx/OrcaSlicer/resources/profiles")

class TestOrcaJson(unittest.TestCase):
    def test_machine_chain(self):
        m = resolve_orca(PROFILES, "machine", "Prusa XL 5T 0.4 nozzle")
        self.assertEqual(m["nozzle_diameter"], ["0.4", "0.4", "0.4", "0.4", "0.4"])
        self.assertEqual(m["single_extruder_multi_material"], "0")   # from fdm_machine_common_xl_5t
        self.assertEqual(m["printable_height"], "360")               # from fdm_machine_common_xl
        self.assertNotIn("inherits", m)

    def test_filament_chain(self):
        f = resolve_orca(PROFILES, "filament", "Prusament PLA @CORE One")
        self.assertEqual(f["nozzle_temperature"], ["225"])
        self.assertEqual(f["filament_type"], ["PLA"])
        self.assertEqual(f["temperature_vitrification"], ["60"])     # from fdm_filament_pla

if __name__ == "__main__":
    unittest.main()
