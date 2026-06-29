---
id: SK-hvac-chiller-shortcycle
domain: facilities_hvac
title: "Rooftop chiller compressor short-cycling (condenser fouling / low charge)"
match_key:
  equipment_class: rooftop_chiller
  component: compressor
  failure_mode: short_cycling
  capacity_band: mid
  environment: hot_humid
  vendor: any
hard_keys: [equipment_class, component, failure_mode]
soft_keys: [capacity_band, environment, vendor]
asset_attributes_used: [tr_rating, refrigerant_type, ambient_c, head_pressure_psi]
severity: P2
standards: ["ASHRAE refrigeration guide", "OEM superheat/subcool table"]
status: trusted
approve_count: 3
source_cases: [MALL-WEST-CH-3, OFFICE-12-CH-1]
citations: ["chiller-troubleshooting#hp-trip", "refrigerant-charge-table#subcool"]
safety_protocol: false
superseded_by: null
---

# Rooftop chiller compressor short-cycling (condenser fouling / low charge)

**Scope.** Mid-capacity rooftop/air-cooled chiller in **hot-humid** ambient, compressor cycling on
its high-pressure protection. Not a contactor/electrical chatter case.

**Canonical signs (measurable).**
- Compressor starts **> 6–8 / hour** (well above design cycle rate).
- **High head pressure** tripping the HP cutout; **subcooling out of band** (low ⇒ undercharge).
- Discharge temperature high; suction pressure low.

**Diagnosis.** High head pressure from **condenser-coil fouling** (poor heat rejection) or **low
refrigerant** trips the HP cutout → the compressor short-cycles. Hot-humid ambient makes fouling
the prime suspect.

**Differential.**
- **Steady** head pressure with electrical chatter ⇒ contactor / control fault, not refrigeration.
- Low subcooling ⇒ undercharge; high subcooling + dirty coil ⇒ fouling. Different fixes.

**Recipe.**
1. `clean_condenser_coil`.
2. `leak_test_and_recharge(if=low_subcool)`.
3. `verify_superheat_subcool(per OEM table)`.
4. `log_runtime_baseline`.

**Risk / financial.** **P2** — comfort + compressor wear (short-cycling shortens compressor life);
escalates if it serves a critical load (server room, cold storage).

**Confirm via telemetry.** cycles/hr, head/suction pressure, discharge temp, compressor run-time.

**Rule out.** contactor chatter, fan failure, blocked airflow, thermostat differential too tight.
