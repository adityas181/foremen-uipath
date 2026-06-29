---
id: SK-transformer-bushing-pd
domain: power_grid
title: "Power-transformer HV bushing partial discharge (insulation failure precursor)"
match_key:
  equipment_class: power_transformer
  component: hv_bushing
  failure_mode: partial_discharge
  voltage_band: [ehv, hv]
  capacity_band: large
  environment: any
  vendor: any
hard_keys: [equipment_class, component, failure_mode, voltage_band]
soft_keys: [capacity_band, vendor, environment]
asset_attributes_used: [voltage_kV, mva_rating, bushing_type, oil_volume_l, last_dga_date]
severity: P1
standards: ["IEEE C57.104", "IEC 60599 (DGA / Duval)", "IEEE C57.19.01 (bushings)"]
status: trusted
approve_count: 3
source_cases: [GRID-SS-7-TX-2]
citations: ["transformer-dga-guide#duval", "bushing-tan-delta-limits#class", "ieee-c57104#condition-codes"]
safety_protocol: true
superseded_by: null
---

# Power-transformer HV bushing partial discharge (insulation failure precursor)

**Scope.** HV/EHV (≥ 66 kV) large power transformer, condenser-type HV bushing. Predictive,
**not** reactive — act on the trend before flashover.

**Canonical signs (measurable, per standard).**
- Dissolved-gas analysis (IEEE C57.104 / IEC 60599): **rising H₂ and CH₄ with low C₂H₂** →
  partial discharge; **C₂H₂ > 2 ppm** would instead indicate active arcing (escalate). Place the
  gas ratios on the **Duval triangle** to type the fault (PD vs D1/D2 vs thermal).
- Bushing **tan-δ (power factor) rising** toward / past the IEEE C57.19.01 limit, or **capacitance
  change > ±5%** vs nameplate.
- Online PD pulse count trending up.

**Diagnosis.** PD signature + rising combustible gases + tan-δ drift on the bushing → progressive
insulation (oil-impregnated-paper) degradation. This is a **failure precursor**: untreated it
leads to bushing flashover and a catastrophic, often violent, transformer failure.

**Differential — band & severity.**
- `hv/ehv` large unit = P1 with a regulatory + grid-stability dimension.
- A *distribution* transformer (different `voltage_band`, smaller) with the same gases is a lower
  band and a different response cadence → a separate card.
- Sustained **thermal** gases (not PD) ⇒ overheating fault, not this card.

**Recipe.**
1. `schedule_dga_retest(interval = short)` — confirm the trend, not a one-off.
2. `increase_online_pd_monitoring_cadence`.
3. `plan_bushing_replacement_outage` — coordinate with grid control for a switching window.
4. `notify_grid_control_and_protection`.

**Risk / financial.** **P1** — catastrophic-failure and safety risk (fire, oil release), plus grid
SLA / penalty and a long-lead replacement. The avoided cost of a single mega-transformer failure
dwarfs the inspection cost — the core enterprise argument for predictive maintenance.

**Confirm via telemetry.** DGA trend, bushing tan-δ / capacitance log, online PD counter,
hot-spot / top-oil temperature.

**Rule out.** sampling/lab error (retest), through-fault gassing event, recent on-load tap-changer
activity contaminating the main-tank sample.
