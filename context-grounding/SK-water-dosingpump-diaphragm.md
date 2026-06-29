---
id: SK-water-dosingpump-diaphragm
domain: water_utilities
title: "Chemical dosing-pump diaphragm rupture (wetted-material incompatibility)"
match_key:
  equipment_class: dosing_pump
  component: diaphragm
  failure_mode: rupture
  capacity_band: small
  environment: corrosive_chemical
  vendor: any
hard_keys: [equipment_class, component, failure_mode, environment]
soft_keys: [capacity_band, vendor]
asset_attributes_used: [chemical_type, wetted_material, backpressure_bar, dosing_rate_lph]
severity: P2
standards: ["pump O&M manual", "chemical-compatibility chart (PTFE/EPDM/PVDF)", "ISO 4413"]
status: candidate
approve_count: 2
source_cases: [WTP-EAST-DP-3]
citations: ["dosing-pump-manual#diaphragm", "chemical-compatibility-chart#p4"]
safety_protocol: false
superseded_by: null
---

# Chemical dosing-pump diaphragm rupture (wetted-material incompatibility)

**Scope.** Small metering / dosing pump on a **corrosive-chemical** duty (e.g. sodium
hypochlorite, ferric chloride). The discriminator is the chemical + wetted material, not size.

**Canonical signs (measurable).**
- Dosing flow **drop / loss**; chemical **weep at the pump head**; leak-detection trip.
- Backpressure outside band; stroke not producing rated `lph`.
- Diaphragm material vs chemical = mismatch on the compatibility chart.

**Diagnosis.** A wetted-material mismatch (or over-pressure spikes) degrades and **ruptures the
diaphragm** → loss of dosing + chemical release. Usually incompatibility, not simple wear.

**Differential.**
- True **rupture** (chemical weep + flow loss) vs **valve clog** (flow loss, no weep) vs
  **air-lock** (flow loss, primes after bleeding) — different remedy.

**Recipe.**
1. `replace_diaphragm(material=PTFE/PVDF per compatibility chart)`.
2. `verify_chemical_compatibility(wetted parts vs dosed chemical)`.
3. `set_backpressure_valve(within band)`.
4. `calibrate_stroke(to rated lph)`.

**Risk / financial.** **P2**, escalates if it's a **disinfection** dose (water-quality compliance
breach) — then it carries a regulatory dimension. Tie to the treatment SLA.

**Confirm via telemetry.** dosing-flow trend, residual-chlorine analyser, leak detection, stroke counter.

**Rule out.** valve/check clog, air-lock, suction-side starvation, over-pressure event.
