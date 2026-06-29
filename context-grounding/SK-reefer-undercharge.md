---
id: SK-reefer-undercharge
domain: cold_chain
title: "Reefer unit can't hold setpoint (refrigerant undercharge / slow leak)"
match_key:
  equipment_class: reefer_unit
  component: refrigerant_circuit
  failure_mode: undercharge
  capacity_band: any
  environment: any
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [vendor, environment]
asset_attributes_used: [refrigerant_type, setpoint_c, cargo_type, suction_pressure_bar]
severity: P2
standards: ["reefer OEM service manual", "cold-chain SLA / GDP", "F-gas leak-check regs"]
status: trusted
approve_count: 3
source_cases: [REEFER-IND-22, REEFER-IND-31]
citations: ["reefer-service-manual#charge", "cold-chain-sla#excursion"]
safety_protocol: false
superseded_by: null
---

# Reefer unit can't hold setpoint (refrigerant undercharge / slow leak)

**Scope.** Container/trailer reefer unit drifting off setpoint. Severity flips to **P1** the moment
**perishable cargo** is loaded (spoilage clock).

**Canonical signs (measurable).**
- Setpoint **creeping up** while the unit runs **continuously** (low duty headroom).
- **Low suction pressure**, **high superheat**, long **pull-down time** vs baseline.
- Sight-glass flashing / bubbles; gradual charge loss across trips (slow leak).

**Diagnosis.** A slow refrigerant **leak → undercharge** → insufficient mass flow to hold box
temperature. The pattern (low suction + high superheat + long pull-down) distinguishes it from a
compressor or airflow fault.

**Differential.**
- Undercharge (low suction, high superheat) vs **compressor** weakness (low capacity, normal
  charge) vs **airflow/defrost** fault (box cold at coil, warm at cargo) — different fixes.

**Recipe.**
1. `leak_test(uv_dye / electronic)`.
2. `recover_evacuate_recharge(to nameplate)`.
3. `expedite_dispatch(if=perishable_cargo)`.
4. `log_cargo_temperature_excursion(for the SLA / GDP record)`.

**Risk / financial.** **P1 with perishables** — cargo write-off + cold-chain SLA / GDP breach far
exceed the repair; otherwise P2. Quantify cargo value at risk.

**Confirm via telemetry.** box-vs-setpoint trend, suction pressure, superheat, compressor duty,
door-open events.

**Rule out.** door seal / frequent openings, defrost stuck, condenser airflow blocked, compressor wear.
