# ABOUTME: Diffs resolved PrusaSlicer INDX presets against the ported Orca presets.
# ABOUTME: CLI: python3 -m tools.check_fidelity {machine|process|filament} [--expected]
import re
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
    # PS vector values use "," for most keys and ";" for a few (extruder_colour)
    return [v.strip() for v in re.split(r"[,;]", str(value))]

# PS wraps these values in quotes with literal \n escapes; compare raw, not split
GCODE_KEYS = {"start_filament_gcode", "end_filament_gcode"}

def unquote_gcode(value):
    value = str(value)
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value.replace("\\n", "\n").strip()

def compare(ps, orca, keymap):
    diffs = []
    for ps_key, orca_key in keymap.items():
        if orca_key is None or ps_key not in ps:
            continue
        ps_val = VALUE_TRANSFORMS.get((ps_key, ps[ps_key]), ps[ps_key])
        orca_val = orca.get(orca_key)
        if orca_val is None:
            diffs.append(f"{ps_key} -> {orca_key}: missing in Orca (PS={ps_val!r})")
        elif ps_key in GCODE_KEYS:
            orca_text = orca_val[0] if isinstance(orca_val, list) else orca_val
            if unquote_gcode(ps_val) != str(orca_text).strip():
                diffs.append(f"{ps_key} -> {orca_key}: gcode text differs")
        elif normalize(ps_val) != normalize(orca_val):
            diffs.append(f"{ps_key} -> {orca_key}: PS={ps_val!r} Orca={orca_val!r}")
    return diffs

def main():
    kind = sys.argv[1]
    bundle = load_bundle(SRC_INI)
    keymap = MAPS[kind]
    failed = False
    unmapped = set()
    for ps_name, orca_name in PAIRS[kind]:
        ps = resolve(bundle, PS_TYPE[kind], ps_name)
        unmapped.update(k for k in ps if k not in keymap)
        if "--expected" in sys.argv:
            print(f"=== {ps_name} ===")
            for k in sorted(ps):
                if keymap.get(k):
                    print(f"  {k} ({keymap[k]}) = {ps[k]}")
            continue
        try:
            orca = resolve_orca(PROFILES, ORCA_DIR[kind], orca_name)
        except FileNotFoundError as e:
            print(f"[FAIL] {ps_name} -> {orca_name}: missing Orca preset ({e.filename})")
            failed = True
            continue
        diffs = compare(ps, orca, keymap)
        status = "OK" if not diffs else "FAIL"
        print(f"[{status}] {ps_name} -> {orca_name}")
        for d in diffs:
            print(f"    {d}")
        failed = failed or bool(diffs)
    if unmapped and "--expected" not in sys.argv:
        print(f"note: {len(unmapped)} PS keys outside the {kind} map "
              f"(inherited baseline, not ported): {', '.join(sorted(unmapped)[:12])}"
              + (" ..." if len(unmapped) > 12 else ""))
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
