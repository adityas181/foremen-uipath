import type { AgentId, AgentRun, CaseEvent, CaseView, Scenario, Skill } from '../types'

export function initAgents(): Record<AgentId, AgentRun> {
  const ids: AgentId[] = ['supervisor', 'vision', 'entitlement', 'sla', 'rootcause', 'fleet']
  return Object.fromEntries(ids.map((id) => [id, { id, status: 'idle' }])) as Record<
    AgentId,
    AgentRun
  >
}

export function emptyCase(s: Scenario): CaseView {
  return {
    case_id: s.case_id,
    site_id: '',
    title: s.title,
    worker_phone: '',
    worker_name: '',
    stage: 'intake',
    status: 'open',
    reachedStages: ['intake'],
    risk_score: null,
    opened_at: '',
    scenario: s.id,
    media: [],
    agents: initAgents(),
    crewAssembled: false,
    chat: [],
    tasks: [],
    call: { status: 'idle', lines: [] },
    artifacts: [],
    log: [],
  }
}

// A blank case for the LIVE feed (not tied to a scripted scenario). The first
// `case.opened` event from the agent/backend fills in the real fields.
export function blankCase(caseId: string): CaseView {
  return {
    case_id: caseId,
    site_id: '',
    title: caseId,
    worker_phone: '',
    worker_name: '',
    stage: 'intake',
    status: 'open',
    reachedStages: ['intake'],
    risk_score: null,
    opened_at: '',
    scenario: 'A',
    media: [],
    agents: initAgents(),
    crewAssembled: false,
    chat: [],
    tasks: [],
    call: { status: 'idle', lines: [] },
    artifacts: [],
    log: [],
  }
}

// Pure-ish reducer: returns a NEW CaseView with the event applied.
// Skill events also mutate the passed-in `skills` map (handled by the caller).
export function reduceCase(prev: CaseView, ev: CaseEvent, atMs: number): CaseView {
  const c: CaseView = { ...prev }

  switch (ev.kind) {
    case 'case.opened':
      Object.assign(c, ev.case)
      c.reachedStages = ['intake']
      break

    case 'stage.entered':
      c.stage = ev.stage
      c.reachedStages = c.reachedStages.includes(ev.stage)
        ? c.reachedStages
        : [...c.reachedStages, ev.stage]
      if (ev.stage === 'resolve') c.status = 'resolved'
      break

    case 'message':
      c.chat = [...c.chat, ev.message]
      break

    case 'media.received':
      c.media = ev.media
      break

    case 'perception.ready':
      c.perception = ev.perception
      c.asset_note = ev.asset_note
      break

    case 'skill.matched':
      c.skillHit = ev.hit
      break

    case 'agent.assembled':
      c.agents = { ...c.agents, [ev.agent]: { ...c.agents[ev.agent], status: 'assembled' } }
      c.crewAssembled = true
      break

    case 'agent.running':
      c.agents = {
        ...c.agents,
        [ev.agent]: { ...c.agents[ev.agent], status: 'running', startedAt: atMs },
      }
      break

    case 'agent.completed':
      c.agents = {
        ...c.agents,
        [ev.agent]: {
          ...c.agents[ev.agent],
          ...ev.run,
          status: 'done',
          finishedAt: atMs,
        },
      }
      break

    case 'task.raised':
      c.tasks = [...c.tasks, ev.task]
      c.status = 'parked'
      break

    case 'task.answered':
      c.tasks = c.tasks.map((t) =>
        t.id === ev.taskId ? { ...t, status: 'answered', answer: ev.answer, answeredBy: ev.by } : t,
      )
      c.status = 'open'
      break

    case 'risk.scored':
      c.risk_score = ev.risk
      break

    case 'investigation.ready':
      c.investigation = ev.investigation
      break

    case 'fleet.ready':
      c.fleet = ev.fleet
      break

    case 'call.started':
      c.call = { status: 'dialing', to: ev.to, toRole: ev.toRole, lines: [] }
      break

    case 'call.connected':
      c.call = { ...c.call, status: 'connected' }
      break

    case 'call.line':
      c.call = { ...c.call, lines: [...c.call.lines, ev.line] }
      break

    case 'call.decision':
      c.call = { ...c.call, status: 'ended', decision: ev.decision }
      break

    case 'call.recording':
      c.call = { ...c.call, audioUrl: ev.url, audioDuration: ev.duration }
      break

    case 'action.produced':
      c.artifacts = [...c.artifacts, ev.artifact]
      break

    case 'audit.ready':
      c.audit = ev.audit
      break

    case 'graph.updated':
      c.graphNote = ev.note
      break

    case 'skill.written':
      c.skillWritten = ev.skill
      break

    case 'feedback':
      c.feedback = ev.verdict
      break

    case 'case.closed':
      c.status = 'closed'
      break

    case 'skill.promoted':
    case 'log':
      // handled at store level (skills map) / via step.log
      break
  }

  return c
}

export function applySkillEvent(
  skills: Record<string, Skill>,
  ev: CaseEvent,
): Record<string, Skill> {
  if (ev.kind === 'skill.written') {
    return { ...skills, [ev.skill.id]: ev.skill }
  }
  if (ev.kind === 'skill.promoted') {
    const existing = skills[ev.skillId]
    if (!existing) return skills
    return {
      ...skills,
      [ev.skillId]: { ...existing, status: ev.status, approve_count: ev.approve_count },
    }
  }
  return skills
}
