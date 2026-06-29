---
id: SK-coastal-rf-corrosion
domain: telecom_tower
title: "Coastal RF jumper connector galvanic corrosion (non-marine spec defect)"
match_key:
  equipment_class: rf_jumper_cable
  component: connector
  failure_mode: galvanic_corrosion
  spec: non-marine
  environment: coastal
  vendor: any
hard_keys: [equipment_class, component, failure_mode, spec, environment]
soft_keys: [vendor]
asset_attributes_used: [site_environment, humidity_pct, cable_spec, batch_id, warranty_status]
severity: P1
standards: ["ASTM B117 (salt-fog)", "connector IP/material spec", "telecom O&M corrosion guide"]
status: trusted
approve_count: 4
source_cases: [DEL-0473, MUM-0210, GOA-0188, KOC-0231]
citations: ["rf-cable-spec-NG-22#p3", "corrosion-troubleshooting#p1", "anti-patterns#discolouration", "sla-master#c7"]
safety_protocol: false
superseded_by: null
---

# Coastal RF jumper connector galvanic corrosion (non-marine spec defect)

**Scope.** Non-marine-rated RF jumper connector at a **coastal / high-salinity** site
(humidity **> 80%**). Not for dry-inland sites or marine-grade cable (different cause/recipe).

**Canonical signs (measurable).**
- Green/white deposits **with pitting** at the connector (ASTM B117 salt-fog signature).
- RF degradation: **return loss / VSWR worsening** (e.g. VSWR > 1.5), **PIM** test failing,
  insertion loss up — the RF-measurable proof, not just a photo.
- Site humidity > 80%, salt-laden air; cable spec = `non-marine`.

**Diagnosis.** Salt + humidity drive galvanic corrosion at a connector whose material rating is
wrong for the environment → a **spec defect** (vendor used non-marine cable on the coast), not
field workmanship.

**Differential.**
- Spec defect requires `coastal + non-marine + humidity>80%`. On a **dry** site or with
  **marine-grade** cable, corrosion of this kind shouldn't occur → look at workmanship / water
  ingress instead.
- **Discolouration without pitting or deposits is NOT corrosion** — do not call it (anti-pattern).

**Recipe.**
1. `raise_ticket(priority=P1)`.
2. `warranty_claim(basis=spec_defect, within_window=true)` — reframe as a vendor material defect.
3. `cluster_upgrade(to=marine_grade_NG-30)` — pre-empt the rest of the coastal cluster.

**Risk / financial.** **P1** — multi-tenant SLA exposure (~₹48k/hr at DEL-0473) plus a claimable
warranty recovery; systemic across the batch (see the Fleet agent).

**Confirm via telemetry.** VSWR / return-loss trend, PIM test history, alarm-rate per site.

**Rule out.** loose connector torque, water ingress without salt, weathering discolouration.
