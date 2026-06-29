---
id: SK-rail-axle-hotbox
domain: rail_transport
title: "Rail bogie axle-bearing hot-box (thermal runaway — safety)"
match_key:
  equipment_class: rail_bogie
  component: axle_bearing
  failure_mode: thermal_overheat
  capacity_band: any
  environment: any
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [vendor, environment]
asset_attributes_used: [bearing_type, axle_load_t, hbd_alarm_level, mileage_since_overhaul]
severity: P1
standards: ["AAR/UIC axle-bearing standard", "hot-box detector (HBD) thresholds", "rail safety reg"]
status: trusted
approve_count: 4
source_cases: [CONSIST-44-AX-7]
citations: ["rail-bearing-standard#hotbox", "rail-safety-reg#incident"]
safety_protocol: true
superseded_by: null
---

# Rail bogie axle-bearing hot-box (thermal runaway — safety)

**Scope.** Wagon/coach bogie axle bearing flagged by a **wayside hot-box detector (HBD)**.
**Safety-critical** — handled as a safety incident, never a routine repair.

**Canonical signs (measurable).**
- HBD **alarm / warm-axle** flag; bearing temperature **> ambient + ~50–70 °C** (or absolute HBD
  threshold) and a high **rate of rise** between detectors.
- Acoustic / grease-degradation indicators; one axle hotter than the rest of the consist.

**Diagnosis.** Bearing degradation (grease breakdown, brinelling, water ingress) → friction →
**thermal runaway**. Untreated it ends in a seized axle / burn-off and **derailment**.

**Differential.**
- Hot **bearing** vs **brake binding** (also produces heat, but at the wheel/tread, not the axle
  end) — confirm the heat source before acting; the remedy differs.

**Recipe.**
1. `stop_consist_at_next_safe_point`.
2. `isolate_affected_wagon`.
3. `schedule_bearing_replacement`.
4. `file_regulatory_incident_log`.

**Risk / financial.** **P1 / safety** — derailment risk dwarfs everything; regulatory reportable.
The detain-and-inspect cost is trivial against the consequence.

**Confirm via telemetry.** HBD trend across successive detectors, on-board temp/acoustic sensors,
rate-of-rise.

**Rule out.** brake binding (wheel heat), HBD sensor error (cross-check next detector), recent heavy braking.
