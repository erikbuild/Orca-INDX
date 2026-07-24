#!/bin/bash
# ABOUTME: Syncs the repo's Prusa vendor profiles into OrcaSlicer's app-data system
# ABOUTME: dir (the copy Orca loads) and best-effort into the app bundle resources.
set -euo pipefail
REPO="/Users/erik/Code/orca-indx/OrcaSlicer/resources/profiles"
APP="/Applications/OrcaSlicer.app/Contents/Resources/profiles"
DATA="$HOME/Library/Application Support/OrcaSlicer/system"

if pgrep -xq OrcaSlicer; then
    echo "OrcaSlicer is running — quit it first." >&2
    exit 1
fi

rsync -a --delete "$REPO/Prusa/" "$DATA/Prusa/"
cp "$REPO/Prusa.json" "$DATA/Prusa.json"
echo "synced -> $DATA"

# The app bundle copy is only the install source; syncing it needs macOS App
# Management permission for this terminal. Best-effort: warn instead of fail.
if rsync -a --delete "$REPO/Prusa/" "$APP/Prusa/" 2>/dev/null && cp "$REPO/Prusa.json" "$APP/Prusa.json" 2>/dev/null; then
    echo "synced -> $APP"
else
    echo "warning: could not update $APP (App Management permission); app-data copy is newer and should win" >&2
fi

echo "Restart OrcaSlicer to load the INDX presets."
