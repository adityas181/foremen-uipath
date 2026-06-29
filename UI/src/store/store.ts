import { create } from 'zustand'
import type { CaseEvent, CaseView, LogEntry, Skill } from '../types'
import { applySkillEvent, blankCase, reduceCase } from './reducer'

let logSeq = 0
function makeLog(entry: Omit<LogEntry, 'id'>): LogEntry {
  logSeq += 1
  return { ...entry, id: `log-${logSeq}` }
}

interface ForemanState {
  cases: Record<string, CaseView>
  order: string[]
  activeCaseId: string | null
  skills: Record<string, Skill>

  // actions
  selectCase: (caseId: string) => void
  resetAll: () => void
  // LIVE feed seam: apply one CaseEvent pushed from the view-backend over WebSocket.
  ingestEvent: (caseId: string, event: CaseEvent) => void
  // Human-in-the-loop: the thumbs-up/down at the learning gate. Records the
  // verdict; the real learning events (graph + skill) stream from the agent.
  submitFeedback: (verdict: 'up' | 'down') => void
}

function activeCase(get: () => ForemanState): CaseView | null {
  const { activeCaseId, cases } = get()
  return activeCaseId ? cases[activeCaseId] ?? null : null
}

export const useStore = create<ForemanState>((set, get) => ({
  cases: {},
  order: [],
  activeCaseId: null,
  skills: {},

  selectCase: (caseId) => set({ activeCaseId: caseId }),

  resetAll: () => set({ cases: {}, order: [], activeCaseId: null, skills: {} }),

  // Record the human verdict on the active case. The downstream learning
  // (graph.updated / skill.written / promoted) streams in live from the agent.
  submitFeedback: (verdict) => {
    const s = get()
    const caseId = s.activeCaseId
    if (!caseId) return
    const cur = s.cases[caseId]
    if (!cur || cur.feedback) return // already decided
    set((st) => {
      const c0 = st.cases[caseId]
      if (!c0) return {}
      const caseObj = reduceCase(c0, { kind: 'feedback', verdict }, performance.now())
      return { cases: { ...st.cases, [caseId]: caseObj } }
    })
  },

  // LIVE: apply a single CaseEvent pushed from the backend. Creates the case on
  // first sight, appends explicit log events, and keeps the skills map in sync.
  ingestEvent: (caseId, event) =>
    set((s) => {
      let cases = s.cases
      let order = s.order
      if (!cases[caseId]) {
        cases = { ...cases, [caseId]: blankCase(caseId) }
        order = order.includes(caseId) ? order : [...order, caseId]
      }
      let caseObj = reduceCase(cases[caseId], event, performance.now())
      if (event.kind === 'log') {
        caseObj = { ...caseObj, log: [...caseObj.log, makeLog({ ...event.entry })] }
      }
      const skills = applySkillEvent(s.skills, event)
      return {
        cases: { ...cases, [caseId]: caseObj },
        order,
        skills,
        activeCaseId: s.activeCaseId ?? caseId,
      }
    }),
}))

// ── Selectors / hooks ───────────────────────────────────────────────────────
export function useActiveCase(): CaseView | null {
  return useStore((s) => (s.activeCaseId ? s.cases[s.activeCaseId] ?? null : null))
}
export { activeCase }
