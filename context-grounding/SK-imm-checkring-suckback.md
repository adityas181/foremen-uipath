---
id: SK-imm-checkring-suckback
domain: manufacturing_plastics
title: "IMM inconsistent suck-back / cushion loss (check-ring / NRV wear)"
match_key:
  equipment_class: injection_moulding_machine
  clamp_architecture: any
  component: check_ring_nrv
  failure_mode: inconsistent_suckback
  capacity_band: any
  material: any
  environment: any
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [clamp_architecture, capacity_band, material, vendor, environment]
asset_attributes_used: [tonnage_T, screw_diameter_mm, nrv_type, decompression_mm]
severity: P2
standards: ["OEM screw-tip / NRV service manual", "SPE process-stability guide"]
status: candidate
approve_count: 1
source_cases: [PLANT-D-IMM-05]
citations: ["imm-screw-tip-assembly#nrv", "decompression-setting-guide#p2", "imm-cushion-stability#p1"]
safety_protocol: false
superseded_by: null
---

# IMM inconsistent suck-back / cushion loss (check-ring / NRV wear)

**Scope.** Any IMM where the screw rotates and feeds normally but the **suck-back (decompression)
behaves erratically** and the **cushion is unstable**. (This is the failure described in the demo
clip — a hydraulic IMM, "screw rotation… feeding… suck-back is a big problem".)

**Canonical signs (measurable).**
- Cushion variation **> 0.5 mm** shot-to-shot, or a steadily **falling cushion**.
- Suck-back not holding → nozzle drool / stringing, or air pulled in → splay/bubbles.
- Injection-pressure-integral drift at constant setpoint; short shots / sink appear intermittently.

**Diagnosis.** Melt backflows past a worn **check ring / non-return valve (NRV)** on the screw
tip → the screw cannot hold a repeatable cushion, so decompression is erratic. Confirm only after
ruling out the **decompression *setting*** (a mis-set suck-back stroke mimics the symptom).

**Differential — band & architecture.**
- `toggle ≤650 T`: NRV is a screw-tip part swap; quick.
- `two_platen / large`: same symptom but the screw/NRV assembly is large and the resin is often
  engineering-grade — confirm screw-tip wear too, and the downtime cost is far higher (plan it).

**Recipe.**
1. `verify_decompression_setting` — set suck-back stroke to spec; re-check cushion first.
2. `inspect_check_ring_seat_and_screw_tip` — measure ring/seat clearance.
3. `replace_nrv_assembly(if=worn)` — free-flow vs locking ring per resin.
4. `confirm_repeatable_cushion(variation < 0.3 mm, shots >= 20)`.

**Risk / financial.** P2 — quality variation (scrap, sink, short shots); on engineering resins the
scrap value per shot is high, so quantify ₹/shift before deciding emergency vs planned.

**Confirm via telemetry.** cushion SPC chart, recovery-time trend, injection-pressure-integral.

**Rule out.** decompression mis-set, screw-tip torque loose, resin viscosity / moisture change.
