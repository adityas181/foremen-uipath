---
id: SK-tower-anchorbolt-torque
domain: telecom_structural
title: "Tower anchor-bolt torque loss after high wind (RETIRED — superseded)"
match_key:
  equipment_class: telecom_tower
  component: anchor_bolt
  failure_mode: torque_loss
  capacity_band: any
  environment: high_wind
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [environment, vendor]
asset_attributes_used: [tower_height_m, wind_zone, bolt_grade, last_torque_check]
severity: P1
standards: ["TIA-222 (tower structural)", "OEM base-plate torque spec"]
status: retired
approve_count: 1
source_cases: [TOWER-CST-14]
citations: ["tower-structural-manual#anchor"]
safety_protocol: true
superseded_by: SK-tower-structural-fatigue-v2
---

# Tower anchor-bolt torque loss after high wind (RETIRED — superseded)

**Scope.** Self-support / guyed tower base anchor bolts in a high-wind zone. **Safety-critical.**

**Canonical signs (measurable).**
- Bolt **torque below spec** on check; visible **base-plate gap / movement**; nut backing off.
- Repeated loosening after named high-wind events.

**Diagnosis.** Cyclic wind loading relaxes anchor-bolt preload → base-plate loosening.

**Why retired.** The simple "re-torque + locking washers" recipe **missed fatigue cracking** in
the anchor assembly that a torque check alone can't see. **Superseded by
`SK-tower-structural-fatigue-v2`**, which mandates an NDT / structural inspection *first*. Kept
here to demonstrate the **retire path**: a thumbs-down / better evidence pushes a card to
`retired` with a `superseded_by` pointer, and the matcher stops serving it.

**Recipe (deprecated — do not auto-apply).**
1. `re_torque_to_spec`.
2. `install_locking_washers`.
3. `schedule_structural_inspection`.

**Risk / financial.** **P1 / safety** — structural; this is exactly why a torque-only recipe was
unsafe and got retired.

**Confirm via telemetry.** bolt-tension monitor, base-plate strain, tilt sensor, post-event checks.

**Rule out.** (handled by the superseding card via NDT before any re-torque.)
