# ABOUTME: Shared filesystem locations for the INDX port toolchain.
# ABOUTME: Single place to update when the source bundle or clone moves.
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_INI = ROOT / "PrusaSlicer-Source-Configs" / "PrusaSlicer_2.5.5.ini"
REPO = ROOT / "OrcaSlicer"
PROFILES = REPO / "resources" / "profiles"
OUTPUT = ROOT / "output"
