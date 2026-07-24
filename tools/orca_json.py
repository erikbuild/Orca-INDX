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
