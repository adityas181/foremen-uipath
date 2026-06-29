// The FOREMAN crew — mirrors crew/crew-registry.json (v2.1).
// EVERY case runs the always-on Diagnosis & Recommendation Engine (the brain).
// The Supervisor then assembles ONLY the dynamic specialists the findings call
// for — and can justify why it skipped the rest. That selectivity is the signal.

export interface CrewAgent {
  id: string
  name: string
  short: string // label for the orchestration diagram
  kind: 'coded' | 'low-code'
  tagline: string
  reads: string
  horizontal?: string
  safety?: boolean
}

export const SUPERVISOR: CrewAgent = {
  id: 'supervisor',
  name: 'Supervisor',
  short: 'Supervisor',
  kind: 'coded',
  tagline: 'The orchestrator — assembles the crew per case, runs them in parallel, merges one cited recommendation, runs the two human gates.',
  reads: 'All specialists · all four stores',
}

export const VISION: CrewAgent = {
  id: 'vision',
  name: 'Vision',
  short: 'Vision',
  kind: 'coded',
  tagline: 'One multimodal call reads image, sound and thermal together → findings as strict JSON.',
  reads: 'Vision model · media',
}

export const ALWAYS_ON: CrewAgent = {
  id: 'diagnosis_recommendation_engine',
  name: 'Diagnosis & Recommendation Engine',
  short: 'Brain',
  kind: 'coded',
  tagline:
    'The brain — runs on every case. Matches a learned Skill on the hard gate, cites the reference manuals, reads the asset master record, recalls memory, reasons to a root cause, and emits the cited fix. On close it writes the Skill back.',
  reads: 'Skills · Reference docs · Data Fabric · Memory · Neo4j',
}

export const SPECIALISTS: CrewAgent[] = [
  { id: 'fleet_blast_radius', name: 'Fleet & Blast-Radius', short: 'Fleet', kind: 'coded', tagline: 'Who else shares a failing factor — batch, vendor, firmware, feeder, cooling loop or install crew.', reads: 'Neo4j', horizontal: 'cable batch · connector lot · resin lot · transformer feeder' },
  { id: 'warranty_entitlement', name: 'Warranty & Entitlement', short: 'Warranty', kind: 'low-code', tagline: 'Is this a claimable vendor / batch / spec defect inside a warranty window?', reads: 'Data Fabric · Warranty, Batch, Vendor', horizontal: 'cable spec defect · OEM defect · supplier defect' },
  { id: 'sla_commercial_impact', name: 'SLA & Commercial Impact', short: 'SLA', kind: 'coded', tagline: 'Exposure per hour across tenants / customers — could the money change the action?', reads: 'Data Fabric · Contracts, Tenant', horizontal: 'tower tenants · solar PPA · line output · occupants' },
  { id: 'safety_compliance', name: 'Safety & Compliance', short: 'Safety', kind: 'coded', tagline: 'Hazard codes & protocols — can BLOCK auto-resolve and force the human gate.', reads: 'Codes & standards', horizontal: 'PV DC arc · lift EN 81 · rail hot-box · HV', safety: true },
  { id: 'parts_logistics', name: 'Parts & Logistics', short: 'Parts', kind: 'low-code', tagline: 'Is the replacement part in stock, where, and what is the lead time?', reads: 'Data Fabric · Inventory, Spares', horizontal: 'matched MC4 pair · NRV kit · bushing · bearing' },
  { id: 'field_dispatch', name: 'Field Dispatch & Scheduling', short: 'Dispatch', kind: 'coded', tagline: 'Find the certified crew, check the certification, route them, ETA.', reads: 'Data Fabric · Crew, Roster · Maps', horizontal: 'rigger · certified PV tech · lift inspector' },
  { id: 'telemetry_predictive', name: 'Telemetry & Predictive', short: 'Telemetry', kind: 'coded', tagline: 'Trend the sensor — fix-now vs schedule — for incipient, degrading faults.', reads: 'IoT telemetry · Data Fabric', horizontal: 'VSWR / PIM · IR thermal · vibration SPC · DGA' },
  { id: 'vendor_supply_chain', name: 'Vendor & Supply-Chain', short: 'Vendor', kind: 'low-code', tagline: 'Known defect / recall / counterfeit? RMA path and approved replacement source.', reads: 'Data Fabric · Vendor, Batch · Recall feed', horizontal: 'batch recall · counterfeit lot · OEM bulletin' },
  { id: 'site_access_weather', name: 'Site Access & Weather', short: 'Access', kind: 'coded', tagline: 'Safe outdoor / at-height window — weather and access constraints.', reads: 'Weather API · Data Fabric · Site', horizontal: 'solar daylight · tower wind · track possession' },
  { id: 'cost_optimization', name: 'Cost Optimization', short: 'Cost', kind: 'coded', tagline: 'A genuine repair-vs-replace-vs-upgrade trade-off — whole-life cost.', reads: 'Data Fabric · Asset, Cost', horizontal: 'rebuild vs replace spindle · repair vs replace transformer' },
]

export interface Invocation {
  id: string
  why: string
}

// The MC4 case (the live demo): 5 invoked, 5 skipped — each with the argument.
export const MC4_INVOKED: Invocation[] = [
  { id: 'safety_compliance', why: 'DC arc + fire is safety-critical (NEC 690.11). Isolate under LOTO; this BLOCKS auto-resolve — the human gate is mandatory. The non-negotiable one.' },
  { id: 'fleet_blast_radius', why: 'A poor-crimp / cross-mating root cause is a SYSTEMIC install defect, not a one-off. Audit the same installer’s other strings — one finding can mean dozens of latent fire risks.' },
  { id: 'parts_logistics', why: 'The fix needs a matched genuine MC4 pair + the correct crimp die. Confirm stock and lead time before a truck rolls.' },
  { id: 'field_dispatch', why: 'Physical re-termination is required, by a CERTIFIED PV technician — DC arc work is not for any hand.' },
  { id: 'site_access_weather', why: 'Outdoor DC work needs a DRY weather window and daylight — schedule into a safe window, not into rain.' },
]

export const MC4_SKIPPED: Invocation[] = [
  { id: 'warranty_entitlement', why: 'The visible frayed copper at the crimp is FIELD WORKMANSHIP, not a vendor spec defect — there is no claimable warranty path. (Contrast the RF case, where a non-marine SPEC defect WAS claimable.)' },
  { id: 'vendor_supply_chain', why: 'No confirmed supplier defect or recall — workmanship is the lead cause. Held for re-engagement only if the Fleet audit proves systemic cross-mating (a procurement substitution).' },
  { id: 'sla_commercial_impact', why: 'A single PV string is a small, bounded loss — and the action is already MANDATED by safety. A commercial number cannot change a fire-risk decision, so computing one is wasted effort.' },
  { id: 'telemetry_predictive', why: 'The connector has already HARD-FAILED — melted, live now. Nothing incipient to trend, and the string-current signal is already lost. The decision is immediate.' },
  { id: 'cost_optimization', why: 'No repair-vs-replace trade-off — a charred connector is always cut out and replaced. Safety-optimal and cost-optimal are identical, so there is nothing to optimise.' },
]

// Per-scenario invocation. C (MC4) is fully argued; A/B reuse the registry's
// example crews (no per-agent essay needed for the secondary demos).
const RF_INVOKED = ['warranty_entitlement', 'fleet_blast_radius', 'sla_commercial_impact']

export function invocationFor(scenario: 'A' | 'B' | 'C'): {
  invoked: Invocation[]
  skipped: Invocation[]
} {
  if (scenario === 'C') return { invoked: MC4_INVOKED, skipped: MC4_SKIPPED }
  const invokedIds = scenario === 'A' || scenario === 'B' ? RF_INVOKED : []
  const invoked = SPECIALISTS.filter((s) => invokedIds.includes(s.id)).map((s) => ({ id: s.id, why: '' }))
  const skipped = SPECIALISTS.filter((s) => !invokedIds.includes(s.id)).map((s) => ({ id: s.id, why: '' }))
  return { invoked, skipped }
}
