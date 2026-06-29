---
id: SK-dc-crac-condensate
domain: data_center
title: "CRAC condensate overflow near live racks"
match_key:
  equipment_class: crac_unit
  component: condensate_pump
  failure_mode: overflow
  capacity_band: any
  environment: indoor_controlled
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [environment, vendor]
asset_attributes_used: [proximity_to_live_racks_m, drain_type, humidity_setpoint_pct]
severity: P1
standards: ["ASHRAE TC9.9 thermal guidelines", "DC moisture / containment policy"]
status: trusted
approve_count: 4
source_cases: [DC-BLR-CRAC-04, DC-HYD-CRAC-02]
citations: ["crac-maintenance#condensate", "dc-moisture-policy#p2"]
safety_protocol: false
superseded_by: null
---

# CRAC condensate overflow near live racks

**Scope.** Computer-room AC unit, condensate evacuation. Severity is driven by **proximity to
energised racks** — moisture near live power distribution is the risk multiplier.

**Canonical signs (measurable).**
- Condensate float / overflow alarm; pan water level above limit; pump not evacuating.
- Drain flow ≈ 0 (clogged) or pump float stuck; rising sub-floor humidity near the unit.
- Distance to nearest live rack **< ~1 m** ⇒ escalate.

**Diagnosis.** Clogged drain pan/line or a failed condensate pump float → the pan overflows.
Indoor-controlled environment means it's not weather; it's the evacuation path.

**Differential.**
- Overflow with the pump running ⇒ **drain clog**; pump silent ⇒ **pump/float failure**.
- Persistent condensate generation ⇒ check the **humidity setpoint** (over-dehumidifying).

**Recipe.**
1. `clear_drain_line_and_pan`.
2. `replace_condensate_pump(if=float_failed)`.
3. `raise_ticket(priority=P1, if=near_live_racks)`.
4. `notify_dc_ops_and_facilities`.

**Risk / financial.** **P1 when near live racks** — water + energised PDU = short / outage risk
to the rack and its tenants; otherwise P2. Tie to the affected rack's SLA.

**Confirm via telemetry.** condensate-pan level, drain flow, sub-floor leak detection, room RH.

**Rule out.** humidity setpoint too aggressive, blocked drain vs failed pump, building-drain backup.
