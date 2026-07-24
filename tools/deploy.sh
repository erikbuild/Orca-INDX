#!/bin/bash
# ABOUTME: Syncs the repo's Prusa vendor profiles into the installed OrcaSlicer.app
# ABOUTME: and the user-data system dir so a restart picks up the INDX presets.
set -euo pipefail
REPO="/Users/erik/Code/orca-indx/OrcaSlicer/resources/profiles"
APP="/Applications/OrcaSlicer.app/Contents/Resources/profiles"
DATA="$HOME/Library/Application Support/OrcaSlicer/system"

if pgrep -xq OrcaSlicer; then
    echo "OrcaSlicer is running — quit it first." >&2
    exit 1
fi

for DEST in "$APP" "$DATA"; do
    rsync -a --delete "$REPO/Prusa/" "$DEST/Prusa/"
    cp "$REPO/Prusa.json" "$DEST/Prusa.json"
    echo "synced -> $DEST"
done
echo "Restart OrcaSlicer to load the INDX presets."
