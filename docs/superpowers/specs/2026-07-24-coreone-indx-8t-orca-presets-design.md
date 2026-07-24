# Prusa CORE One INDX 8T presets for OrcaSlicer — Design

Date: 2026-07-24
Status: Approved pending Erik's review of this document

## Context

Erik has a Prusa CORE One with the 8-tool INDX toolchanger and wants to run
OrcaSlicer's built-in filament calibrations on it. OrcaSlicer has no INDX
profiles (verified: zero INDX references in `OrcaSlicer/resources/profiles/`).
PrusaSlicer ships official INDX presets; a full vendor bundle export lives at
`PrusaSlicer_2.5.5.ini` in this repo and contains everything needed:

- Printer model `COREONE_INDX8T` and printer preset
  `Prusa CORE One INDX 8T HF0.4 nozzle` (chain: `*C1_INDX_8T_common*`).
  INDX currently ships only a high-flow 0.4 nozzle variant.
- Print presets: `0.10mm Fine`, `0.15mm Detail`, `0.20mm Balanced ★`,
  `0.25mm Draft` `@COREONEINDX HF0.4`, built on `*INDX_common*` +
  `*INDX_04hf_common*`.
- 12 filament presets `@COREONEINDX HF0.4`: Prusament PLA, PLA Blend, rPLA,
  Woodfill, PETG, ASA, PC Blend, PC Blend Carbon Fiber; Generic PLA, PLA Silk,
  PETG, ABS. Built on `*C1INDX_common*` plus per-material chamber-temp helpers
  (`*C1INDX_CH_PLA*` etc.).

Environment facts (verified):

- OrcaSlicer clone at `OrcaSlicer/`, clean, branch `main`, 2.5.0-dev.
- Installed OrcaSlicer 2.4.2 at `/Applications/OrcaSlicer.app`.
- Prusa vendor bundle version `02.04.00.03` is identical in the repo, the
  installed app, and `~/Library/Application Support/OrcaSlicer/system/` — the
  repo's Prusa tree matches what the installed app runs, so deploying repo
  profiles into 2.4.2 is low-risk.
- Orca installs vendor bundles from app resources into `<data_dir>/system/`
  and loads from there (`src/libslic3r/PresetBundle.cpp`).
- Orca's XL 5T port (`machine/fdm_machine_common_xl_5t.json`) proves Orca's
  placeholder engine handles the advanced PrusaSlicer g-code constructs the
  INDX presets use: `local`/script blocks with `if/then/endif` and string
  emission, `is_extruder_used[]`, `filament_notes[]` regex (`=~`),
  PrusaSlicer-style names (`first_layer_temperature`, `temperature`,
  `first_layer_bed_temperature`) in g-code context.
- Repo has profile validation tooling: `scripts/orca_extra_profile_check.py`
  and the CI-built `OrcaSlicer_profile_validator` binary
  (`.github/workflows/build_all.yml` runs it with `-p resources/profiles -s -l 2`).

## Goals

- Upstream-quality additions to the Prusa vendor bundle in the OrcaSlicer
  repo tree: INDX 8T machine, 4 process profiles, all 12 filament profiles.
- Working end-to-end on Erik's installed OrcaSlicer 2.4.2 via a deploy
  script, so filament calibration runs on the real machine.

## Non-goals

- INDX 4T (trivial follow-up once 8T is proven; excluded to keep everything
  shippable testable on real hardware).
- Non-HF or other nozzle sizes (Prusa doesn't ship them for INDX yet).
- Building OrcaSlicer from source.

## Design

### 1. Profile files (in `OrcaSlicer/resources/profiles/Prusa/`, upstream-shaped)

Modeled on the XL 5T (Orca's only other Prusa toolchanger) and CORE One HF:

- `machine/Prusa CORE One INDX 8T.json` — `machine_model`. Reuses
  `coreone_bed.stl` / `coreone.svg`, `nozzle_diameter` "0.4",
  `default_materials` = the 12 filaments. Cover image
  `Prusa CORE One INDX 8T_cover.png` copied from the CORE One cover as a
  placeholder (upstream will want a real render before merge).
- `machine/fdm_machine_common_coreone_indx.json` — non-instantiated common:
  8-element arrays (nozzle diameters, retraction set, extruder colours,
  offsets, min/max layer heights), bed shape `248x205`, `max_print_height`
  270, machine limits from `*C1_INDX_8T_common*`, `single_extruder_multi_material`
  0, and the four translated g-code blocks (start / end / toolchange /
  layer-change, incl. the dock-fan logic and `before_layer_change` Z-based
  acceleration table). Inherits the closest existing common the CORE One
  machines use; exact parent chosen during implementation by mirroring the tree.
- `machine/Prusa CORE One INDX 8T 0.4 nozzle.json` — instantiated machine,
  `printer_variant` per Orca HF convention (CORE One HF uses variant "0.4"
  with HF expressed by the model), `nozzle_diameter` = 8 × 0.4.
- `process/` — 4 files inheriting Orca's existing CORE One process bases,
  overriding only what `*INDX_common*` / `*INDX_04hf_common*` change
  (seam/travel/accel specifics, compatible-printers condition). The `★` in
  Prusa's "0.20mm Balanced ★" is dropped if the existing Orca tree doesn't
  use it; final names mirror tree conventions.
- `filament/` — 12 files inheriting Orca's existing Prusament/Generic bases
  where present, overriding INDX-specific values: temps, chamber temperature
  and minimal chamber temperature, purge/"minimal purge on wipe tower"
  volumes, max volumetric speed, filament notes keywords the g-code keys on
  (e.g. `MBL160`, `HT_MBL10`).
- `Prusa.json` — index entries (`machine_model_list`, `machine_list`,
  `process_list`, `filament_list`) and version bump `02.04.00.03` →
  `02.04.00.04` (upstream convention for profile changes).

### 2. G-code translation

Port Prusa's INDX g-code with minimal semantic change. The XL 5T and CORE
One Orca ports are the compatibility dictionary: any construct they use is
proven; anything else gets checked against Orca's placeholder parser and, if
rejected, rewritten using only proven constructs. Known specifics:

- Start g-code: tool-pick loop, per-tool `M862.1` checks, `M574` filament
  runout config, chamber temp logic (`M141`/`M191`), `G427` tool calibration,
  purge-station prime sequence (`G12`).
- Toolchange g-code: keep Prusa's purge-station branch (firmware `G12` eject)
  as the default path; keep the prime-tower branch guarded the way XL 5T
  uses `purge_in_prime_tower`. The PrusaSlicer `wipe_tower` placeholder is
  mapped to Orca's equivalent during implementation (verified against parser,
  not assumed).
- `machine_max_junction_deviation` and any other keys Orca lacks are dropped
  with a note in the fidelity checker's allowlist.

### 3. Fidelity checker (`tools/check_fidelity.py`, outer repo — not in the Orca diff)

Resolves the INI inheritance chains for the INDX presets, resolves our Orca
JSON inheritance chains, maps PrusaSlicer→Orca key names, and diffs values.
Intentional deviations live in a documented allowlist in the script. Run
after authoring and after any profile edit; a clean report (only allowlisted
diffs) is the transcription-error gate.

### 4. Deploy script (`tools/deploy.sh`, outer repo)

Syncs `OrcaSlicer/resources/profiles/Prusa.json` + `Prusa/` into:

1. `/Applications/OrcaSlicer.app/Contents/Resources/profiles/`
2. `~/Library/Application Support/OrcaSlicer/system/` (the copy Orca loads)

Restart Orca to pick up changes. Re-run after any profile edit or app
update. Known small risks, accepted: macOS code-signature complaints
(mitigation: re-run script / `xattr` clear if Gatekeeper objects) and app
updates overwriting the patch (mitigation: re-run script).

### 5. Validation

| Tier | What | Gate |
|------|------|------|
| Unit | Fidelity checker vs resolved PrusaSlicer INI | Only allowlisted diffs |
| Integration | `scripts/orca_extra_profile_check.py`; `OrcaSlicer_profile_validator` binary (prebuilt from Orca CI/releases) against `resources/profiles` | Zero errors, CI parity |
| E2E | In patched Orca 2.4.2: select INDX 8T, slice a 2+ tool model and an Orca calibration print; diff emitted start/toolchange g-code against PrusaSlicer's output for the same setup; then a real 2-tool print + one filament calibration on the machine | G-code sequence-equivalent; print succeeds |

Erik runs the physical prints; everything before that is scriptable/local.

## Workflow

- Outer repo `orca-indx` (this repo): tooling (`tools/`), docs, the source
  INI. `OrcaSlicer/` is git-ignored.
- OrcaSlicer clone: work happens on branch `prusa-coreone-indx-8t` off
  `main`; only profile files + `Prusa.json` touched, keeping a clean
  upstreamable diff.
- Erik commits; Claude prompts for commits at each milestone.

## Risks

- **Placeholder incompatibility** (main risk): mitigated by the proven-construct
  dictionary, parser checks during implementation, and the g-code diff in E2E.
- **2.4.2 vs main drift**: bundle versions match today, so repo `main`
  profiles are what 2.4.2 ships; if upstream moves Prusa profiles before we
  PR, rebase and re-run validation.
- **Firmware expectations**: INDX g-code targets a specific firmware level
  (`M115 U6.6.3+15625`); kept verbatim so behavior matches PrusaSlicer.
