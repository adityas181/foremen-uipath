---
id: SK-pv-combiner-arc
domain: energy_solar
title: "PV combiner-box DC series arc / connector burn (fire risk — safety)"
match_key:
  equipment_class: pv_array
  component: combiner_box
  failure_mode: dc_arc_connector_burn
  capacity_band: any
  environment: outdoor
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [environment, vendor]
asset_attributes_used: [string_count, dc_voltage_v, afci_present, last_thermal_scan]
severity: P1
standards: ["NEC 690.11 (DC AFCI)", "IEC 62852 (PV connectors)", "UL 1699B (arc-fault)"]
status: candidate
approve_count: 1
source_cases: [SOLAR-RJ-CB-09]
citations: ["pv-combiner-spec#mc4", "dc-arc-safety-bulletin#p1"]
safety_protocol: true
superseded_by: null
---

# PV combiner-box DC series arc / connector burn (fire risk — safety)

**Scope.** String combiner box / MC4 connectors / fuse holders on a PV array. **Safety-critical**
(DC arc + fire) — isolate before touching.

**Canonical signs (measurable).**
- Scorching / melted insulation at MC4 connectors or fuse holders; soot.
- **Arc-fault detector (AFCI) trip** (NEC 690.11); **thermal scan ΔT** at a connector well above
  its neighbours; **string-current imbalance**.
- Intermittent string drop-outs.

**Diagnosis.** A high-resistance joint (poor crimp, water ingress, mismatched connectors) creates
a **DC series arc fault** — self-sustaining on PV DC and a fire risk. The burn is the symptom; the
loose/oxidised joint is the cause.

**Differential.**
- **Series** arc (in-line connector/fuse) vs **parallel/ground** arc (insulation to ground) vs a
  module **hot-spot** — different location and remedy. Thermal scan localises it.

**Recipe.**
1. `de_energize_string(open_dc_isolator)`.
2. `lockout_tagout`.
3. `replace_connectors_and_fuse(matched, IEC 62852)`.
4. `thermal_scan_adjacent_strings`.

**Risk / financial.** **P1 / safety** — fire and asset-loss risk; arc faults have burned down
combiner boxes and roofs. The avoided-loss case for fast isolation is overwhelming.

**Confirm via telemetry.** AFCI events, per-string current, connector thermal trend, ground-fault monitor.

**Rule out.** module hot-spot (not connector), ground fault, simple fuse blow without arcing.
