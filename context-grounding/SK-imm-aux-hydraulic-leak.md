---
id: SK-imm-aux-hydraulic-leak
domain: manufacturing_plastics
title: "IMM clamp/aux hydraulic rod-seal leak (large/mega two-platen)"
match_key:
  equipment_class: injection_moulding_machine
  clamp_architecture: two_platen
  component: clamp_cylinder_seal
  failure_mode: rod_seal_leak
  capacity_band: [large, mega]
  material: any
  environment: any
  vendor: any
hard_keys: [equipment_class, clamp_architecture, component, failure_mode, capacity_band]
soft_keys: [material, vendor, environment]
asset_attributes_used: [tonnage_T, clamp_architecture, system_pressure_bar]
severity: P2
standards: ["OEM hydraulic schematic", "ISO 4413 hydraulic safety"]
status: candidate
approve_count: 2
source_cases: [PLANT-B-IMM-11]
citations: ["imm-hydraulics-manual#aux-circuit", "seal-extrusion-note#p1"]
safety_protocol: false
superseded_by: null
---

# IMM clamp/aux hydraulic rod-seal leak (large/mega two-platen)

**Scope.** **Two-platen** hydraulic IMM, **≥ 650 T** (`large`/`mega`), clamp / auxiliary cylinder
circuit. Not the same as a screw/injection fault, and not a small-toggle machine.

**Canonical signs (measurable).**
- Clamp-pressure droop / longer pressure-hold time; oil weep at the gland / rod gland.
- System pressure spikes **> 10–15%** over nominal on movement transitions.
- Reservoir level fall; tonnage repeatability drifting across the four corners.

**Diagnosis.** Pressure spikes on a high-pressure clamp/aux circuit extrude the **cylinder
rod-seal** → external weep + internal bypass → the cylinder cannot hold force cleanly. On a
two-platen machine the clamp cylinders are short-stroke and high-pressure, so seal extrusion is
the classic field mode.

**Differential — band & architecture.**
- This card = **two-platen, large/mega**. On a `toggle` machine there is no clamp cylinder of this
  kind; a leak there is the injection or ejector circuit (different card).
- If the symptom is *tonnage imbalance* rather than a *leak* ⇒ `SK-imm-tiebar-imbalance`.

**Recipe.**
1. `isolate_and_lockout_hydraulics` (ISO 4413) — depressurise before opening the gland.
2. `replace_rod_seal_and_wiper_kit`.
3. `install_or_check_pressure_dampener` — cut the spikes that extruded the seal.
4. `audit_relief_valve_setpoint_vs_OEM`.

**Risk / financial.** P2 — escalates to P1 if leak is near hot zones (fire) or tonnage loss is
scrapping parts; mega-machine downtime is very high ₹/hr, so quantify.

**Confirm via telemetry.** clamp-pressure trend, reservoir level, corner-tonnage balance.

**Rule out.** relief-valve chatter, pump wear, contaminated oil eroding seals.
