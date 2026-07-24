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
