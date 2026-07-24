# orca-indx

Tooling and docs for porting the Prusa CORE One INDX 8T presets (machine,
process, filament) into OrcaSlicer's Prusa vendor bundle.

The source of truth is `PrusaSlicer_2.5.5.ini` — the PrusaSlicer **Prusa-FFF
2.5.5** vendor configuration bundle, which contains the official
`COREONE_INDX8T` presets. The ported Orca profiles live in the `OrcaSlicer/`
clone (git-ignored here) on branch `prusa-coreone-indx-8t`, under
`resources/profiles/Prusa/`.

## Layout

- `PrusaSlicer_2.5.5.ini` — Prusa-FFF vendor bundle the port is derived from
- `tools/prusa_ini.py` — parses the bundle, resolves preset inheritance
- `tools/orca_json.py` — resolves OrcaSlicer profile inheritance chains
- `tools/keymap.py` — PrusaSlicer→Orca key maps, drop allowlist, value transforms
- `tools/check_fidelity.py` — diffs resolved PS presets against the ported Orca presets
- `tools/deploy.sh` — syncs the ported profiles into the installed OrcaSlicer.app
- `docs/superpowers/specs/` — design spec
- `plans/` — implementation plan

## Usage

```bash
# unit tests
python3 -m unittest discover -s tools/tests -t .

# fidelity gates (exit 0 = every mapped value matches PrusaSlicer)
python3 -m tools.check_fidelity machine
python3 -m tools.check_fidelity process
python3 -m tools.check_fidelity filament

# print the resolved PrusaSlicer values used for authoring
python3 -m tools.check_fidelity filament --expected

# deploy to /Applications/OrcaSlicer.app (quit Orca first)
tools/deploy.sh
```

Intentional deviations from the PrusaSlicer values (keys Orca lacks, renamed
semantics, g-code substitutions) are documented in `ALLOWLIST` and
`VALUE_TRANSFORMS` in `tools/keymap.py`.

## Updating from a newer Prusa bundle

Export the current bundle from PrusaSlicer (or fetch the Prusa-FFF vendor
ini), replace `PrusaSlicer_2.5.5.ini` (adjusting the filename in
`tools/check_fidelity.py` and `tools/tests/`), re-run the fidelity gates, and
update the Orca profiles until they pass again.
