---
id: SK-imm-tiebar-imbalance
domain: manufacturing_plastics
title: "IMM tie-bar strain / corner-tonnage imbalance (large/mega two-platen)"
match_key:
  equipment_class: injection_moulding_machine
  clamp_architecture: two_platen
  component: tie_bar_clamp
  failure_mode: tonnage_imbalance
  capacity_band: [large, mega]
  material: any
  environment: any
  vendor: any
hard_keys: [equipment_class, clamp_architecture, component, failure_mode, capacity_band]
soft_keys: [material, vendor, environment]
asset_attributes_used: [tonnage_T, clamp_architecture, tie_bar_count, strain_gauge_present]
severity: P2
standards: ["OEM tie-bar strain-balance procedure", "platen parallelism spec (µm/m)"]
status: trusted
approve_count: 3
source_cases: [PLANT-MEGA-1800-02, PLANT-MEGA-2500-01]
citations: ["two-platen-clamp-manual#strain-balance", "platen-parallelism-spec#class", "halfnut-wear-bulletin#p1"]
safety_protocol: false
superseded_by: null
---

# IMM tie-bar strain / corner-tonnage imbalance (large/mega two-platen)

**Scope.** **Two-platen** hydraulic IMM, **≥ 1800 T** (`mega`; also large two-platen 800–1800 T).
This failure mode **does not exist on a small toggle machine** — it is specific to the four-tie-bar
locking architecture. This card is the canonical example of "same complaint, different machine,
different cause."

**Canonical signs (measurable).**
- Flash on one side of the part / one mould corner; part-weight asymmetry across cavities.
- **Tie-bar strain spread > 5–8%** corner-to-corner (from on-machine strain gauges).
- **Platen parallelism out of spec** (typ. > 0.05–0.10 mm/m); half-nut / locking-nut wear marks.
- "Won't build full tonnage" or tonnage repeatability drift — *with the injection unit healthy*.

**Diagnosis.** On a two-platen clamp, clamp force is reacted through **four tie-bars locked by
split half-nuts**. Uneven tie-bar strain (worn half-nuts, mould-mounting asymmetry, platen
parallelism drift) → the four corners carry unequal force → localised flash and dimensional
variation. The injection side (screw, NRV, cushion) is **fine** — so a screw/suck-back recipe
would be the wrong fix here. That contrast is the whole point of gating on
`clamp_architecture` + `capacity_band`.

**Differential — why a toggle/small card is wrong here.**
- `toggle ≤650 T`: no tie-bar half-nut lock; the analogous "flash" cause is toggle-pin wear or
  mould-height set → a different card and a different recipe.
- Same machine but shot-weight drift with healthy clamp ⇒ injection side
  (`SK-imm-screw-wear` / `SK-imm-checkring-suckback`).

**Recipe.**
1. `run_tie_bar_strain_balance(per OEM)` — read all four corners under clamp; quantify spread.
2. `inspect_half_nuts_and_locking_segments` — measure wear; replace if out of tolerance.
3. `check_platen_parallelism(µm/m)` and re-shim / re-level mould mounting.
4. `re_balance_and_verify(flash gone, strain spread < 3%)`.

**Risk / financial.** P2, escalates fast — a mega two-platen line is very high ₹/hr; sustained
imbalance also overloads tie-bars (fatigue) and wrecks expensive moulds, so it carries a real
asset-damage tail. Quantify scrap ₹/shift + mould-risk before scheduling.

**Confirm via telemetry.** per-corner tie-bar strain, clamp-tonnage repeatability, cavity-pressure
balance, platen-parallelism log.

**Rule out.** mould-mounting asymmetry, uneven mould-height set, thermal expansion not stabilised.
