# ABOUTME: Copies the profile files our OrcaSlicer branch adds or modifies into
# ABOUTME: output/<source-bundle-label>/, mirroring the resources/profiles layout.
import shutil
import subprocess
import sys
from pathlib import Path

from tools.paths import SRC_INI, REPO, OUTPUT

PROFILES_PREFIX = "resources/profiles/"

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

def changed_profile_files():
    out = subprocess.run(
        ["git", "-C", str(REPO), "diff", "--name-only", "main", "--", PROFILES_PREFIX],
        check=True, capture_output=True, text=True).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--others", "--exclude-standard", PROFILES_PREFIX],
        check=True, capture_output=True, text=True).stdout.splitlines()
    return sorted(set(out) | set(untracked))

def export(output_root):
    dest_root = Path(output_root) / source_label(SRC_INI)
    if dest_root.exists():
        shutil.rmtree(dest_root)
    copied = []
    for repo_rel in changed_profile_files():
        rel = repo_rel[len(PROFILES_PREFIX):]
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / repo_rel, dest)
        copied.append(rel)
    return copied

def main():
    copied = export(OUTPUT)
    for rel in copied:
        print(rel)
    print(f"{len(copied)} files -> {OUTPUT / source_label(SRC_INI)}")
    return 0 if copied else 1

if __name__ == "__main__":
    sys.exit(main())
