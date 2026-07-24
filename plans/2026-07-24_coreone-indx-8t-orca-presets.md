# Prusa CORE One INDX 8T → OrcaSlicer Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add upstream-quality Prusa CORE One INDX 8T presets (machine + 4 process + 12 filament) to the OrcaSlicer Prusa vendor bundle, verified by a fidelity checker against PrusaSlicer's official INDX presets, and deployed to the installed OrcaSlicer 2.4.2.

**Architecture:** Hand-authored Orca JSON profiles in `OrcaSlicer/resources/profiles/Prusa/` on branch `prusa-coreone-indx-8t`, mirroring the XL 5T toolchanger pattern and CORE One HF conventions. A Python toolchain in the outer repo (`tools/`) resolves both preset formats' inheritance and diffs mapped values — built first, TDD-style, so profile authoring happens against a red/green gate.

**Tech Stack:** Python 3 stdlib only (unittest, json, re). No pip dependencies. Bash for deploy.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-24-coreone-indx-8t-orca-presets-design.md`.
- Source of truth for values: `/Users/erik/Code/orca-indx/PrusaSlicer_2.5.5.ini` (referred to as `SRC_INI`).
- Orca repo: `/Users/erik/Code/orca-indx/OrcaSlicer` (referred to as `REPO`), branch `prusa-coreone-indx-8t`. Only `resources/profiles/Prusa.json` and `resources/profiles/Prusa/**` may be modified inside REPO.
- Outer repo: `/Users/erik/Code/orca-indx` — tools, tests, docs live here. `OrcaSlicer/` is git-ignored here.
- **Erik commits, never the implementer.** Every "Commit" step below means: report the exact `git add`/`git commit -m` commands and files, then STOP and ask Erik to commit before continuing.
- 8T only. HF 0.4 nozzle only. All 12 filaments. `Prusa.json` version bumps `02.04.00.03` → `02.04.00.04` (Task 7, once, not per-task).
- New preset names (used consistently everywhere):
  - Machine model: `Prusa CORE One INDX 8T`
  - Machine: `Prusa CORE One INDX 8T 0.4 nozzle`
  - Machine common (abstract): `fdm_machine_common_coreone_indx`
  - Process common (abstract): `process_common_coreone_indx`
  - Processes: `0.10mm FINE @CORE One INDX 0.4`, `0.15mm DETAIL @CORE One INDX 0.4`, `0.20mm BALANCED @CORE One INDX 0.4`, `0.25mm DRAFT @CORE One INDX 0.4`
  - Filaments: `<PrusaSlicer base name> @CORE One INDX`, e.g. `Prusament PLA @CORE One INDX` (12 total; the `8T` is deliberately omitted so a future 4T can share them, mirroring Prusa's own naming)
- Orca casing conventions: CORE One process quality tokens are ALL-CAPS (`SPEED`, `STRUCTURAL`) → we use `FINE`/`DETAIL`/`BALANCED`/`DRAFT`. The `★` in Prusa's `0.20mm Balanced ★` is dropped (no `★` anywhere in the Orca tree).
- Linkage convention: XL 5T style — explicit `compatible_printers` arrays (`["Prusa CORE One INDX 8T 0.4 nozzle"]`), NOT `compatible_printers_condition` regexes.
- Known-good placeholder constructs (verified in `src/libslic3r/PlaceholderParser.cpp` / `GCode.cpp`): `global`/`local` variables persisting across blocks, vector globals + element writes, `interpolate_table()`, `is_nil()`, `=~`/`!~` regex, ternary, `min`/`max`, writable `e_retracted[]`/`position[]`, injected read-only `temperature[]`, `retract_length[]`, `is_extruder_used[]`, `initial_tool`, `num_extruders`, `layer_z`, `max_layer_z`, `layer_num`, `first_layer_print_min/max`, `print_bed_max`, `has_wipe_tower`; `next_extruder`/`previous_extruder`/`first_layer_temperature` **only inside `change_filament_gcode`**.

---

### Task 1: PrusaSlicer INI resolver (`tools/prusa_ini.py`)

**Files:**
- Create: `tools/prusa_ini.py`
- Test: `tools/tests/test_prusa_ini.py` (and empty `tools/tests/__init__.py`, `tools/__init__.py`)

**Interfaces:**
- Produces: `load_bundle(path) -> dict[str, dict[str, str]]` mapping `"TYPE:name"` → raw key/value dict (no inheritance applied), and `resolve(bundle, section_type, name) -> dict[str, str]` returning the fully inherited flat dict for a preset. Inheritance: `inherits = A; B; C` composes parents depth-first, left to right, section's own keys last; parent names resolve within the same `section_type` namespace; the `inherits` key itself is removed from the result. Lines starting with `;` or `#` are comments. A key's value runs to end-of-line (values contain literal `\n` two-char escapes — do NOT unescape them).

- [ ] **Step 1: Write the failing test**

```python
# ABOUTME: Tests for the PrusaSlicer INI bundle parser and inheritance resolver.
# ABOUTME: Uses the real PrusaSlicer_2.5.5.ini as fixture; asserts known INDX values.
import unittest
from pathlib import Path
from tools.prusa_ini import load_bundle, resolve

SRC_INI = Path(__file__).resolve().parents[2] / "PrusaSlicer_2.5.5.ini"

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/erik/Code/orca-indx && python3 -m unittest tools.tests.test_prusa_ini -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'tools.prusa_ini'`

- [ ] **Step 3: Write the implementation**

```python
# ABOUTME: Parses a PrusaSlicer vendor bundle INI and resolves preset inheritance.
# ABOUTME: Presets compose parents depth-first left-to-right, own keys applied last.
from pathlib import Path

def load_bundle(path):
    bundle = {}
    current = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = {}
            bundle[line[1:-1]] = current
            continue
        if current is None or "=" not in line:
            continue
        key, _, value = line.partition("=")
        current[key.strip()] = value.strip()
    return bundle

def resolve(bundle, section_type, name):
    section = bundle[f"{section_type}:{name}"]
    result = {}
    for parent in [p.strip() for p in section.get("inherits", "").split(";") if p.strip()]:
        result.update(resolve(bundle, section_type, parent))
    result.update(section)
    result.pop("inherits", None)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/erik/Code/orca-indx && python3 -m unittest tools.tests.test_prusa_ini -v`
Expected: `OK` (5 tests)

- [ ] **Step 5: Commit gate**

Report to Erik: `git add tools/ && git commit -m "Add PrusaSlicer INI bundle resolver with tests"` — STOP and ask Erik to commit.

---

### Task 2: Orca profile resolver (`tools/orca_json.py`)

**Files:**
- Create: `tools/orca_json.py`
- Test: `tools/tests/test_orca_json.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `resolve_orca(profiles_dir, type_dir, name) -> dict` — loads `<profiles_dir>/Prusa/<type_dir>/<name>.json`, recursively applies single-parent `inherits` (Orca profiles have at most one parent, also in `<type_dir>`), child keys win, and strips `inherits`. `profiles_dir` is `REPO/resources/profiles`. Values stay as loaded (strings, lists).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/erik/Code/orca-indx && python3 -m unittest tools.tests.test_orca_json -v`
Expected: FAIL/ERROR `ModuleNotFoundError: No module named 'tools.orca_json'`

- [ ] **Step 3: Write the implementation**

```python
# ABOUTME: Loads OrcaSlicer vendor profile JSON files and resolves their inherits chains.
# ABOUTME: Orca profiles have at most one parent per file; child keys override parent keys.
import json
from pathlib import Path

def resolve_orca(profiles_dir, type_dir, name):
    path = Path(profiles_dir) / "Prusa" / type_dir / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    parent_name = data.get("inherits")
    if not parent_name:
        data.pop("inherits", None)
        return data
    result = resolve_orca(profiles_dir, type_dir, parent_name)
    result.update(data)
    result.pop("inherits", None)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/erik/Code/orca-indx && python3 -m unittest tools.tests.test_orca_json -v`
Expected: `OK` (2 tests)

- [ ] **Step 5: Commit gate**

Report: `git add tools/orca_json.py tools/tests/test_orca_json.py && git commit -m "Add Orca profile inheritance resolver with tests"` — STOP and ask Erik to commit.

---

### Task 3: Key map + fidelity checker (`tools/keymap.py`, `tools/check_fidelity.py`)

**Files:**
- Create: `tools/keymap.py`, `tools/check_fidelity.py`
- Test: `tools/tests/test_check_fidelity.py`

**Interfaces:**
- Consumes: `load_bundle`/`resolve` (Task 1), `resolve_orca` (Task 2).
- Produces: CLI `python3 -m tools.check_fidelity {machine|process|filament} [--expected]`. For each ported preset pair it compares PS-resolved values against Orca-resolved values through the key map; exit 0 iff every mapped key matches or is allowlisted. `--expected` prints the PS-resolved value table (the authoring reference for Tasks 4–6). `tools/keymap.py` exports three dicts `MACHINE_MAP`, `PROCESS_MAP`, `FILAMENT_MAP` (`ps_key -> orca_key or None` where `None` = intentionally dropped, see `ALLOWLIST` with a reason string per dropped key) plus `PAIRS = {"machine": [...], "process": [...], "filament": [...]}` listing `(ps_name, orca_name)` preset pairs.

**The key maps are plan content — copy them exactly.** Verification greps for the ⚠ entries are in Step 3a; run them before writing the map and correct any entry the grep disproves (record corrections in the task report).

`MACHINE_MAP` (PS key → Orca key; `None` = dropped, must appear in `ALLOWLIST`):

```python
MACHINE_MAP = {
    "bed_shape": "printable_area",
    "max_print_height": "printable_height",
    "nozzle_diameter": "nozzle_diameter",
    "max_layer_height": "max_layer_height",
    "min_layer_height": "min_layer_height",
    "extruder_colour": "extruder_colour",
    "extruder_offset": "extruder_offset",
    "retract_length": "retraction_length",
    "retract_speed": "retraction_speed",
    "deretract_speed": "deretraction_speed",
    "retract_before_travel": "retraction_minimum_travel",
    "retract_before_wipe": "retract_before_wipe",
    "retract_layer_change": "retract_when_changing_layer",
    "retract_length_toolchange": "retract_length_toolchange",
    "retract_restart_extra": "retract_restart_extra",
    "retract_restart_extra_toolchange": "retract_restart_extra_toolchange",
    "retract_lift": "z_hop",
    "retract_lift_above": "retract_lift_above",
    "retract_lift_below": "retract_lift_below",
    "wipe": "wipe",
    "machine_max_acceleration_e": "machine_max_acceleration_e",
    "machine_max_acceleration_extruding": "machine_max_acceleration_extruding",
    "machine_max_acceleration_retracting": "machine_max_acceleration_retracting",
    "machine_max_acceleration_travel": "machine_max_acceleration_travel",
    "machine_max_acceleration_x": "machine_max_acceleration_x",
    "machine_max_acceleration_y": "machine_max_acceleration_y",
    "machine_max_acceleration_z": "machine_max_acceleration_z",
    "machine_max_feedrate_e": "machine_max_speed_e",
    "machine_max_feedrate_x": "machine_max_speed_x",
    "machine_max_feedrate_y": "machine_max_speed_y",
    "machine_max_feedrate_z": "machine_max_speed_z",
    "machine_max_jerk_e": "machine_max_jerk_e",
    "machine_max_jerk_x": "machine_max_jerk_x",
    "machine_max_jerk_y": "machine_max_jerk_y",
    "machine_max_jerk_z": "machine_max_jerk_z",
    "machine_max_junction_deviation": "machine_max_junction_deviation",
    "machine_min_extruding_rate": "machine_min_extruding_rate",
    "machine_min_travel_rate": "machine_min_travel_rate",
    "cooling_tube_length": "cooling_tube_length",
    "cooling_tube_retraction": "cooling_tube_retraction",
    "parking_pos_retraction": "parking_pos_retraction",
    "extra_loading_move": "extra_loading_move",
    "high_current_on_filament_swap": "high_current_on_filament_swap",
    "single_extruder_multi_material": "single_extruder_multi_material",
    "use_firmware_retraction": "use_firmware_retraction",
    "use_relative_e_distances": "use_relative_e_distances",
    "gcode_flavor": "gcode_flavor",
    "host_type": "host_type",
    "thumbnails": "thumbnails",
    "thumbnails_format": "thumbnails_format",
    "extruder_clearance_radius": "extruder_clearance_radius",
    "extruder_clearance_height": "extruder_clearance_height_to_rod",
    "machine_limits_usage": "emit_machine_limits_to_gcode",   # value transform: emit_to_gcode -> "1"
    "z_offset": "z_offset",
    "pause_print_gcode": "machine_pause_gcode",
    # Dropped (each needs an ALLOWLIST reason):
    "autoemit_temperature_commands": None,   # no Orca key; Orca always emits temps itself
    "binary_gcode": None,                    # Orca has no binary-gcode output
    "color_change_gcode": None,              # no Orca config key; M600 not used on toolchanger
    "machine_limits_usage_note": None,       # placeholder row, see machine_limits_usage above
    "multimaterial_purging": None,           # no Orca key; purge volumes come from filament settings
    "prefer_clockwise_movements": None,      # no Orca key
    "printer_technology": None,              # implicit FFF in Orca machine profiles
    "remaining_times": None,                 # no Orca key; firmware M73 always understood
    "silent_mode": None,                     # deprecated/ignored in Orca (PrintConfig ignore set)
    "travel_lift_before_obstacle": None,     # Orca lift model is z_hop + z_hop_types
    "travel_max_lift": None,                 # ported as literal in change_filament_gcode
    "travel_ramping_lift": None,             # expressed via z_hop_types "Slope Lift"
    "travel_slope": None,                    # ported as literal in change_filament_gcode
    "use_volumetric_e": None,                # no Orca key
    "variable_layer_height": None,           # no usable Orca key (adaptive_layer_height removed)
    "nozzle_high_flow": None,                # Orca convention: HF_NOZZLE keyword in printer_notes
    "default_filament_profile": None,        # names differ by design (checked by eye)
    "default_print_profile": None,           # names differ by design (checked by eye)
    "printer_model": None,                   # names differ by design
    "printer_variant": None,                 # PS "HF0.4" vs Orca "0.4" by design
    "printer_notes": None,                   # rewritten to Orca keyword conventions
    "start_gcode": None, "end_gcode": None, "toolchange_gcode": None,
    "layer_gcode": None, "before_layer_gcode": None,   # g-code compared by review, not value-diff
}
```

`PROCESS_MAP`:

```python
PROCESS_MAP = {
    "layer_height": "layer_height",
    "first_layer_height": "initial_layer_print_height",
    "perimeters": "wall_loops",
    "top_solid_layers": "top_shell_layers",
    "bottom_solid_layers": "bottom_shell_layers",
    "top_solid_min_thickness": "top_shell_thickness",
    "bottom_solid_min_thickness": "bottom_shell_thickness",
    "extrusion_width": "line_width",
    "perimeter_extrusion_width": "inner_wall_line_width",
    "external_perimeter_extrusion_width": "outer_wall_line_width",
    "infill_extrusion_width": "sparse_infill_line_width",
    "solid_infill_extrusion_width": "internal_solid_infill_line_width",
    "top_infill_extrusion_width": "top_surface_line_width",
    "first_layer_extrusion_width": "initial_layer_line_width",
    "support_material_extrusion_width": "support_line_width",
    "perimeter_speed": "inner_wall_speed",
    "external_perimeter_speed": "outer_wall_speed",
    "small_perimeter_speed": "small_perimeter_speed",
    "infill_speed": "sparse_infill_speed",
    "solid_infill_speed": "internal_solid_infill_speed",
    "top_solid_infill_speed": "top_surface_speed",
    "first_layer_speed": "initial_layer_speed",
    "first_layer_infill_speed": "initial_layer_infill_speed",
    "bridge_speed": "bridge_speed",
    "gap_fill_speed": "gap_infill_speed",
    "support_material_speed": "support_speed",
    "support_material_interface_speed": "support_interface_speed",
    "travel_speed": "travel_speed",
    "travel_speed_z": "travel_speed_z",
    "default_acceleration": "default_acceleration",
    "perimeter_acceleration": "inner_wall_acceleration",
    "external_perimeter_acceleration": "outer_wall_acceleration",
    "infill_acceleration": "sparse_infill_acceleration",
    "solid_infill_acceleration": "internal_solid_infill_acceleration",
    "top_solid_infill_acceleration": "top_surface_acceleration",
    "first_layer_acceleration": "initial_layer_acceleration",       # ⚠ verify
    "bridge_acceleration": "bridge_acceleration",
    "travel_acceleration": "travel_acceleration",
    "fill_density": "sparse_infill_density",
    "fill_pattern": "sparse_infill_pattern",                        # value "grid" valid in Orca
    "fill_angle": "infill_direction",
    "infill_overlap": "infill_wall_overlap",
    "infill_anchor": "infill_anchor",
    "infill_anchor_max": "infill_anchor_max",
    "top_fill_pattern": "top_surface_pattern",                      # monotoniclines -> monotonicline
    "bottom_fill_pattern": "bottom_surface_pattern",
    "enable_dynamic_overhang_speeds": "enable_overhang_speed",
    "overhang_speed_0": "overhang_1_4_speed",
    "overhang_speed_1": "overhang_2_4_speed",
    "overhang_speed_2": "overhang_3_4_speed",
    "overhang_speed_3": "overhang_4_4_speed",                       # ⚠ percent values: see Task 5 note
    "seam_position": "seam_position",
    "elefant_foot_compensation": "elefant_foot_compensation",
    "gcode_resolution": "resolution",
    "arc_fitting": "enable_arc_fitting",                            # value transform: emit_center -> "1"
    "perimeter_generator": "wall_generator",
    "thin_walls": "detect_thin_wall",
    "overhangs": "detect_overhang_wall",
    "bridge_flow_ratio": "bridge_flow",
    "thick_bridges": "thick_bridges",
    "min_bead_width": "min_bead_width",
    "min_feature_size": "min_feature_size",
    "wall_distribution_count": "wall_distribution_count",
    "wall_transition_angle": "wall_transition_angle",
    "wall_transition_filter_deviation": "wall_transition_filter_deviation",
    "wall_transition_length": "wall_transition_length",
    "brim_type": "brim_type",
    "brim_width": "brim_width",
    "brim_separation": "brim_object_gap",
    "skirts": "skirt_loops",
    "skirt_distance": "skirt_distance",
    "skirt_height": "skirt_height",
    "support_material": "enable_support",
    "support_material_auto": None,   # expressed via support_type "normal(manual)" (see Task 5)
    "support_material_threshold": "support_threshold_angle",
    "support_material_angle": "support_angle",
    "support_material_contact_distance": "support_top_z_distance",  # ⚠ verify
    "support_material_bottom_contact_distance": "support_bottom_z_distance",  # ⚠ verify
    "support_material_interface_layers": "support_interface_top_layers",
    "support_material_bottom_interface_layers": "support_interface_bottom_layers",
    "support_material_interface_spacing": "support_interface_spacing",
    "support_material_interface_pattern": "support_interface_pattern",
    "support_material_pattern": "support_base_pattern",
    "support_material_spacing": "support_base_pattern_spacing",
    "support_material_style": "support_style",
    "support_material_xy_spacing": "support_object_xy_distance",
    "support_material_buildplate_only": "support_on_build_plate_only",
    "support_tree_angle": "tree_support_branch_angle",
    "support_tree_angle_slow": "tree_support_angle_slow",
    "support_tree_branch_diameter": "tree_support_branch_diameter",
    "support_tree_branch_diameter_angle": "tree_support_branch_diameter_angle",
    "support_tree_branch_diameter_double_wall": "tree_support_branch_diameter_double_wall",
    "support_tree_branch_distance": "tree_support_branch_distance",  # ⚠ verify
    "support_tree_tip_diameter": "tree_support_tip_diameter",
    "support_tree_top_rate": "tree_support_top_rate",
    "raft_contact_distance": "raft_contact_distance",
    "raft_expansion": "raft_expansion",
    "raft_first_layer_density": "raft_first_layer_density",
    "raft_first_layer_expansion": "raft_first_layer_expansion",
    "wipe_tower": "enable_prime_tower",
    "wipe_tower_width": "prime_tower_width",
    "wipe_tower_cone_angle": "wipe_tower_cone_angle",
    "wipe_tower_extra_spacing": "wipe_tower_extra_spacing",
    "wipe_tower_extra_flow": "wipe_tower_extra_flow",               # ⚠ verify
    "wipe_tower_bridging": "wipe_tower_bridging",
    "wipe_tower_brim_width": "prime_tower_brim_width",              # ⚠ verify
    "wipe_tower_no_sparse_layers": "wipe_tower_no_sparse_layers",
    "single_extruder_multi_material_priming": "single_extruder_multi_material_priming",
    "mmu_segmented_region_max_width": "mmu_segmented_region_max_width",
    "output_filename_format": "filename_format",
    "xy_size_compensation": "xy_size_compensation",
    "ensure_vertical_shell_thickness": "ensure_vertical_shell_thickness",
    "gcode_label_objects": "gcode_label_objects",                   # value transform: firmware -> "1"
    "ooze_prevention": "ooze_prevention",
    "elefant_foot_compensation_dup": None,
    # Dropped:
    "automatic_infill_combination_max_layer_height": None,  # no Orca key
    "bridge_angle": None,                    # PS 0 = auto = Orca default when key absent
    "dont_support_bridges": None,            # no matching Orca key; Orca default behavior
    "extra_perimeters": None,                # PS 0 = off = Orca default
    "external_perimeters_first": None,       # PS 0 = Orca default wall_sequence
    "first_layer_acceleration_over_raft": None,  # PS 0 = disabled; no Orca key
    "first_layer_speed_over_raft": None,     # no Orca key
    "gap_fill_enabled": None,                # PS 1 = Orca default (gap fill on)
    "infill_every_layers": None,             # PS 1 = no combining = Orca default
    "infill_extruder": None, "perimeter_extruder": None, "solid_infill_extruder": None,
    "support_material_extruder": None, "support_material_interface_extruder": None,  # PS 1/0 = defaults
    "infill_first": None,                    # PS 0 = Orca default order
    "max_print_speed": None,                 # no Orca key (auto from feature speeds)
    "max_volumetric_speed": None,            # PS 0 = unlimited = Orca default (filament caps apply)
    "min_skirt_length": None,                # skirts=0 makes it moot
    "notes": None,
    "over_bridge_speed": None,               # no Orca key
    "overhangs_dup": None,
    "solid_infill_below_area": None,         # PS 0 = off = Orca default
    "solid_infill_every_layers": None,       # PS 0 = off = Orca default
    "support_material_closing_radius": None, # no Orca key
    "support_material_enforce_layers": None, # PS 0 = off
    "support_material_interface_contact_loops": None,  # PS 0 = off
    "support_material_synchronize_layers": None,       # PS 0 = off
    "support_material_with_sheath": None,    # PS 0 = off
    "toolchange_ordering": None,             # no Orca key (0.15mm DETAIL loses "cyclic")
    "top_one_perimeter_type": None,          # ⚠ check for Orca one-wall-top key; drop if absent
    "travel_short_distance_acceleration": None,  # no Orca key
    "wipe_tower_acceleration": None,         # PS 0 = use default accel; no Orca key
    "wipe_tower_extruder": None,             # PS 0 = auto = Orca default
    "compatible_printers_condition": None,   # replaced by compatible_printers array
}
```

`FILAMENT_MAP`:

```python
FILAMENT_MAP = {
    "temperature": "nozzle_temperature",
    "first_layer_temperature": "nozzle_temperature_initial_layer",
    "bed_temperature": "hot_plate_temp",
    "first_layer_bed_temperature": "hot_plate_temp_initial_layer",
    "chamber_temperature": "chamber_temperature",
    "chamber_minimal_temperature": "chamber_minimal_temperature",   # ⚠ verify filament-level key
    "filament_max_volumetric_speed": "filament_max_volumetric_speed",
    "filament_minimal_purge_on_wipe_tower": "filament_minimal_purge_on_wipe_tower",
    "min_fan_speed": "fan_min_speed",
    "max_fan_speed": "fan_max_speed",
    "bridge_fan_speed": "overhang_fan_speed",
    "disable_fan_first_layers": "close_fan_the_first_x_layers",
    "fan_below_layer_time": "fan_cooling_layer_time",
    "slowdown_below_layer_time": "slow_down_layer_time",
    "min_print_speed": "slow_down_min_speed",
    "filament_retract_length": "filament_retraction_length",        # ⚠ verify
    "filament_wipe": "filament_wipe",
    "filament_retract_before_wipe": "filament_retract_before_wipe",  # ⚠ verify
    "filament_density": "filament_density",
    "filament_cost": "filament_cost",
    "extrusion_multiplier": "filament_flow_ratio",
    "filament_type": "filament_type",
    "filament_soluble": "filament_soluble",
    "filament_diameter": "filament_diameter",
    "start_filament_gcode": "filament_start_gcode",
    "end_filament_gcode": "filament_end_gcode",
    "filament_multitool_ramming": "filament_multitool_ramming",
    "filament_multitool_ramming_volume": "filament_multitool_ramming_volume",
    "filament_multitool_ramming_flow": "filament_multitool_ramming_flow",
    "filament_loading_speed": "filament_loading_speed",
    "filament_loading_speed_start": "filament_loading_speed_start",
    "filament_unloading_speed": "filament_unloading_speed",
    "filament_unloading_speed_start": "filament_unloading_speed_start",
    "filament_load_time": "filament_load_time",
    "filament_unload_time": "filament_unload_time",
    "filament_cooling_moves": "filament_cooling_moves",
    "filament_cooling_initial_speed": "filament_cooling_initial_speed",
    "filament_cooling_final_speed": "filament_cooling_final_speed",
    "filament_stamping_distance": "filament_stamping_distance",
    "filament_stamping_loading_speed": "filament_stamping_loading_speed",
    "filament_shrinkage_compensation_xy": "filament_shrink",        # ⚠ verify name + semantics
    "filament_shrinkage_compensation_z": "filament_shrinkage_compensation_z",  # ⚠ verify
    # Dropped:
    "compatible_printers_condition": None,   # replaced by compatible_printers array
    "cooling_perimeter_transition_distance": None,   # no Orca key
    "cooling_slowdown_logic": None,          # no Orca key
    "enable_dynamic_fan_speeds": None,       # Orca overhang fan model differs; overhang_fan_speed used
    "overhang_fan_speed_0": None, "overhang_fan_speed_1": None,
    "overhang_fan_speed_2": None, "overhang_fan_speed_3": None,  # collapsed into overhang_fan_speed
    "filament_abrasive": None,               # expressed as ABRASIVE keyword in filament_notes
    "filament_infill_max_speed": None,       # no Orca key
    "filament_infill_max_crossing_speed": None,  # no Orca key
    "filament_purge_multiplier": None,       # ⚠ check; drop if absent
    "filament_ramming_parameters": None,     # SEMM ramming; INDX uses multitool ramming keys
    "filament_retract_length_toolchange": None,  # no Orca key; g-code uses retract_length[] instead
    "filament_travel_max_lift": None, "filament_travel_ramming_lift": None,
    "filament_travel_slope": None, "filament_travel_ramping_lift": None,  # Orca: filament_z_hop model
    "filament_toolchange_delay": None,       # ⚠ check; drop if absent
    "filament_spool_weight": None,           # ⚠ check; drop if absent
    "filament_vendor": "filament_vendor",
    "filament_colour": None,                 # Orca Prusa filaments do not carry colour; omit
    "idle_temperature": "idle_temperature",  # PS resolves to nil; see Task 6 idle-temp rule
    "renamed_from": None,
    "filament_notes": None,                  # rewritten (ABRASIVE keyword only where needed)
    "full_fan_speed_layer": "full_fan_speed_layer",
    "fan_always_on": "reduce_fan_stop_start_freq",   # ⚠ verify semantic equivalence; else drop
    "cooling": "slow_down_for_layer_cooling",        # ⚠ verify; else drop
}
```

- [ ] **Step 1: Write the failing test**

```python
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

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/erik/Code/orca-indx && python3 -m unittest tools.tests.test_check_fidelity -v`
Expected: ERROR `ModuleNotFoundError: No module named 'tools.keymap'`

- [ ] **Step 3a: Verify the ⚠ entries against Orca source before writing keymap.py**

Run each; a hit = keep the mapping, no hit = move the PS key to dropped (`None`) with an allowlist reason:

```bash
cd /Users/erik/Code/orca-indx/OrcaSlicer
grep -n '"initial_layer_acceleration"' src/libslic3r/PrintConfig.cpp
grep -n '"support_top_z_distance"\|"support_bottom_z_distance"' src/libslic3r/PrintConfig.cpp
grep -n '"tree_support_branch_distance"' src/libslic3r/PrintConfig.cpp
grep -n '"wipe_tower_extra_flow"\|"prime_tower_brim_width"' src/libslic3r/PrintConfig.cpp
grep -n '"chamber_minimal_temperature"' src/libslic3r/PrintConfig.cpp
grep -n '"filament_retraction_length"\|"filament_retract_before_wipe"' src/libslic3r/PrintConfig.cpp
grep -n '"filament_shrink"\|"filament_shrinkage_compensation_z"' src/libslic3r/PrintConfig.cpp
grep -n '"filament_purge_multiplier"\|"filament_toolchange_delay"\|"filament_spool_weight"' src/libslic3r/PrintConfig.cpp
grep -n '"top_one_wall_type"\|"only_one_wall_top"' src/libslic3r/PrintConfig.cpp
grep -n '"reduce_fan_stop_start_freq"\|"slow_down_for_layer_cooling"' src/libslic3r/PrintConfig.cpp
```

- [ ] **Step 3b: Write `tools/keymap.py`** — the three maps above (corrected per 3a), plus:

```python
ALLOWLIST = {
    # ps_key: reason string (one line each, copied from the map comments above)
}
PAIRS = {
    "machine": [("Prusa CORE One INDX 8T HF0.4 nozzle", "Prusa CORE One INDX 8T 0.4 nozzle")],
    "process": [
        ("0.10mm Fine @COREONEINDX HF0.4", "0.10mm FINE @CORE One INDX 0.4"),
        ("0.15mm Detail @COREONEINDX HF0.4", "0.15mm DETAIL @CORE One INDX 0.4"),
        ("0.20mm Balanced ★ @COREONEINDX HF0.4", "0.20mm BALANCED @CORE One INDX 0.4"),
        ("0.25mm Draft @COREONEINDX HF0.4", "0.25mm DRAFT @CORE One INDX 0.4"),
    ],
    "filament": [
        ("Prusament PLA @COREONEINDX HF0.4", "Prusament PLA @CORE One INDX"),
        ("Prusament PLA Blend @COREONEINDX HF0.4", "Prusament PLA Blend @CORE One INDX"),
        ("Prusament rPLA @COREONEINDX HF0.4", "Prusament rPLA @CORE One INDX"),
        ("Prusament Woodfill @COREONEINDX HF0.4", "Prusament Woodfill @CORE One INDX"),
        ("Prusament PETG @COREONEINDX HF0.4", "Prusament PETG @CORE One INDX"),
        ("Prusament ASA @COREONEINDX HF0.4", "Prusament ASA @CORE One INDX"),
        ("Prusament PC Blend @COREONEINDX HF0.4", "Prusament PC Blend @CORE One INDX"),
        ("Prusament PC Blend Carbon Fiber @COREONEINDX HF0.4", "Prusament PC Blend Carbon Fiber @CORE One INDX"),
        ("Generic PLA @COREONEINDX HF0.4", "Generic PLA @CORE One INDX"),
        ("Generic PLA Silk @COREONEINDX HF0.4", "Generic PLA Silk @CORE One INDX"),
        ("Generic PETG @COREONEINDX HF0.4", "Generic PETG @CORE One INDX"),
        ("Generic ABS @COREONEINDX HF0.4", "Generic ABS @CORE One INDX"),
    ],
}
VALUE_TRANSFORMS = {
    ("machine_limits_usage", "emit_to_gcode"): "1",
    ("arc_fitting", "emit_center"): "1",
    ("gcode_label_objects", "firmware"): "1",
    ("top_fill_pattern", "monotoniclines"): "monotonicline",
    ("wipe_tower", "0"): "0",
    ("support_material", "1"): "1",
}
```

- [ ] **Step 3c: Write `tools/check_fidelity.py`**

```python
# ABOUTME: Diffs resolved PrusaSlicer INDX presets against the ported Orca presets.
# ABOUTME: CLI: python3 -m tools.check_fidelity {machine|process|filament} [--expected]
import sys
from pathlib import Path
from tools.prusa_ini import load_bundle, resolve
from tools.orca_json import resolve_orca
from tools.keymap import (MACHINE_MAP, PROCESS_MAP, FILAMENT_MAP,
                          PAIRS, VALUE_TRANSFORMS)

ROOT = Path(__file__).resolve().parents[1]
SRC_INI = ROOT / "PrusaSlicer_2.5.5.ini"
PROFILES = ROOT / "OrcaSlicer" / "resources" / "profiles"
MAPS = {"machine": MACHINE_MAP, "process": PROCESS_MAP, "filament": FILAMENT_MAP}
PS_TYPE = {"machine": "printer", "process": "print", "filament": "filament"}
ORCA_DIR = {"machine": "machine", "process": "process", "filament": "filament"}

def normalize(value):
    if isinstance(value, list):
        return [str(v).strip() for v in value]
    return [v.strip() for v in str(value).split(",")]

def compare(ps, orca, keymap):
    diffs = []
    for ps_key, orca_key in keymap.items():
        if orca_key is None or ps_key not in ps:
            continue
        ps_val = VALUE_TRANSFORMS.get((ps_key, ps[ps_key]), ps[ps_key])
        orca_val = orca.get(orca_key)
        if orca_val is None:
            diffs.append(f"{ps_key} -> {orca_key}: missing in Orca (PS={ps_val!r})")
        elif normalize(ps_val) != normalize(orca_val):
            diffs.append(f"{ps_key} -> {orca_key}: PS={ps_val!r} Orca={orca_val!r}")
    return diffs

def main():
    kind = sys.argv[1]
    bundle = load_bundle(SRC_INI)
    failed = False
    for ps_name, orca_name in PAIRS[kind]:
        ps = resolve(bundle, PS_TYPE[kind], ps_name)
        if "--expected" in sys.argv:
            print(f"=== {ps_name} ===")
            for k in sorted(ps):
                if MAPS[kind].get(k):
                    print(f"  {k} ({MAPS[kind][k]}) = {ps[k]}")
            continue
        orca = resolve_orca(PROFILES, ORCA_DIR[kind], orca_name)
        diffs = compare(ps, orca, MAPS[kind])
        status = "OK" if not diffs else "FAIL"
        print(f"[{status}] {ps_name} -> {orca_name}")
        for d in diffs:
            print(f"    {d}")
        failed = failed or bool(diffs)
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run unit tests, then the red integration run**

Run: `python3 -m unittest tools.tests.test_check_fidelity -v` → Expected: `OK`
Run: `python3 -m tools.check_fidelity machine` → Expected: exit 1 with `FileNotFoundError`-style failure or `[FAIL]` (the Orca INDX machine doesn't exist yet — this is the red state for Tasks 4–6). Wrap the resolve in try/except reporting `missing Orca preset` instead of crashing.

- [ ] **Step 5: Commit gate**

Report: `git add tools/ && git commit -m "Add PS->Orca key maps and fidelity checker"` — STOP and ask Erik to commit.

---

### Task 4: Machine port

**Files:**
- Create: `REPO/resources/profiles/Prusa/machine/Prusa CORE One INDX 8T.json`
- Create: `REPO/resources/profiles/Prusa/machine/fdm_machine_common_coreone_indx.json`
- Create: `REPO/resources/profiles/Prusa/machine/Prusa CORE One INDX 8T 0.4 nozzle.json`
- Create: `REPO/resources/profiles/Prusa/Prusa CORE One INDX 8T_cover.png` (copy of `Prusa CORE One_cover.png`)
- Modify: `REPO/resources/profiles/Prusa.json` (machine_model_list + machine_list entries)

**Interfaces:**
- Consumes: `python3 -m tools.check_fidelity machine --expected` (value reference); Task 3 checker as gate.
- Produces: machine preset name `Prusa CORE One INDX 8T 0.4 nozzle` (referenced by Tasks 5–6 `compatible_printers`), model name `Prusa CORE One INDX 8T`.

- [ ] **Step 1: Red check** — `python3 -m tools.check_fidelity machine` → Expected: FAIL (missing preset).

- [ ] **Step 2: Machine model file** — `Prusa CORE One INDX 8T.json`:

```json
{
	"type": "machine_model",
	"name": "Prusa CORE One INDX 8T",
	"model_id": "Prusa_CORE_One_INDX_8T",
	"nozzle_diameter": "0.4",
	"machine_tech": "FFF",
	"family": "Prusa",
	"bed_model": "coreone_bed.stl",
	"bed_texture": "coreone.svg",
	"hotend_model": "",
	"default_materials": "Prusament PLA @CORE One INDX;Prusament PLA Blend @CORE One INDX;Prusament PETG @CORE One INDX;Generic PLA @CORE One INDX;Generic PLA Silk @CORE One INDX;Generic PETG @CORE One INDX;Prusament rPLA @CORE One INDX;Prusament Woodfill @CORE One INDX;Prusament PC Blend Carbon Fiber @CORE One INDX;Prusament ASA @CORE One INDX;Prusament PC Blend @CORE One INDX;Generic ABS @CORE One INDX"
}
```

Copy the cover: `cp "REPO/resources/profiles/Prusa/Prusa CORE One_cover.png" "REPO/resources/profiles/Prusa/Prusa CORE One INDX 8T_cover.png"` (placeholder; upstream will want a real render — note this in the eventual PR description).

- [ ] **Step 3: Machine common** — `fdm_machine_common_coreone_indx.json`. Non-gcode keys are the PS `*C1_INDX_8T_common*` values run through `MACHINE_MAP` (source values: `python3 -m tools.check_fidelity machine --expected`). Exact file (g-code fields filled in Step 4):

```json
{
	"type": "machine",
	"name": "fdm_machine_common_coreone_indx",
	"inherits": "fdm_machine_common",
	"from": "system",
	"instantiation": "false",
	"gcode_flavor": "marlin2",
	"host_type": "prusalink",
	"printer_structure": "corexy",
	"printable_area": ["0x0", "248x0", "248x205", "0x205"],
	"printable_height": "270",
	"nozzle_diameter": ["0.4", "0.4", "0.4", "0.4", "0.4", "0.4", "0.4", "0.4"],
	"extruder_colour": ["#F58231", "#1F77B4", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#17BECF", "#BCBD22"],
	"extruder_offset": ["0x0", "0x0", "0x0", "0x0", "0x0", "0x0", "0x0", "0x0"],
	"max_layer_height": ["0.3", "0.3", "0.3", "0.3", "0.3", "0.3", "0.3", "0.3"],
	"min_layer_height": ["0.07", "0.07", "0.07", "0.07", "0.07", "0.07", "0.07", "0.07"],
	"retraction_length": ["0.8", "0.8", "0.8", "0.8", "0.8", "0.8", "0.8", "0.8"],
	"retraction_speed": ["40", "40", "40", "40", "40", "40", "40", "40"],
	"deretraction_speed": ["30", "30", "30", "30", "30", "30", "30", "30"],
	"retraction_minimum_travel": ["1.5", "1.5", "1.5", "1.5", "1.5", "1.5", "1.5", "1.5"],
	"retract_before_wipe": ["80%", "80%", "80%", "80%", "80%", "80%", "80%", "80%"],
	"retract_when_changing_layer": ["1", "1", "1", "1", "1", "1", "1", "1"],
	"retract_length_toolchange": ["0", "0", "0", "0", "0", "0", "0", "0"],
	"retract_restart_extra": ["0", "0", "0", "0", "0", "0", "0", "0"],
	"retract_restart_extra_toolchange": ["0", "0", "0", "0", "0", "0", "0", "0"],
	"z_hop": ["0.2", "0.2", "0.2", "0.2", "0.2", "0.2", "0.2", "0.2"],
	"z_hop_types": ["Slope Lift", "Slope Lift", "Slope Lift", "Slope Lift", "Slope Lift", "Slope Lift", "Slope Lift", "Slope Lift"],
	"retract_lift_above": ["0", "0", "0", "0", "0", "0", "0", "0"],
	"retract_lift_below": ["269", "269", "269", "269", "269", "269", "269", "269"],
	"wipe": ["0", "0", "0", "0", "0", "0", "0", "0"],
	"machine_max_acceleration_e": ["5000", "2500"],
	"machine_max_acceleration_extruding": ["7000", "2500"],
	"machine_max_acceleration_retracting": ["2500", "2500"],
	"machine_max_acceleration_travel": ["7000", "2500"],
	"machine_max_acceleration_x": ["10000", "2500"],
	"machine_max_acceleration_y": ["10000", "2500"],
	"machine_max_acceleration_z": ["400", "200"],
	"machine_max_speed_e": ["100", "100"],
	"machine_max_speed_x": ["350", "160"],
	"machine_max_speed_y": ["350", "160"],
	"machine_max_speed_z": ["12", "12"],
	"machine_max_jerk_e": ["10", "10"],
	"machine_max_jerk_x": ["10", "8"],
	"machine_max_jerk_y": ["10", "8"],
	"machine_max_jerk_z": ["2", "2"],
	"machine_max_junction_deviation": ["0.01", "0.01"],
	"machine_min_extruding_rate": ["0", "0"],
	"machine_min_travel_rate": ["0", "0"],
	"emit_machine_limits_to_gcode": "1",
	"cooling_tube_length": "20",
	"cooling_tube_retraction": "45",
	"parking_pos_retraction": "84",
	"extra_loading_move": "-52",
	"high_current_on_filament_swap": "0",
	"single_extruder_multi_material": "0",
	"purge_in_prime_tower": "0",
	"use_firmware_retraction": "0",
	"use_relative_e_distances": "1",
	"extruder_clearance_radius": "75",
	"extruder_clearance_height_to_rod": "33",
	"extruder_clearance_height_to_lid": "50",
	"thumbnails": ["16x16/QOI", "313x173/QOI", "480x240/QOI", "380x285/PNG"],
	"thumbnails_format": "QOI",
	"z_offset": "0",
	"machine_pause_gcode": "M601",
	"printer_notes": "Don't remove the following keywords! These keywords are used in the \"compatible printer\" condition of the print and filament profiles to link the particular print and filament profiles to this printer profile.\nPRINTER_MODEL_COREONE_INDX\nHF_NOZZLE\nPG\nNO_TEMPLATES",
	"machine_start_gcode": "<Step 4>",
	"machine_end_gcode": "<Step 4>",
	"change_filament_gcode": "<Step 4>",
	"layer_change_gcode": "<Step 4>",
	"before_layer_change_gcode": "<Step 4>"
}
```

- [ ] **Step 4: G-code translation.** Extract the five PS blocks, apply the rename table, then the semantic edits. Extraction (prints each block with `\n` escapes intact — keep them; Orca JSON strings use the same literal `\n`):

```bash
cd /Users/erik/Code/orca-indx && python3 - <<'EOF'
from tools.prusa_ini import load_bundle, resolve
b = load_bundle("PrusaSlicer_2.5.5.ini")
p = resolve(b, "printer", "Prusa CORE One INDX 8T HF0.4 nozzle")
for k in ("start_gcode", "end_gcode", "toolchange_gcode", "layer_gcode", "before_layer_gcode"):
    open(f"/tmp/indx_{k}.txt", "w").write(p[k])
    print(k, len(p[k]))
EOF
```

Mechanical renames — apply to ALL five blocks (word-boundary replace, e.g. in an editor or `python3 -c "import re,sys; ..."`):

| PS identifier | Orca identifier |
|---|---|
| `first_layer_bed_temperature` | `hot_plate_temp_initial_layer` |
| `first_layer_temperature` | `nozzle_temperature_initial_layer` — **EXCEPT inside toolchange_gcode, keep as-is** (injected there) |
| `max_print_height` | `printable_height` |
| `deretract_speed` | `deretraction_speed` |
| `retract_speed` | `retraction_speed` (careful: run AFTER `deretract_speed`; do not touch `retract_length`, which stays — it is injected) |
| `max_fan_speed` | `fan_max_speed` |
| `external_perimeter_speed` | `outer_wall_speed` |
| `external_perimeter_extrusion_width` | `outer_wall_line_width` |
| `extrusion_width` (bare, after the previous rename) | `line_width` |
| `first_layer_height` | `initial_layer_print_height` |
| `wipe_tower` | `has_wipe_tower` |

Semantic edits (exact before → after; apply each once unless noted):

1. start_gcode, 8× (`N` = 0–7): `A{(filament_abrasive[N] ? 1 : 0)}` → `A{(filament_notes[N]=~/.*ABRASIVE.*/ ? 1 : 0)}` and `F{(nozzle_high_flow[N] ? 1 : 0)}` → `F1`
2. toolchange_gcode, the deretract branch:
   Before: `{if is_nil(filament_retract_length_toolchange[next_extruder])}\n    {deretract_length = retract_toolchange + retract_length[next_extruder]}\n  {else}\n    {deretract_length = retract_toolchange + filament_retract_length_toolchange[next_extruder]}\n  {endif}`
   After: `{deretract_length = retract_toolchange + retract_length[next_extruder]}`
   (Orca lacks a per-filament toolchange retract override; `retract_length[]` reflects the filament-level retraction override, and the 12 ported filaments set identical values for both PS keys, so behavior is preserved.)
3. toolchange_gcode, the same removal for the current-extruder retract guard:
   Before: `{if is_nil(filament_retract_length_toolchange[current_extruder])}\n  G1 E-[retract_length[current_extruder]] F{retraction_speed[current_extruder] * 60}\n{endif}`
   After: `G1 E-[retract_length[current_extruder]] F{retraction_speed[current_extruder] * 60}`
4. toolchange_gcode: `G27 W3 Z{travel_max_lift[current_extruder]} P2 R{retract_toolchange} V{retraction_speed[current_extruder]} A{travel_slope[current_extruder]}` → `G27 W3 Z1.5 P2 R{retract_toolchange} V{retraction_speed[current_extruder]} A1`
5. end_gcode + start_gcode: any `[first_layer_bed_temperature]`/`[hot_plate_temp_initial_layer]` bracket forms already handled by rename table; verify none remain by grepping `/tmp/indx_*.txt` for `first_layer_bed` after renames → zero hits.
6. start_gcode `M104 S{if is_nil(idle_temperature[initial_tool])}100{else}{idle_temperature[initial_tool]}{endif}` — keep verbatim (`is_nil` works; filament files set `idle_temperature` to `"nil"` per Task 6; if the profile validator rejects `"nil"` there, change this line to `M104 S100` and drop the key — record in allowlist).
7. Escape check: the JSON value must contain literal two-char `\n` sequences and escaped quotes (`M862.3 P \"COREONEINDX\"`). Paste each block as a single JSON string. `python3 -m json.tool <file>` on each machine JSON must pass.

- [ ] **Step 5: Variant machine** — `Prusa CORE One INDX 8T 0.4 nozzle.json`:

```json
{
	"type": "machine",
	"name": "Prusa CORE One INDX 8T 0.4 nozzle",
	"inherits": "fdm_machine_common_coreone_indx",
	"from": "system",
	"instantiation": "true",
	"printer_model": "Prusa CORE One INDX 8T",
	"printer_variant": "0.4",
	"nozzle_diameter": ["0.4", "0.4", "0.4", "0.4", "0.4", "0.4", "0.4", "0.4"],
	"default_filament_profile": "Prusament PLA @CORE One INDX",
	"default_print_profile": "0.20mm BALANCED @CORE One INDX 0.4"
}
```

- [ ] **Step 6: Index entries in `Prusa.json`.** Add to `machine_model_list` after the `Prusa CORE One L HF` entry:
`{ "name": "Prusa CORE One INDX 8T", "sub_path": "machine/Prusa CORE One INDX 8T.json" }`
Add to the END of `machine_list` (convention: new machines append):
`{ "name": "Prusa CORE One INDX 8T 0.4 nozzle", "sub_path": "machine/Prusa CORE One INDX 8T 0.4 nozzle.json" }`
(The abstract common must ALSO be listed in `machine_list` before the variant — verify by checking that `fdm_machine_common_xl_5t` appears there; mirror whatever the tree does.)

- [ ] **Step 7: Green gate**

Run: `python3 -m tools.check_fidelity machine` → Expected: `[OK]`, exit 0.
Run: `python3 -m json.tool` over each new/modified JSON → all parse.

- [ ] **Step 8: Commit gate** — report `git add` of the four REPO files + `git commit -m "Add Prusa CORE One INDX 8T machine profiles"` (in REPO on branch `prusa-coreone-indx-8t`) — STOP and ask Erik to commit.

---

### Task 5: Process port

**Files:**
- Create: `REPO/resources/profiles/Prusa/process/process_common_coreone_indx.json` + the four leaf files named in Global Constraints
- Modify: `REPO/resources/profiles/Prusa.json` (process_list)

**Interfaces:**
- Consumes: machine name from Task 4; `python3 -m tools.check_fidelity process --expected` for values.
- Produces: process names referenced by Task 4's `default_print_profile`.

- [ ] **Step 1: Red check** — `python3 -m tools.check_fidelity process` → FAIL (missing presets).

- [ ] **Step 2: `process_common_coreone_indx.json`** — `inherits: "fdm_process_common"`, `instantiation: "false"`, `from: "system"`, `type: "process"`. Body = PS `*INDX_common*` + `*INDX_04hf_common*` values through `PROCESS_MAP` (authoritative values from `--expected`; the map in Task 3 is the complete key list — every mapped key gets its PS value, every dropped key is skipped). Include: `"compatible_printers": ["Prusa CORE One INDX 8T 0.4 nozzle"]`, `"enable_prime_tower": "0"` (PS `wipe_tower = 0` — the INDX purges at the dock by default), `"support_type": "normal(manual)"` with `"enable_support": "1"` (PS `support_material=1, support_material_auto=0`), `"filename_format"` = PS `output_filename_format` with `COREONEINDX` kept (cosmetic string). Overhang speed note: PS `overhang_speed_3 = 70%` is a percent-of-normal value; Orca `overhang_4_4_speed` in shipped Prusa profiles is absolute mm/s. Port percent values as-is ONLY if `overhang_4_4_speed` is coFloatOrPercent (`grep -n '"overhang_4_4_speed"' src/libslic3r/PrintConfig.cpp` and check the option type); otherwise use the Orca CORE One HF leaf's absolute values and allowlist the delta.

- [ ] **Step 3: Four leaves.** Each: `inherits: "process_common_coreone_indx"`, `instantiation: "true"`, `from: "system"`, own deltas = the PS leaf sections (already extracted, small) through `PROCESS_MAP`. Example, `0.20mm BALANCED @CORE One INDX 0.4.json` (the 0.20 leaf sets no layer_height — 0.2 comes from common):

```json
{
	"type": "process",
	"name": "0.20mm BALANCED @CORE One INDX 0.4",
	"inherits": "process_common_coreone_indx",
	"from": "system",
	"instantiation": "true",
	"inner_wall_speed": "250",
	"internal_solid_infill_speed": "250",
	"sparse_infill_acceleration": "7000",
	"internal_solid_infill_acceleration": "7000",
	"inner_wall_acceleration": "6000",
	"outer_wall_acceleration": "5000",
	"support_speed": "120",
	"support_interface_speed": "60",
	"top_surface_speed": "150",
	"overhang_4_4_speed": "75%"
}
```

Build 0.10 FINE / 0.15 DETAIL / 0.25 DRAFT the same way from their extracted PS sections (`--expected` prints every mapped key+value per leaf; `toolchange_ordering` in 0.15 is dropped/allowlisted).

- [ ] **Step 4: Index entries** — append the four leaves (and the abstract common iff the tree lists `process_common_xl_5t` in `process_list` — mirror it) after the last `@Prusa XL 5T` process entry.

- [ ] **Step 5: Green gate** — `python3 -m tools.check_fidelity process` → all `[OK]`, exit 0; `json.tool` passes on all five files.

- [ ] **Step 6: Commit gate** — report REPO commit `"Add CORE One INDX process profiles"` — STOP for Erik.

---

### Task 6: Filament port

**Files:**
- Create: 12 files `REPO/resources/profiles/Prusa/filament/<name>.json` (names in Task 3 `PAIRS`)
- Modify: `REPO/resources/profiles/Prusa.json` (filament_list)

**Interfaces:**
- Consumes: machine name; `python3 -m tools.check_fidelity filament --expected` (authoritative per-filament values, resolved from the INI).
- Produces: filament names referenced by the machine model's `default_materials`.

Rules:
- Each file inherits the Prusa-local material base: PLA-family → `fdm_filament_pla`, PETG → `fdm_filament_pet`, ABS/ASA → `fdm_filament_abs`, PC → `fdm_filament_pc` (verify each base exists: `ls REPO/resources/profiles/Prusa/filament/fdm_filament_*.json`; if a base is missing, fall back to `fdm_filament_common`). All tracked values are set explicitly, so the parent only supplies cosmetics (vitrification, plate-type defaults).
- Every file sets `"compatible_printers": ["Prusa CORE One INDX 8T 0.4 nozzle"]`, `"filament_id"` = its own name, and the shared multi-tool block (from PS `*C1INDX_common*`): `filament_multitool_ramming ["1"]`, `filament_multitool_ramming_volume ["18"]`, `filament_multitool_ramming_flow ["50"]`, `filament_loading_speed ["0"]`, `filament_loading_speed_start ["0"]`, `filament_unloading_speed ["0"]`, `filament_unloading_speed_start ["0"]`, `filament_load_time ["8"]`, `filament_unload_time ["3.5"]`, `filament_cooling_moves ["0"]`, `filament_cooling_initial_speed ["0"]`, `filament_cooling_final_speed ["0"]`, `filament_stamping_distance ["0"]`, `filament_stamping_loading_speed ["0"]`, `filament_minimal_purge_on_wipe_tower ["12"]`.
- `idle_temperature`: set `["nil"]` if the profile validator accepts it (Orca nullable ints); else omit the key and apply the Task 4 Step 4 note 6 fallback. Decide once, apply to all 12.
- Pressure advance: `filament_start_gcode` = the PS section's own `start_filament_gcode` value verbatim (e.g. `["M572 S0.038 ; Pressure advance\nM573 R"]` for Prusament PLA). Every filament's S-value is in `--expected`.
- `Prusament PC Blend Carbon Fiber @CORE One INDX` additionally sets `"filament_notes": ["ABRASIVE"]` (drives the `M862.1 A` flag in start g-code).
- Shrinkage (ABS/ASA 0.22%, PC 0.18%, PC-CF 0%/0.18% Z): apply through the verified `filament_shrink` mapping from Task 3 Step 3a. PS `0.22%` compensation = Orca `filament_shrink` `"99.78%"` **only if** Orca semantics are "material shrinks to X%" — read the `filament_shrink` tooltip in PrintConfig.cpp and convert accordingly; record the conversion rule in a comment in `keymap.py`.

- [ ] **Step 1: Red check** — `python3 -m tools.check_fidelity filament` → 12× FAIL.

- [ ] **Step 2: Author the two template shapes**, then the remaining 10 from `--expected` values. Complete example 1 (Prusament, PLA family) — `Prusament PLA @CORE One INDX.json`:

```json
{
	"type": "filament",
	"name": "Prusament PLA @CORE One INDX",
	"inherits": "fdm_filament_pla",
	"from": "system",
	"filament_id": "Prusament PLA @CORE One INDX",
	"instantiation": "true",
	"compatible_printers": ["Prusa CORE One INDX 8T 0.4 nozzle"],
	"filament_vendor": ["Prusa Polymers"],
	"filament_type": ["PLA"],
	"nozzle_temperature": ["225"],
	"nozzle_temperature_initial_layer": ["230"],
	"hot_plate_temp": ["60"],
	"hot_plate_temp_initial_layer": ["60"],
	"chamber_temperature": ["20"],
	"filament_max_volumetric_speed": ["28"],
	"filament_minimal_purge_on_wipe_tower": ["12"],
	"fan_min_speed": ["100"],
	"fan_max_speed": ["100"],
	"overhang_fan_speed": ["100"],
	"close_fan_the_first_x_layers": ["1"],
	"fan_cooling_layer_time": ["40"],
	"slow_down_layer_time": ["9"],
	"slow_down_min_speed": ["20"],
	"filament_retraction_length": ["0.8"],
	"filament_wipe": ["1"],
	"filament_retract_before_wipe": ["70%"],
	"filament_density": ["1.24"],
	"filament_cost": ["27.99"],
	"filament_flow_ratio": ["1"],
	"filament_multitool_ramming": ["1"],
	"filament_multitool_ramming_volume": ["18"],
	"filament_multitool_ramming_flow": ["50"],
	"filament_loading_speed": ["0"],
	"filament_loading_speed_start": ["0"],
	"filament_unloading_speed": ["0"],
	"filament_unloading_speed_start": ["0"],
	"filament_load_time": ["8"],
	"filament_unload_time": ["3.5"],
	"filament_cooling_moves": ["0"],
	"filament_cooling_initial_speed": ["0"],
	"filament_cooling_final_speed": ["0"],
	"filament_stamping_distance": ["0"],
	"filament_stamping_loading_speed": ["0"],
	"filament_start_gcode": ["M572 S0.038 ; Pressure advance\nM573 R"]
}
```

(Add `chamber_minimal_temperature`/`idle_temperature` per the Task 3 verification and idle rule. `chamber_minimal_temperature` values per family: PLA/PETG 0, ABS/ASA/PC 40.)

Complete example 2 (Generic, PETG family, hotter chamber) — `Generic PETG @CORE One INDX.json`: same skeleton with `inherits: "fdm_filament_pet"`, `filament_vendor ["Generic"]`, `filament_type ["PETG"]`, temps 240/245, hot_plate 85/85, chamber 35, volumetric 17, fan 30/65, overhang_fan_speed 60, close_fan 3, cooling_layer_time 25, slow_down 9/20, retraction 1.6, density 1.27, cost 27.82, start_gcode `M572 S0.052`.

The remaining 10: every tracked value is printed by `--expected`; the resolved reference table also lives in the Task-3 research (ASA 265/265 bed 110/110 chamber 55/40 vol 30 fans 20/25; PC Blend 285/285 bed 115/110 chamber 55/40 vol 22 fans 15/25; PC-CF 290/290 vol 13 flow_ratio 1.03 + ABRASIVE note; rPLA 205/205 vol 10; Woodfill 195/195 vol 10 density 1.2; PLA Blend 225/230 vol 12.5; PLA Silk 215/220 vol 12.5; Generic PLA 215/220 vol 17; Generic ABS 260/260 bed 110/110 vol 25 fans 15/20 cost 34.65).

- [ ] **Step 3: Index entries** — append all 12 to `filament_list` after the last `@XL 5T` filament entry.

- [ ] **Step 4: Green gate** — `python3 -m tools.check_fidelity filament` → 12× `[OK]`, exit 0; `json.tool` passes ×12.

- [ ] **Step 5: Commit gate** — report REPO commit `"Add CORE One INDX filament profiles"` — STOP for Erik.

---

### Task 7: Repo validation + version bump

**Files:**
- Modify: `REPO/resources/profiles/Prusa.json` (`"version": "02.04.00.04"`)

- [ ] **Step 1:** Bump the version. Run `python3 REPO/scripts/orca_extra_profile_check.py --help` to learn invocation, then run it over `REPO/resources/profiles` (the CI workflow `.github/workflows/check_profiles.yml` shows the exact arguments — mirror them). Expected: zero errors for Prusa.
- [ ] **Step 2:** Check whether `REPO/scripts/assign_vendor_setting_ids.py` is required for new presets (read its header + check whether shipped new-preset PRs include `setting_id`). If required, run it as the script documents and verify it only adds `setting_id`/`filament_id` fields to our new files (`git -C REPO diff --stat`).
- [ ] **Step 3:** Profile validator binary: download the current `OrcaSlicer_profile_validator` from the OrcaSlicer nightly release assets (`gh release list -R OrcaSlicer/OrcaSlicer`, then `gh release download` the macOS validator asset). Run: `OrcaSlicer_profile_validator -p REPO/resources/profiles -s -l 2` (CI parity). Expected: exit 0. If no macOS asset exists, note it and rely on Step 1 + Task 8's live smoke test.
- [ ] **Step 4:** Re-run the full checker: `python3 -m tools.check_fidelity machine && python3 -m tools.check_fidelity process && python3 -m tools.check_fidelity filament` → all green.
- [ ] **Step 5: Commit gate** — REPO commit `"Bump Prusa bundle version for INDX 8T"` — STOP for Erik.

---

### Task 8: Deploy + live smoke test

**Files:**
- Create: `tools/deploy.sh`

- [ ] **Step 1: Write `tools/deploy.sh`:**

```bash
#!/bin/bash
# ABOUTME: Syncs the repo's Prusa vendor profiles into the installed OrcaSlicer.app
# ABOUTME: and the user-data system dir so a restart picks up the INDX presets.
set -euo pipefail
REPO="/Users/erik/Code/orca-indx/OrcaSlicer/resources/profiles"
APP="/Applications/OrcaSlicer.app/Contents/Resources/profiles"
DATA="$HOME/Library/Application Support/OrcaSlicer/system"
for DEST in "$APP" "$DATA"; do
    rsync -a --delete "$REPO/Prusa/" "$DEST/Prusa/"
    cp "$REPO/Prusa.json" "$DEST/Prusa.json"
    echo "synced -> $DEST"
done
echo "Restart OrcaSlicer to load the INDX presets."
```

`chmod +x tools/deploy.sh`. NOTE: quit OrcaSlicer before running. If macOS refuses to launch the modified app (signature), run `sudo xattr -dr com.apple.quarantine /Applications/OrcaSlicer.app` and relaunch; if it still refuses, `codesign --force --deep --sign - /Applications/OrcaSlicer.app` (ad-hoc re-sign) — document which was needed.

- [ ] **Step 2:** Run it; launch OrcaSlicer 2.4.2. Manual checklist (Erik at the keyboard, or implementer via `run` skill screenshots if feasible):
  1. Printer dropdown shows `Prusa CORE One INDX 8T 0.4 nozzle` (add via printer settings if the wizard must "install" the model first).
  2. Selecting it shows 8 filament slots; the 12 INDX filaments appear in the filament dropdown; the 4 INDX processes appear.
  3. Slice the built-in cube with 2 filaments assigned → slices without placeholder errors (Orca surfaces parser errors in the slicing dialog — a failed placeholder aborts the export; that is the acceptance signal).
  4. Export g-code; verify: `M862.3 P "COREONEINDX"` present, `T<n> S1 L0 D0` toolchange lines present, `G12 S90`/`G12 S30` purge-station sequence present, `M104 T<n>` per-tool shutdowns in the end block.
- [ ] **Step 3: G-code equivalence spot-check.** Slice the same 2-color model with the same filaments in PrusaSlicer (INDX 8T profile) and diff the start and one toolchange sequence side by side (order of operations, temps, tool-pick lines — not byte equality; Orca and PS emit different motion planning). Record deviations; anything semantic (missing temp wait, missing tool lock) is a bug to fix before Task 9.
- [ ] **Step 4:** Run one Orca calibration flow (Calibration → Flow rate or Temp tower) with `Prusament PLA @CORE One INDX` → slices clean.
- [ ] **Step 5: Commit gate** — outer-repo commit `"Add deploy script"` — STOP for Erik.

---

### Task 9: Hardware validation + wrap-up (Erik-driven)

- [ ] **Step 1:** Erik prints: (a) a small 2-tool print, (b) one filament calibration from Orca. Acceptance: successful tool changes, purge at dock, first layer OK.
- [ ] **Step 2:** Fix anything the print surfaces (loop back to the relevant task; checker + validators re-run after every profile edit).
- [ ] **Step 3:** Write memory notes (`~/.claude/.../memory/`): project state, deploy quirks discovered (signature handling), allowlist location.
- [ ] **Step 4:** Offer PR prep: rebase branch on upstream `main`, re-run validators, draft PR description (mentions: placeholder cover image needs a real render, 4T is a trivial follow-up, purge-station default with prime-tower opt-in).

---

## Self-review notes

- Spec coverage: machine (T4), process (T5), filament (T6), checker (T1–3), validators (T7), deploy+smoke (T8), hardware e2e (T9), version bump (T7), branch/commit discipline (global constraints). No gaps found.
- The ⚠ entries are deliberate verify-first steps with exact grep commands, not placeholders — each has a defined resolution path (keep, rename, or drop+allowlist).
- Type consistency: preset names in Task 3 `PAIRS` match Task 4–6 file names and the model's `default_materials` byte-for-byte (checked).
