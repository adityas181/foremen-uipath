---
id: SK-escalator-stepchain
domain: vertical_transport
title: "Escalator step-chain elongation (entrapment risk — safety)"
match_key:
  equipment_class: escalator
  component: step_chain
  failure_mode: elongation
  capacity_band: any
  environment: any
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [vendor, environment]
asset_attributes_used: [rise_m, step_width_mm, chain_pitch_mm, last_inspection_date]
severity: P1
standards: ["EN 115 (escalators)", "ASME A17.1", "OEM chain service limit"]
status: candidate
approve_count: 2
source_cases: [METRO-ST-ESC-3]
citations: ["escalator-maintenance#stepchain", "lift-safety-code#escalator"]
safety_protocol: true
superseded_by: null
---

# Escalator step-chain elongation (entrapment risk — safety)

**Scope.** Public-transport / commercial escalator step chain. **Safety-critical** — out of
service before adjustment.

**Canonical signs (measurable).**
- Measured **chain elongation beyond the OEM service limit** (typically **> ~2%** of pitch).
- **Step-indexing fault** / comb-plate impact; broken-step-chain switch nuisance trips; rattle.
- Increasing tensioning-carriage travel toward its limit.

**Diagnosis.** Wear elongates the step chain past its service limit → steps mis-index at the
comb plate → step-gap and **entrapment** hazard. It's a wear-out, not a setting.

**Differential.**
- **Chain** elongation (tensioner near limit, even rattle) vs **step-roller** wear (localised
  thump) vs **comb-plate** damage (impact marks) — different parts.

**Recipe.**
1. `take_out_of_service`.
2. `measure_chain_pitch_vs_service_limit(EN 115)`.
3. `replace_step_chain_set(both sides)`.
4. `safety_signoff_before_return`.

**Risk / financial.** **P1 / safety** — entrapment / fall injury and a regulatory inspection item;
public footfall raises the exposure. Downtime is the right trade.

**Confirm via telemetry.** tensioner-carriage position, broken-chain switch events, step-index sensor.

**Rule out.** step-roller wear, comb-plate damage, drive-chain (not step-chain), handrail-sync drift.
