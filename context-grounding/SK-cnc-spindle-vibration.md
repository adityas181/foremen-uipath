---
id: SK-cnc-spindle-vibration
domain: manufacturing_cnc
title: "CNC spindle-bearing vibration rise (preload loss / spalling)"
match_key:
  equipment_class: cnc_machine
  component: spindle_bearing
  failure_mode: vibration_spike
  capacity_band: any
  environment: any
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [vendor, environment]
asset_attributes_used: [spindle_rpm_max, bearing_arrangement, hours_since_rebuild]
severity: P2
standards: ["ISO 20816 / ISO 10816 (vibration zones)", "bearing-envelope (HFD) method"]
status: candidate
approve_count: 1
source_cases: [PLANT-A-CNC-12]
citations: ["spindle-vibration-iso10816#band", "spindle-rebuild-note#preload"]
safety_protocol: false
superseded_by: null
---

# CNC spindle-bearing vibration rise (preload loss / spalling)

**Scope.** Machining-centre / lathe spindle. Trended by **ISO 20816** vibration zones; act at
entry to **zone C**, hold the spindle at **zone D**.

**Canonical signs (measurable).**
- RMS velocity crossing **ISO 20816 zone C** threshold for the spindle class.
- **Bearing-envelope / HFD** (high-frequency) spikes at bearing defect frequencies (BPFO/BPFI).
- **Surface-finish (Ra) drift** on parts; audible whine; thermal rise at the spindle nose.

**Diagnosis.** Preload loss or early **spalling** of the spindle bearings → rising vibration and
finish defects. Catch in zone C, before seizure → a spindle crash and a far costlier rebuild.

**Differential.**
- **Bearing** spalling (defect-frequency energy, HFD) vs **imbalance/tool** (1× rpm) vs mechanical
  **looseness** (harmonics/sub-harmonics) — the spectrum says which; don't rebuild for a tool issue.

**Recipe.**
1. `trend_vibration(ISO 20816, window=72h)`.
2. `hold_high_precision_jobs`.
3. `schedule_spindle_rebuild(matched preload set)`.
4. `order_matched_bearing_set`.

**Risk / financial.** **P2** — escalates fast: a seized spindle = long downtime + scrapped
in-process parts + expensive rebuild. Quantify the line's ₹/hr.

**Confirm via telemetry.** ISO-20816 RMS trend, envelope spectrum (BPFO/BPFI), spindle temp, part-Ra SPC.

**Rule out.** tool imbalance / runout, workholding looseness, foundation/coupling, coolant in bearing.
