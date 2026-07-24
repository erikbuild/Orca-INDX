# INDX 8T Hardware Test Punch List

Slice everything from the deployed `Prusa CORE One INDX 8T 0.4 nozzle` machine
with the `@CORE One INDX` filaments (they carry Prusa's tuned PA, purge, and
z-hop values). If anything misbehaves: save the `.gcode`, note the layer/time,
grab a photo and any front-panel message, then bring all of it back for the
fix loop (`edit branch profiles → check_fidelity → deploy.sh → export`).

## 0. Pre-flight

- [ ] `tools/deploy.sh` run since the last profile change; OrcaSlicer restarted
- [ ] Printer firmware ≥ 6.6.3 (start g-code asserts `M115 U6.6.3+15625`; older
      firmware will complain at print start — note the exact message if so)
- [ ] Filaments loaded match the slot assignments in Orca

## 1. Single-tool sanity print (Prusament/Generic PLA, small model)

- [ ] Start sequence: home → tool pick → `G427` tool calibration → bed soak
- [ ] During the bed soak / heat-absorb phase the nozzle holds ~100 °C
      (this validates the idle-temp guard; nozzle at 0 °C = guard failed)
- [ ] MBL runs, then purge-station prime: cleaner in, poop eject, wipe out
- [ ] First layer height and adhesion good across the plate
- [ ] No stringing/blobs mid-print (z-hop 0.2 Slope Lift, retract 0.8 @ 40 mm/s)
- [ ] Dock fan stays **OFF** the whole print (single-tool → logic must not trigger)
- [ ] End: heaters off, tool parked, head parks rear-right, dock fan off

## 2. Multi-tool print (2–3 tools, PLA, a handful of changes — not the 149-change cube)

- [ ] Toolchange dance: retract → `G27` lift (~1.5 mm) → park → pick → no
      nozzle dragging across the print on the way to the dock
- [ ] Eject-temp wait then poop eject at the purge station each change
- [ ] **First lines after each toolchange extrude immediately — no dry gap or blob.**
      This is the port's biggest judgment call (per-filament toolchange deretract
      was mapped onto `retract_length[]`); under-extrusion right after a change
      means that substitution needs revisiting
- [ ] No color bleed after the purge (minimal purge is 12 mm³ — note if it's not enough)
- [ ] Repeated changes to the *same* tool behave identically (validates the
      `tool_init` bookkeeping: first pick vs. later picks use different deretract)

## 3. Dock fan (`M106 P6`) — the logic under test

Ported rule, evaluated once after layer 1: multi-tool **and** any used tool
loaded with PLA/PVA/BVOH/FLEX/TPU/PVB → dock fan **full** (S255); else any
PETG → **30 %** (S76.5); else **off**. Purpose: parked tools sit in a warm
chamber with hot docks — the fan stops heat creep from softening low-temp
filaments inside parked hot-ends. High-temp materials leave it off so the
chamber can hold temperature.

- [ ] Multi-tool PLA print: dock fan audibly/visibly ON right after layer 1
      (not from the very start — layer 0 is fanless by design)
- [ ] Single-tool PLA print: dock fan stays OFF (checked in test 1)
- [ ] Dock fan OFF again at print end
- [ ] Watch for the failure it prevents: a parked PLA tool that jams/clicks on
      its next pick (heat creep) means the fan logic isn't protecting as intended
- [ ] If you run multi-tool PETG (no PLA): fan at low speed, not full

## 4. Orca calibration flows (the original goal)

- [ ] Calibration → Flow rate with `Prusament PLA @CORE One INDX`: slices,
      prints, result plausible vs. Prusa's 1.0 baseline
- [ ] Calibration → Temperature tower: slices and prints; best band should
      bracket 225 °C for Prusament PLA
- [ ] Save any adjusted values as user presets derived from the INDX filaments
      (system presets stay pristine)

## 5. Optional: high-temp material (ASA or PC Blend, single tool)

- [ ] Chamber sequence: bed preheats high with head parked, `M191` waits for
      chamber ≥ 40 °C, then nominal chamber set to 55 °C
- [ ] Dock fan stays OFF throughout (protects chamber temp)
- [ ] Shrinkage compensation sanity: a 100 mm part measures ~100 mm
      (validates the 0.22 %/0.18 % → `filament_shrink` conversion direction —
      if parts come out ~0.4 % *oversized*, the conversion is inverted)

## Wrap-up

- [ ] Note anything the punch list missed in this file
- [ ] Green across the board → rebase `prusa-coreone-indx-8t` on upstream main
      and prep the OrcaSlicer PR
