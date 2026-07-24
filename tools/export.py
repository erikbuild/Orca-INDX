# ABOUTME: Builds the standalone Prusa-INDX vendor bundle in output/<source-bundle>/:
# ABOUTME: flattened self-contained presets (Orca loads data-dir vendors without cross-vendor inheritance).
import json
import shutil
import sys
from pathlib import Path

from tools.keymap import PAIRS
from tools.orca_json import resolve_orca
from tools.paths import SRC_INI, PROFILES, OUTPUT

VENDOR = "Prusa-INDX"
VENDOR_VERSION = "01.00.00.00"
MODEL_NAME = "Prusa CORE One INDX 8T"
ASSETS = ["coreone_indx.stl", "coreone_indx.svg", f"{MODEL_NAME}_cover.png"]

def source_label(ini_path):
    repo_id = version = None
    for line in Path(ini_path).read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "repo_id":
            repo_id = value.strip()
        elif key.strip() == "config_version":
            version = value.strip()
        if repo_id and version:
            break
    return f"{repo_id}-{version}"

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent="\t", ensure_ascii=False) + "\n", encoding="utf-8")

def flattened(type_dir, name):
    data = resolve_orca(PROFILES, type_dir, name)
    data.pop("inherits", None)
    return data

def export(output_root):
    dest_root = Path(output_root) / source_label(SRC_INI)
    bundle_dir = dest_root / VENDOR
    if dest_root.exists():
        shutil.rmtree(dest_root)
    written = []

    index = {
        "name": VENDOR,
        "version": VENDOR_VERSION,
        "force_update": "0",
        "description": "Prusa CORE One INDX 8T profiles, ported from the Prusa-FFF vendor bundle",
        "machine_model_list": [], "process_list": [], "filament_list": [], "machine_list": [],
    }

    model = json.loads(
        (PROFILES / "Prusa" / "machine" / f"{MODEL_NAME}.json").read_text(encoding="utf-8"))
    write_json(bundle_dir / "machine" / f"{MODEL_NAME}.json", model)
    index["machine_model_list"].append(
        {"name": MODEL_NAME, "sub_path": f"machine/{MODEL_NAME}.json"})
    written.append(f"machine/{MODEL_NAME}.json")

    sections = [("machine", "machine", "machine_list"),
                ("process", "process", "process_list"),
                ("filament", "filament", "filament_list")]
    for kind, type_dir, list_key in sections:
        for _, orca_name in PAIRS[kind]:
            write_json(bundle_dir / type_dir / f"{orca_name}.json", flattened(type_dir, orca_name))
            index[list_key].append(
                {"name": orca_name, "sub_path": f"{type_dir}/{orca_name}.json"})
            written.append(f"{type_dir}/{orca_name}.json")

    for asset in ASSETS:
        shutil.copy2(PROFILES / "Prusa" / asset, bundle_dir / asset)
        written.append(asset)

    write_json(dest_root / f"{VENDOR}.json", index)
    written.append(f"{VENDOR}.json")
    return written

def main():
    written = export(OUTPUT)
    for rel in written:
        print(rel)
    print(f"{len(written)} files -> {OUTPUT / source_label(SRC_INI)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
