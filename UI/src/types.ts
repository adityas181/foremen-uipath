// ─────────────────────────────────────────────────────────────────────────────
// FOREMAN — domain + normalized case-event model
//
// The event union below is the SAME shape the live view-backend will push over
// WebSocket (Orchestrator webhooks + Maestro instance polling, normalized). The
// replay engine emits these from a scripted timeline so the UI is identical
// whether it is driven by a recorded demo or a live Maestro case.
// ─────────────────────────────────────────────────────────────────────────────

export type StageId =
  | 'intake'
  | 'confirm'
  | 'perceive'
  | 'investigate'
  | 'escalate'
  | 'resolve'
  | 'close'

export const STAGES: { id: StageId; label: string; blurb: string }[] = [
  { id: 'intake', label: 'Intake', blurb: 'Any signal → trigger' },
  { id: 'confirm', label: 'Confirm', blurb: 'Completeness · Asset ID' },
  { id: 'perceive', label: 'Perceive', blurb: 'Multimodal vision' },
  { id: 'investigate', label: 'Investigate', blurb: 'Dynamic crew → SOP' },
  { id: 'escalate', label: 'Escalate', blurb: 'Action Center → call' },
  { id: 'resolve', label: 'Resolve', blurb: 'Guarded downstream writes' },
  { id: 'close', label: 'Close', blurb: 'Audit + learn' },
]

export type AgentId = 'supervisor' | 'vision' | 'entitlement' | 'sla' | 'rootcause' | 'fleet'

export type AgentStatus = 'idle' | 'assembled' | 'running' | 'done'

export type PastelHue =
  | 'sky'
  | 'lilac'
  | 'mint'
  | 'amber'
  | 'rose'
  | 'periwinkle'
  | 'pink'
  | 'lemon'

export interface AgentDef {
  id: AgentId
  name: string
  kind: 'coded' | 'low-code'
  role: string
  reads: string
  hue: PastelHue
}

export interface AgentRun {
  id: AgentId
  status: AgentStatus
  headline?: string
  detail?: string
  confidence?: number
  citations?: string[]
  startedAt?: number
  finishedAt?: number
}

// ── Data Fabric entities (mock system of record) ────────────────────────────
export interface Site {
  site_id: string
  cluster: string
  environment: 'coastal' | 'dry' | string
  humidity: number
  tenants: number
}
export interface Asset {
  asset_id: string
  type: string
  installed: string
  vendor: string
  batch: string
  spec: string
}
export interface Warranty {
  warranty_id: string
  asset_id: string
  window: string
  status: 'active' | 'expired'
  liable: string
}
export interface ServiceContract {
  tenant: string
  contract: string
  penalty_per_hr: number
  response_sla_min: number
}
export interface Batch {
  batch_id: string
  vendor: string
  spec: string
  status: 'failing' | 'healthy'
}
export interface Vendor {
  vendor: string
  contact: string
  escalation_role: string
  escalation_phone: string
}

export interface MatchKey {
  equipment_class: string
  component: string
  environment: string
  spec: string
  capacity_band?: string
  failure_mode?: string
}

export type SkillStatus = 'none' | 'candidate' | 'trusted' | 'retired'

export interface Skill {
  id: string
  match_key: MatchKey
  diagnosis: string
  recipe: string[]
  status: SkillStatus
  approve_count: number
  source_cases: string[]
  citations: string[]
}

// ── Output artifacts ────────────────────────────────────────────────────────
export type ArtifactType = 'ticket' | 'work_order' | 'warranty_claim' | 'fleet_case' | 'noc'

export interface Artifact {
  type: ArtifactType
  id: string
  title: string
  guard?: string
  fields: Record<string, string | number>
  external?: boolean // a real external write (ServiceNow PDI)
}

// ── Media (what the field engineer sends — rendered on the MediaBoard) ───────
export type MediaKind = 'video' | 'image' | 'audio' | 'document'
export interface MediaItem {
  kind: MediaKind
  label: string
  thumb?: string
  duration?: string // '0:24' — audio/video
  meta?: string // 'MP4 · 12.4 MB' | '3 pages'
  note?: string // what it shows / a one-line caption
}

// ── Chat (WhatsApp) ─────────────────────────────────────────────────────────
export interface ChatMessage {
  id: string
  from: 'worker' | 'foreman'
  text: string
  ts: string
  media?: MediaItem[]
  options?: string[]
}

// ── Action Center task ──────────────────────────────────────────────────────
export interface HumanTask {
  id: string
  kind: 'confirm' | 'approve_call'
  prompt: string
  options?: string[]
  status: 'pending' | 'answered'
  answer?: string
  answeredBy?: string
}

// ── Voice call ──────────────────────────────────────────────────────────────
export interface CallLine {
  speaker: 'foreman' | 'manager'
  text: string
}
export interface CallState {
  status: 'idle' | 'dialing' | 'connected' | 'ended'
  to?: string
  toRole?: string
  lines: CallLine[]
  decision?: { authorized: boolean; actions: string[]; by: string; at: string }
  audioUrl?: string // pre-signed URL to the real Twilio call recording (mp3)
  audioDuration?: number // recording length in seconds (optional)
}

// ── Neo4j fleet graph ───────────────────────────────────────────────────────
// The node/edge vocabulary is horizontal: an Asset propagates a fault through any
// shared factor — batch, vendor, install crew, part/connector lot, site, cluster.
export type FleetNodeType =
  | 'site'
  | 'batch'
  | 'vendor'
  | 'cluster'
  | 'crew'
  | 'part_lot'
  | 'asset'
  | 'region'
  | 'equipment_class'

export interface FleetNode {
  id: string
  label: string
  type: FleetNodeType
  status?: 'corroded' | 'healthy' | 'failing' | 'at_risk'
  x: number
  y: number
  hub?: boolean // the culprit factor the blast-radius converges on
}
export interface FleetEdge {
  from: string
  to: string
  rel: string
  hot?: boolean // part of the failing propagation path (animated)
}

// A shared upstream factor — used by both common-cause (count = failures it
// explains) and criticality (count = assets that depend on it).
export interface FleetFactor {
  factor: string
  factorType: string
  via?: string
  count: number
  note?: string
}

// The full blast-radius payload. systemic/affected/nodes/edges are the v1 core;
// everything below is optional enrichment so older scenarios + live payloads that
// only send the core stay valid.
export interface FleetView {
  systemic: boolean
  affected: string[]
  nodes: FleetNode[]
  edges: FleetEdge[]
  unitNoun?: string // 'site' | 'string' | 'unit' — keeps copy horizontal
  rootCause?: FleetFactor[] // common-cause: the shared root, ranked
  criticality?: FleetFactor[] // degree centrality: biggest single-points-of-failure
  sqlVsGraph?: { sqlFound: number; sqlNote: string; graphFound: number; graphNote: string }
  queryTitle?: string
  query?: string // the actual Cypher, supplied by the case (never hardcoded in the view)
  exposurePerHr?: number
  exposureLabel?: string
}

// ── Perception (Vision output) ──────────────────────────────────────────────
// Horizontal: the vision/audio model emits a list of findings. `corrosion` and
// `generator_audio` are kept optional only so the original telecom scenarios stay
// valid — new domains (solar, IMM, HVAC…) just emit `findings`.
export interface PerceptionFinding {
  modality: 'image' | 'audio' | 'thermal' | 'text'
  label: string
  detail?: string
  severity?: string
  confidence?: number
}
export interface Perception {
  findings?: PerceptionFinding[]
  issues: string[]
  corrosion?: { present: boolean; severity: string }
  generator_audio?: { anomaly: string; confidence: number }
}

export interface Investigation {
  root_cause: string
  confidence: number
  alternatives_ruled_out: string[]
  systemic: boolean
  fleet_affected: number
  risk_score: number
  recommendation: string
  exposure_per_hr?: number
  eta_min?: number
}

// ── Activity log entry ──────────────────────────────────────────────────────
export interface LogEntry {
  id: string
  ts: string
  stage: StageId
  source: string
  text: string
  tone?: 'info' | 'ok' | 'warn' | 'danger' | 'human' | 'agent'
}

// ── The case (the shared bag, grown by events) ──────────────────────────────
export interface CaseView {
  case_id: string
  site_id: string
  title: string
  worker_phone: string
  worker_name: string
  stage: StageId
  status: 'open' | 'parked' | 'resolved' | 'closed'
  reachedStages: StageId[]
  risk_score: number | null
  opened_at: string
  scenario: 'A' | 'B' | 'C'

  media: MediaItem[]
  perception?: Perception
  asset_note?: string

  agents: Record<AgentId, AgentRun>
  crewAssembled: boolean

  chat: ChatMessage[]
  tasks: HumanTask[]
  call: CallState

  investigation?: Investigation
  artifacts: Artifact[]
  fleet?: FleetView

  skillHit?: { id: string; status: SkillStatus; source: string } | null
  skillWritten?: Skill
  graphNote?: string

  audit?: {
    email: { to: string; subject: string; body: string }
    attachments: string[]
  }
  feedback?: 'up' | 'down'

  log: LogEntry[]
}

// ── The normalized event union (what the feed emits) ────────────────────────
export type CaseEvent =
  | { kind: 'case.opened'; case: Partial<CaseView> }
  | { kind: 'stage.entered'; stage: StageId; note?: string }
  | { kind: 'message'; message: ChatMessage }
  | { kind: 'media.received'; media: CaseView['media'] }
  | { kind: 'perception.ready'; perception: Perception; asset_note: string }
  | { kind: 'skill.matched'; hit: { id: string; status: SkillStatus; source: string } | null }
  | { kind: 'agent.assembled'; agent: AgentId }
  | { kind: 'agent.running'; agent: AgentId }
  | { kind: 'agent.completed'; agent: AgentId; run: Partial<AgentRun> }
  | { kind: 'task.raised'; task: HumanTask }
  | { kind: 'task.answered'; taskId: string; answer: string; by?: string }
  | { kind: 'risk.scored'; risk: number }
  | { kind: 'investigation.ready'; investigation: Investigation }
  | { kind: 'fleet.ready'; fleet: NonNullable<CaseView['fleet']> }
  | { kind: 'call.started'; to: string; toRole: string }
  | { kind: 'call.connected' }
  | { kind: 'call.line'; line: CallLine }
  | { kind: 'call.decision'; decision: NonNullable<CallState['decision']> }
  | { kind: 'call.recording'; url: string; duration?: number }
  | { kind: 'action.produced'; artifact: Artifact }
  | { kind: 'audit.ready'; audit: NonNullable<CaseView['audit']> }
  | { kind: 'graph.updated'; note: string }
  | { kind: 'skill.written'; skill: Skill }
  | { kind: 'skill.promoted'; skillId: string; approve_count: number; status: SkillStatus }
  | { kind: 'feedback'; verdict: 'up' | 'down' }
  | { kind: 'case.closed' }
  | { kind: 'log'; entry: Omit<LogEntry, 'id'> }

// A scripted step: emit `event` `at` ms into the run, with an optional log line.
export interface TimelineStep {
  at: number
  event: CaseEvent
  log?: Omit<LogEntry, 'id' | 'ts'> & { ts?: string }
}

export interface Scenario {
  id: 'A' | 'B' | 'C'
  case_id: string
  title: string
  subtitle: string
  steps: TimelineStep[]
  durationMs: number
}
