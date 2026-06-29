---
id: SK-dg-injector-knock
domain: telecom_power
title: "Diesel generator knock under load (injector timing / worn bearings)"
match_key:
  equipment_class: diesel_generator
  component: injector
  failure_mode: knock_under_load
  capacity_band: mid
  environment: any
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [capacity_band, vendor, environment]
asset_attributes_used: [kva_rating, oil_pressure_bar, running_hours, last_service_date]
severity: P2
standards: ["OEM engine service manual", "ISO 8528 (gensets)", "oil-analysis limits"]
status: trusted
approve_count: 3
source_cases: [DEL-0473, PUN-0188]
citations: ["dg-maintenance-manual#knock", "anti-patterns#oil-pressure"]
safety_protocol: false
superseded_by: null
---

# Diesel generator knock under load (injector timing / worn bearings)

**Scope.** Backup diesel genset (mid kVA) showing combustion knock under load with the lube
system healthy. Distinct from a lubrication-failure knock.

**Canonical signs (measurable).**
- Audible knock that **appears/worsens above ~50% load**, with **oil pressure NORMAL**
  (within OEM band, e.g. > 3 bar hot).
- Exhaust-temperature imbalance between cylinders; fuel-rail pressure drift.
- Recurs across two service visits (not a one-off after a cold start).

**Diagnosis.** Knock under load with normal oil pressure → **injector timing drift or worn
big-end bearings**, not lubrication failure. Recurrence means re-adjustment won't hold → swap.

**Differential.**
- Knock with **LOW oil pressure** ⇒ lubrication / bearing-lube fault — a *different* cause
  (anti-pattern: don't diagnose injectors when oil pressure is low).
- Knock only when cold that clears warm ⇒ ignore (normal).

**Recipe.**
1. `order_injector_service_kit`.
2. `schedule_dg_swap(if=recurrent)`.
3. `monitor_oil_pressure(window=72h)` — confirm it isn't a lube fault.

**Risk / financial.** **P2** (backup asset) — escalates to **P1** if grid mains are down and this
genset is the only supply. Quantify outage risk to the site.

**Confirm via telemetry.** per-cylinder exhaust temp, oil pressure trend, fuel-rail pressure,
load-vs-knock correlation.

**Rule out.** low oil pressure (lube fault), bad fuel batch, air in fuel, cold-start artefact.
