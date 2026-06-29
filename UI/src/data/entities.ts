import type {
  Asset,
  Batch,
  ServiceContract,
  Site,
  Vendor,
  Warranty,
} from '../types'

// ── Data Fabric: the structured system of record (mock seed rows) ───────────

export const SITES: Site[] = [
  { site_id: 'DEL-0473', cluster: 'WEST-COAST', environment: 'coastal', humidity: 85, tenants: 3 },
  { site_id: 'MUM-0210', cluster: 'WEST-COAST', environment: 'coastal', humidity: 82, tenants: 3 },
  { site_id: 'BLR-0337', cluster: 'SOUTH-INLAND', environment: 'dry', humidity: 45, tenants: 2 },
]

export const ASSETS: Asset[] = [
  {
    asset_id: 'AST-RF-DEL-0473',
    type: 'rf_jumper_cable',
    installed: '2026-05-15',
    vendor: 'NorthGrid',
    batch: 'NG-BATCH-22',
    spec: 'non-marine',
  },
  {
    asset_id: 'AST-DG-DEL-0473',
    type: 'diesel_generator',
    installed: '2023-02-10',
    vendor: 'PowerCore',
    batch: '—',
    spec: 'standard',
  },
]

export const WARRANTIES: Warranty[] = [
  {
    warranty_id: 'WR-7781',
    asset_id: 'AST-RF-DEL-0473',
    window: '90 days',
    status: 'active',
    liable: 'per_warranty',
  },
]

export const SERVICE_CONTRACTS: ServiceContract[] = [
  { tenant: 'Airtel', contract: 'SLA-A', penalty_per_hr: 22000, response_sla_min: 60 },
  { tenant: 'Jio', contract: 'SLA-B', penalty_per_hr: 16000, response_sla_min: 60 },
  { tenant: 'Vodafone Idea', contract: 'SLA-C', penalty_per_hr: 10000, response_sla_min: 90 },
]

export const TOTAL_EXPOSURE_PER_HR = SERVICE_CONTRACTS.reduce(
  (s, c) => s + c.penalty_per_hr,
  0,
) // ≈ ₹48,000 / hr

export const BATCHES: Batch[] = [
  { batch_id: 'NG-BATCH-22', vendor: 'NorthGrid', spec: 'non-marine', status: 'failing' },
  { batch_id: 'NG-BATCH-30', vendor: 'NorthGrid', spec: 'marine-grade', status: 'healthy' },
]

export const VENDORS: Vendor[] = [
  {
    vendor: 'NorthGrid',
    contact: 'ops@northgrid.example',
    escalation_role: 'cluster_manager',
    escalation_phone: '+91-98xxxxxx',
  },
]

// ── Context Grounding: documents the agents cite (excerpts) ─────────────────
// Horizontal by design — the library spans asset classes; the agent retrieves
// whatever the case needs. (MC4 solar docs lead because that's the live demo.)
export const GROUNDING_DOCS: { file: string; line: string; tag: string }[] = [
  {
    file: 'mc4-connector-install-spec.pdf',
    line: 'IEC 62852 / UL 6703: never cross-mate MC4 brands. Mixed mating raises contact resistance; I²R heating drives thermal runaway and DC arcing.',
    tag: 'spec',
  },
  {
    file: 'pv-dc-arc-safety-bulletin.pdf',
    line: 'NEC 690.11 / 690.12: a melted connector is a DC-arc and fire hazard. Isolate the string DC-safe before any service.',
    tag: 'safety',
  },
  {
    file: 'connector-cross-mating-warning.pdf',
    line: 'Cross-mated joints recur by install crew and connector lot, not by module batch — audit the crew and requalify the part lot.',
    tag: 'anti-pattern',
  },
  {
    file: 'rf-cable-spec-NG-22.pdf',
    line: 'Non-marine PVC sheath: not for coastal/high-salinity sites; marine-grade advised above 80% humidity.',
    tag: 'spec',
  },
  {
    file: 'iso-20816-vibration.pdf',
    line: 'Rotating-plant vibration zones A–D: trend each unit against the fleet mean — do not threshold on a single reading.',
    tag: 'standard',
  },
  {
    file: 'anti-patterns.md',
    line: 'Do NOT assume a shared batch is the cause when a healthy unit shares it. Do NOT call discolouration a fault without pitting/deposits.',
    tag: 'anti-pattern',
  },
]

// ── The four stores (for the landing + dashboard "stores" rail) ─────────────
export const STORES = [
  {
    id: 'data_fabric',
    name: 'Data Fabric',
    holds: 'Asset · Site · Crew · Batch · Part-lot · Vendor · Warranty',
    agentsDo: 'read + write records',
    hue: 'mint' as const,
  },
  {
    id: 'context_grounding',
    name: 'Context Grounding',
    holds: 'Manuals · specs · SLA clauses · few-shot · anti-patterns · skill cards',
    agentsDo: 'ask + get cited answers',
    hue: 'amber' as const,
  },
  {
    id: 'agent_memory',
    name: 'Agent Memory',
    holds: 'Episodic past cases and human decisions / corrections',
    agentsDo: '“seen this before?”',
    hue: 'rose' as const,
  },
  {
    id: 'neo4j',
    name: 'Neo4j Graph',
    holds: 'The connection brain — blast-radius, common-cause, criticality',
    agentsDo: 'query with Cypher',
    hue: 'periwinkle' as const,
  },
]
