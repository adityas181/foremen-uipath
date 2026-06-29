---
id: SK-pv-mc4-connector-burn
domain: energy_solar
title: "PV MC4 string-connector overheat / melt (high-resistance contact -> DC arc, fire risk)"
match_key:
  equipment_class: pv_array
  component: mc4_connector
  failure_mode: connector_overheat_melt
  capacity_band: any
  environment: outdoor
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [environment, vendor]
asset_attributes_used: [string_voltage_v, string_current_a, connector_brand, install_date]
severity: P1
standards: ["IEC 62852 (PV connectors)", "NEC 690.11 (DC AFCI)", "IEC 62548 (PV array design)", "UL 6703"]
status: candidate
approve_count: 1
source_cases: [SOLAR-RJ-MC4-14]
citations: ["mc4-connector-install-spec#crimp", "pv-dc-arc-safety-bulletin#p1", "connector-cross-mating-warning#p2"]
safety_protocol: true
superseded_by: null
---

# PV MC4 string-connector overheat / melt (high-resistance contact -> DC arc, fire risk)

**Scope.** In-line **MC4 string connector** on a PV array showing thermal damage. **Safety-critical**
(self-sustaining DC arc + fire) — isolate before touching.

**Canonical signs (what the engineer's photo/clip shows + measurable).**
- **Melted / deformed connector housing**; **charred, blackened contact** inside the body.
- **Brown / discoloured insulation** at the pin; **frayed or splayed exposed copper strands** at
  the crimp (a visible bad-termination clue).
- Thermal scan **ΔT well above neighbouring connectors**; **string-current imbalance** or
  intermittent string drop-outs; AFCI events.

**Diagnosis.** A **high-resistance MC4 contact** dissipates I²R heat at the joint → the housing
melts and the contact chars → it escalates to a **self-sustaining DC series arc** (fire). Root
cause is one of: a **poor/loose crimp** (the frayed copper points here), **cross-mated**
connectors (genuine vs "MC4-compatible" brands forced together), or **water ingress / oxidation**.
The agent reasons *visible melt + frayed crimp -> high-resistance joint*, not just "it's burnt."

**Differential.**
- **Connector-level** (this card, in-line MC4) vs **combiner-box busbar/fuse** arc
  (`SK-pv-combiner-arc`) vs a **module hot-spot** (cell / junction box — not the connector).
- Within connector-level: poor crimp vs cross-mating vs water ingress — confirm before re-terminating.

**Recipe.**
1. `de_energize_string(open_dc_isolator under no-load)` + `lockout_tagout`.
2. `cut_out_and_replace_both_mating_connectors(matched genuine pair, re-crimp to spec)`.
3. `thermal_scan_adjacent_strings_and_combiner`.
4. `audit_array_for_cross_mated_connectors` (a systemic install defect, not a one-off).

**Risk / financial.** **P1 / safety** — connector overheating is a leading cause of rooftop/solar
fires; risk is asset loss + life-safety + lost generation. The avoided-loss case for fast
isolation + re-termination is overwhelming. If cross-mating is found array-wide, it's a **systemic
fleet review** (the Fleet agent escalates).

**Confirm via telemetry.** per-string current/voltage, AFCI / arc-fault events, IR thermal scan,
ground-fault monitor.

**Rule out.** module hot-spot (not connector), combiner-box busbar, simple surface corrosion with
no heat signature, normal weathering discolouration.
