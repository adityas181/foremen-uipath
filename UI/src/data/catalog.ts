import type { AgentDef, AgentId } from '../types'

export const AGENTS: AgentDef[] = [
  {
    id: 'supervisor',
    name: 'Supervisor',
    kind: 'coded',
    role: 'Case manager — orchestrates the crew, merges the recommendation, runs the two human gates',
    reads: 'Specialists + all four stores',
    hue: 'sky',
  },
  {
    id: 'vision',
    name: 'Vision',
    kind: 'coded',
    role: 'One multimodal call reads the image, sound and thermal together → findings as strict JSON',
    reads: 'Vision model · media URLs',
    hue: 'lilac',
  },
  {
    id: 'entitlement',
    name: 'Entitlement',
    kind: 'low-code',
    role: 'Rule: vendor_liable = recurred-in-window AND warranty active',
    reads: 'Data Fabric · Asset, Warranty',
    hue: 'mint',
  },
  {
    id: 'sla',
    name: 'Impact / Risk',
    kind: 'coded',
    role: 'Crew ETA from traffic, then penalty/hr × stakeholders × hours (or generation lost) = exposure',
    reads: 'Data Fabric · contracts + traffic API',
    hue: 'amber',
  },
  {
    id: 'rootcause',
    name: 'Root-cause',
    kind: 'coded',
    role: 'Weighs evidence to a cause, pulls manuals & anti-patterns, checks memory, asks the graph',
    reads: 'Context Grounding · Memory · Neo4j',
    hue: 'rose',
  },
  {
    id: 'fleet',
    name: 'Fleet',
    kind: 'coded',
    role: 'Multi-factor blast-radius + common-cause Cypher: every unit sharing a failing factor (batch, crew or part lot)',
    reads: 'Neo4j',
    hue: 'periwinkle',
  },
]

export const AGENT_BY_ID: Record<AgentId, AgentDef> = Object.fromEntries(
  AGENTS.map((a) => [a.id, a]),
) as Record<AgentId, AgentDef>

// The crew that runs in parallel during Investigate (Supervisor + Vision act earlier).
export const CREW: AgentId[] = ['entitlement', 'sla', 'rootcause', 'fleet']
