---
id: SK-elevator-sheave-wear
domain: vertical_transport
title: "Traction elevator drive-sheave groove wear (rope slip — safety)"
match_key:
  equipment_class: traction_elevator
  component: drive_sheave
  failure_mode: groove_wear
  capacity_band: any
  environment: any
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [vendor, environment]
asset_attributes_used: [rated_load_kg, rope_count, last_inspection_date, traction_ratio]
severity: P1
standards: ["EN 81-20 / EN 81-50", "ASME A17.1 / A17.6", "lift safety code"]
status: trusted
approve_count: 6
source_cases: [TOWER-A-LIFT-2, MALL-N-LIFT-5]
citations: ["elevator-traction-manual#sheave", "lift-safety-code#traction"]
safety_protocol: true
superseded_by: null
---

# Traction elevator drive-sheave groove wear (rope slip — safety)

**Scope.** Geared/gearless traction lift, drive sheave. **Safety-critical** — the car comes out of
service before any repair.

**Canonical signs (measurable).**
- Rope **slip** (sheave turns, car lags); **levelling error** > floor-stop tolerance (e.g. > 10 mm).
- Uneven groove **undercut / step**; rope seating below the groove pitch line.
- Vibration/noise at the machine; traction ratio degrading toward the safety limit (EN 81-50).

**Diagnosis.** Worn / undercut sheave grooves reduce the rope-to-sheave traction grip → slip and
levelling faults; if it progresses it threatens overspeed/levelling safety functions.

**Differential.**
- Sheave **groove** wear (uneven undercut) vs **rope** wear/stretch vs **brake** slip — each a
  different remedy. Confirm which surface is failing before regrooving.

**Recipe.**
1. `lockout_tagout`.
2. `take_car_out_of_service`.
3. `schedule_sheave_regroove_or_replacement(per EN 81-50 traction check)`.
4. `mandatory_safety_signoff_before_return`.

**Risk / financial.** **P1 / safety** — entrapment and fall-arrest functions depend on traction;
also a regulatory inspection item. Out-of-service cost vs the safety liability is no contest.

**Confirm via telemetry.** levelling-error log, machine vibration, slip detection, trip history.

**Rule out.** rope wear/stretch, brake torque loss, governor issue.
