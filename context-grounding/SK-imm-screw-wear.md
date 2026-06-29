---
id: SK-imm-screw-wear
domain: manufacturing_plastics
title: "IMM plasticising screw & barrel wear (small/mid toggle, abrasive resin)"
match_key:
  equipment_class: injection_moulding_machine
  clamp_architecture: toggle
  component: plasticising_screw
  failure_mode: screw_barrel_wear
  capacity_band: [small, mid]
  material: abrasive
  environment: any
  vendor: any
hard_keys: [equipment_class, clamp_architecture, component, failure_mode, capacity_band, material]
soft_keys: [vendor, environment]
asset_attributes_used: [tonnage_T, clamp_architecture, screw_diameter_mm, resin_grade]
severity: P2
standards: ["SPE/SPI screw-wear bulletin", "OEM barrel-bore tolerance table"]
status: trusted
approve_count: 5
source_cases: [PLANT-A-IMM-07, PLANT-C-IMM-02]
citations: ["imm-screw-wear-guide#p2", "resin-abrasion-table#glassfill", "barrel-bore-tolerance#class"]
safety_protocol: false
superseded_by: null
---

# IMM plasticising screw & barrel wear (small/mid toggle, abrasive resin)

**Scope.** Toggle-clamp IMM, **≤ 650 T** (`small`/`mid`), running **abrasive** resin
(glass/mineral-filled, ≥ 20% filler). Not for large two-platen machines (different recipe).

**Canonical signs (measurable).**
- Shot-weight drift **> ±1.5%** over a run with the same setpoints.
- Recovery (screw-back) time up **> 15%** vs commissioning baseline.
- Barrel-bore wear or screw-flight OD loss beyond OEM class (typ. **> 0.10–0.15 mm** radial).
- Output fall-off + barrel-zone temperatures running hot to compensate; flashing.

**Diagnosis.** Abrasive filler erodes the screw flights, barrel bore and check-ring over service
hours → growing clearance → melt backflow during recovery → lower, less repeatable output. This
is **wear**, not a process-setting fault; on filled resins it is the expected wear-out mode.

**Differential — band & architecture.**
- This card = **toggle, ≤650 T**. On a **two-platen / large** machine the same shot-weight drift
  is more often a *tie-bar imbalance* (clamp side) — see `SK-imm-tiebar-imbalance`.
- Pure suck-back/cushion instability without flight wear ⇒ `SK-imm-checkring-suckback`.

**Recipe.**
1. `measure_screw_OD_and_barrel_bore` — compare to OEM class table; quantify radial clearance.
2. `replace_with_bimetallic_screw_and_liner(if=abrasive)` — bimetallic/nitrided for filled resin.
3. `replace_check_ring_and_seat`.
4. `re_baseline_recovery_time_and_cushion(shots>=30)`.

**Risk / financial.** P2 — scrap-rate and cycle-time creep; quantify scrap ₹/shift. Schedule into
the next planned stop rather than emergency unless scrap > threshold.

**Confirm via telemetry.** recovery-time trend, cushion stability, barrel-zone power draw,
shot-weight SPC chart.

**Rule out.** resin moisture / drying, screw-tip assembly torque, wrong backpressure setpoint.
