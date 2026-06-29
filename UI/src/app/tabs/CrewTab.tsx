import { motion } from 'framer-motion'
import { Bot, ChevronDown, MessageSquare, Send, Users, Zap } from 'lucide-react'
import { useStore } from '../../store/store'
import { clsx } from '../../lib/format'
import robosUrl from '../../assets/robos.png'
import { CREW_ICON as ICON } from '../../data/crewIcons'
import { ALWAYS_ON, SPECIALISTS, VISION, invocationFor, type CrewAgent } from '../../data/crew'

// ── Real deployed crew — the actual UiPath agent processes (Shared / foremen v1)
// agentName = the deployed Orchestrator process; team = its function; desc = what
// it does; contribution = what it added to this case. Card chrome only — no logic.
const CREW_CHROME: Record<
  string,
  { agentName: string; team: string; desc: string; skills: string[]; contribution: string }
> = {
  diagnosis_recommendation_engine: {
    agentName: 'Foreman-diagnosis-recommendation',
    team: 'Diagnosis & Recommendation',
    desc: 'The always-on brain — runs on every case. Matches a learned Skill on the hard gate, cites the reference manuals, reads the asset record, recalls memory and reasons to the root cause.',
    skills: ['Skill match', 'Citations', 'Root cause'],
    contribution: 'Returns the cited diagnosis + recommendation — root cause with confidence, the fix steps and the manual/skill citations; on close it writes the Skill back.',
  },
  safety_compliance: {
    agentName: 'Foreman-safety',
    team: 'Safety & Compliance',
    desc: 'Invoked when the equipment/failure is hazardous — arc/fire, fall, derailment, pressure, HV. Can block auto-resolve.',
    skills: ['Context Ground', 'Safety Gate', 'Citations'],
    contribution: 'Returns the safety verdict — safety-critical flag, ordered isolate/LOTO/de-energise steps, cited clauses, and the auto-resolve block.',
  },
  fleet_blast_radius: {
    agentName: 'Foreman-fleet-blast-radius',
    team: 'Fleet & Blast-Radius',
    desc: 'Invoked when the asset shares a failure-propagating link with others — same batch, vendor, firmware, feeder, cooling loop or install crew.',
    skills: ['Neo4j', 'Blast-radius', 'Criticality'],
    contribution: 'Traverses the Neo4j graph — flags whether the fault is systemic, lists the affected sibling strings, and ranks crew/lot/batch criticality.',
  },
  parts_logistics: {
    agentName: 'Foreman-parts',
    team: 'Parts & Logistics',
    desc: 'Invoked when the recommended fix needs a replacement part or consumable.',
    skills: ['Data Fabric', 'In-stock', 'Lead time'],
    contribution: 'Checks live Data Fabric inventory — returns in-stock, the nearest warehouse (DEL-warehouse), lead time and a genuine substitute.',
  },
  field_dispatch: {
    agentName: 'Foreman-field-dispatch',
    team: 'Field Dispatch & Scheduling',
    desc: 'Invoked when a physical repair, swap or inspection visit is required.',
    skills: ['Data Fabric', 'OSRM route', 'Cert match'],
    contribution: 'Picks the crew — returns the crew (CREW-PV-W), skill/cert match and an OSRM road route + ETA (27 min · 25.9 km).',
  },
  site_access_weather: {
    agentName: 'Foreman-Weather',
    team: 'Site Access & Weather',
    desc: 'Invoked when the fix is outdoor / at height / weather-sensitive, or site access is constrained.',
    skills: ['Weather MCP', 'Data Fabric', 'Safe-window'],
    contribution: 'Calls the Weather MCP — returns the earliest dry, daylit, lightning-free safe window plus any weather and access blockers.',
  },
  telemetry_predictive: {
    agentName: 'Foreman-Telemetry',
    team: 'Telemetry & Predictive',
    desc: 'Invoked when the fault is incipient/degrading and a sensor trend would decide fix-now vs schedule — not when the part has hard-failed.',
    skills: ['Anomaly score', 'Trend', 'RUL'],
    contribution: 'Returns the telemetry verdict — trend, anomaly score, remaining useful life, whether it corroborates vision, and fix-now vs schedule.',
  },
  warranty_entitlement: {
    agentName: 'Foreman-Entitlement',
    team: 'Warranty & Entitlement',
    desc: 'Invoked when the asset is in a warranty window AND the cause is a vendor/batch/spec defect (a claimable cost) — not for field-workmanship faults.',
    skills: ['Warranty', 'Claim basis', 'Liability'],
    contribution: 'Returns the entitlement verdict — warranty status, vendor liability, the claim basis and the recoverable amount.',
  },
  sla_commercial_impact: {
    agentName: 'Foreman-SLA',
    team: 'SLA & Commercial Impact',
    desc: 'Invoked when the asset/site serves multiple tenants or an SLA AND the commercial exposure could change the priority or action.',
    skills: ['Exposure / hr', 'Contracts', 'Priority'],
    contribution: 'Returns the commercial picture — exposure per hour across tenants, downtime cost, and any priority uplift.',
  },
  vendor_supply_chain: {
    agentName: 'Foreman-Vendor',
    team: 'Vendor & Supply-Chain',
    desc: 'Invoked when the root cause implicates a supplier — a batch/lot defect, recall, or counterfeit/substituted parts — not a one-off field workmanship fault.',
    skills: ['RMA / recall', 'Replacement', '8D escal.'],
    contribution: 'Checks the supplier — confirms a batch/connector defect, opens an RMA for credit, names the genuine source and files a supplier 8D.',
  },
  cost_optimization: {
    agentName: 'Foreman-Cost',
    team: 'Cost Optimization',
    desc: 'Invoked when there is a genuine repair-vs-replace-vs-upgrade trade-off — not when the fix is forced or trivial.',
    skills: ['Repair/Replace', 'Whole-life', 'CAPEX'],
    contribution: 'Returns the cost verdict — the repair-vs-replace decision, whole-life cost, a CAPEX flag and the rationale.',
  },
}

const FALLBACK_CHROME = {
  agentName: '',
  team: '',
  desc: '',
  skills: [] as string[],
  contribution: '',
}

const chromeFor = (id: string) => CREW_CHROME[id] ?? FALLBACK_CHROME

// Derive the REAL invoked specialists from the live "Crew dispatched: a, b, c"
// activity event (the supervisor emits the dispatched crew ids). Returns null
// until that event has streamed in, so the caller can fall back to the scenario.
function liveInvokedIds(log: { text: string }[]): Set<string> | null {
  for (let i = log.length - 1; i >= 0; i--) {
    const m = (log[i].text || '').match(/crew dispatched[:\-\s]+(.+)/i)
    if (m) {
      const found = new Set<string>()
      for (const s of SPECIALISTS) if (m[1].includes(s.id)) found.add(s.id)
      if (found.size > 0) return found
    }
  }
  return null
}

export function CrewTab() {
  const c = useStore((s) => (s.activeCaseId ? s.cases[s.activeCaseId] : null))
  const scenario = c?.scenario ?? 'C'
  // Real-time: derive the invoked crew from the live "Crew dispatched: …" event;
  // before it streams in, fall back to the scenario's default crew.
  const liveIds = liveInvokedIds(c?.log ?? [])
  const invokedIds = liveIds ?? new Set(invocationFor(scenario).invoked.map((i) => i.id))

  // Sequential dispatch timing — invoked agents are "called" one by one in order;
  // not-invoked settle in (greyed) after the calls finish. Shared by the
  // orchestration's strings + nodes so they fire in lockstep.
  const invokedOrder = SPECIALISTS.filter((s) => invokedIds.has(s.id))
  // Invoked specialists are "called" one at a time (DISPATCH_STEP apart). The
  // not-invoked bench appears AFTER the last call (a short gap later) so the
  // one-by-one cadence reads clearly instead of being masked by the bench.
  const lastCall = DISPATCH_BASE + Math.max(invokedOrder.length - 1, 0) * DISPATCH_STEP
  const benchStart = lastCall + 2
  const callDelayById = new Map<string, number>()
  invokedOrder.forEach((s, i) => callDelayById.set(s.id, DISPATCH_BASE + i * DISPATCH_STEP))
  let benchIdx = 0
  SPECIALISTS.forEach((s) => {
    if (!callDelayById.has(s.id)) {
      callDelayById.set(s.id, benchStart + benchIdx * 0.08)
      benchIdx++
    }
  })

  // Cards: the always-on Diagnosis & Recommendation Engine first (it runs every
  // case), then the invoked specialists in call order, then the greyed bench.
  // Each card's delay matches when its agent is "called" in the orchestration,
  // so the card pops in on the same beat the supervisor dials that agent.
  const cardList: { agent: CrewAgent; invoked: boolean; delay: number }[] = [
    { agent: ALWAYS_ON, invoked: true, delay: 0.45 },
    ...invokedOrder.map((s) => ({ agent: s, invoked: true, delay: (callDelayById.get(s.id) ?? 0) + 0.18 })),
    ...SPECIALISTS.filter((s) => !invokedIds.has(s.id)).map((s) => ({
      agent: s,
      invoked: false,
      delay: (callDelayById.get(s.id) ?? 0) + 0.18,
    })),
  ]

  return (
    <div className="space-y-7">
      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-5">
        <div className="max-w-2xl">
          <div className="inline-flex items-center rounded-md border border-ink-900/[0.08] bg-paper-50 px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-ink-500">
            The dynamic crew
          </div>
          <h1 className="mt-4 font-serif text-[31px] font-normal leading-[1.07] tracking-[-0.012em] text-ink-900 sm:text-[40px]">
            One orchestrator, a crew per case
          </h1>
          <p className="mt-3 max-w-xl text-[14px] leading-relaxed text-ink-500">
            Vision perceives; the brain diagnoses every case.
            <br className="hidden sm:block" /> The supervisor assembles the right specialists for the
            findings call.
          </p>
        </div>

        <div className="flex items-stretch gap-3">
          <HeroStat icon={<Users size={16} />} value={SPECIALISTS.length} label="Specialists" />
          <HeroStat icon={<Zap size={16} />} value={invokedIds.size} label="Invoked" />
        </div>
      </div>

      {/* ── Supervisor orchestration ───────────────────────────────────────── */}
      <Orchestration invokedIds={invokedIds} callDelayById={callDelayById} />

      {/* ── Specialists invoked for this case ──────────────────────────────── */}
      <div>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-[9px] bg-ink-900/[0.045] text-ink-500 ring-1 ring-inset ring-ink-900/[0.04]">
              <Users size={15} />
            </span>
            <h3 className="text-[14.5px] font-semibold tracking-tight text-ink-900">
              The specialist crew
            </h3>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-lg border border-ink-900/[0.12] bg-white px-3 py-1.5 text-[12px] font-medium text-ink-600">
              <span className="text-ink-400">View by</span>
              <span className="font-semibold text-ink-800">Role</span>
              <ChevronDown size={13} className="text-ink-400" />
            </span>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 text-[12px] font-medium text-ink-500 transition-colors hover:text-ink-900"
            >
              <Send size={12} className="-rotate-45" /> Expand all
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {cardList.map(({ agent, invoked, delay }) => (
            <SpecialistCard key={agent.id} agent={agent} invoked={invoked} delay={delay} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Hero KPI stat pill ───────────────────────────────────────────────────────
function HeroStat({ icon, value, label }: { icon: React.ReactNode; value: number; label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-ink-900/[0.08] bg-white px-5 py-3.5 shadow-card-soft">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink-900/[0.04] text-ink-500 ring-1 ring-inset ring-ink-900/[0.05]">
        {icon}
      </span>
      <div>
        <div className="font-display text-[22px] font-bold leading-none tracking-tightest text-ink-900">
          {value}
        </div>
        <div className="mt-1 text-[11px] font-medium text-ink-400">{label}</div>
      </div>
    </div>
  )
}

// ── The orchestration stage — the puppeteer robot conducting the crew ────────
const BRAND = '#2f6dff'
const AMBER = '#c77b08'
// Dispatch choreography — when the stage mounts the supervisor "calls" each
// invoked specialist one by one: its control string draws out from the robot's
// hand, the node pops in and a ring pings. Not-invoked agents settle in greyed
// once the calls have finished.
const DISPATCH_BASE = 12 // the FIRST agent is called only after this lead-in (seconds)
const DISPATCH_STEP = 13 // gap between consecutive agent calls (seconds)
const STRING_DRAW = 0.45 // how long a control string takes to draw out
// the robot "hands" the strings hang from (0–100 canvas)
const HAND_L = { x: 43.5, y: 33 }
const HAND_R = { x: 56.5, y: 33 }
const ROW_Y = 82

function Orchestration({
  invokedIds,
  callDelayById,
}: {
  invokedIds: Set<string>
  callDelayById: Map<string, number>
}) {
  const cols = SPECIALISTS.map((_, i) => 7 + i * (86 / (SPECIALISTS.length - 1)))

  return (
    <div className="panel overflow-hidden p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-[9px] bg-ink-900/[0.045] text-ink-500 ring-1 ring-inset ring-ink-900/[0.04]">
            <Bot size={15} />
          </span>
          <div>
            <h3 className="text-[14.5px] font-semibold leading-tight tracking-tight text-ink-900">
              Supervisor orchestration
            </h3>
            <p className="text-[11.5px] leading-tight text-ink-400">
              Assembled in real-time for this case
            </p>
          </div>
        </div>
        <span className="inline-flex items-center rounded-md border border-brand-400/30 bg-brand-500/[0.07] px-2.5 py-1 text-[10.5px] font-semibold text-brand-600">
          Assembled per case
        </span>
      </div>

      <div className="relative h-[440px] w-full overflow-hidden rounded-2xl border border-ink-900/[0.06] bg-gradient-to-b from-white via-paper-50 to-paper-100 sm:h-[460px]">
        {/* backdrop — dot grid, brand glow, a soft stage floor */}
        <div className="pointer-events-none absolute inset-0 bg-dots opacity-[0.45]" />
        <div className="pointer-events-none absolute left-1/2 top-[6%] h-[46%] w-[44%] -translate-x-1/2 rounded-full bg-brand-500/[0.07] blur-3xl" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-[34%] bg-gradient-to-t from-brand-500/[0.05] to-transparent" />

        {/* control strings (SVG) — drawn beneath the nodes. Percentage coords so
            the endpoints line up exactly with the nodes (which use left:%/top:%). */}
        <svg className="absolute inset-0 h-full w-full">
          {SPECIALISTS.map((s, i) => {
            const on = invokedIds.has(s.id)
            const hand = i < SPECIALISTS.length / 2 ? HAND_L : HAND_R
            const accent = on ? (s.safety ? AMBER : BRAND) : '#9aa1aa'
            const cd = callDelayById.get(s.id) ?? 0
            const X1 = `${hand.x}%`
            const Y1 = `${hand.y}%`
            const X2 = `${cols[i]}%`
            const Y2 = `${ROW_Y - 6}%`
            if (!on) {
              // not invoked — a faint static string that fades in with the bench, later
              return (
                <motion.line
                  key={s.id}
                  x1={X1} y1={Y1} x2={X2} y2={Y2}
                  stroke="#9aa1aa" strokeOpacity={0.16} strokeWidth={0.8}
                  strokeLinecap="round" strokeDasharray="2 3"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: cd, duration: 0.4 }}
                />
              )
            }
            return (
              <g key={s.id}>
                {/* glow halo — drawn out as the agent is called */}
                <motion.line
                  x1={X1} y1={Y1} x2={X2} y2={Y2}
                  stroke={accent} strokeOpacity={0.14} strokeWidth={4} strokeLinecap="round"
                  initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
                  transition={{ delay: cd, duration: STRING_DRAW, ease: 'easeOut' }}
                />
                {/* the control string — draws from the supervisor's hand to the agent */}
                <motion.line
                  x1={X1} y1={Y1} x2={X2} y2={Y2}
                  stroke={accent} strokeOpacity={0.55} strokeWidth={1.3} strokeLinecap="round"
                  initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
                  transition={{ delay: cd, duration: STRING_DRAW, ease: 'easeOut' }}
                />
                {/* live signal flowing down the string — only after it's drawn */}
                <motion.line
                  x1={X1} y1={Y1} x2={X2} y2={Y2}
                  stroke={accent} strokeOpacity={0.95} strokeWidth={1.6}
                  strokeLinecap="round" strokeDasharray="0.5 7"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: cd + STRING_DRAW, duration: 0.3 }}
                >
                  <animate attributeName="stroke-dashoffset" from="0" to="-30"
                           dur={`${1.3 + (i % 4) * 0.22}s`} repeatCount="indefinite" />
                </motion.line>
              </g>
            )
          })}

          {/* always-on links — the supervisor's perception (Vision) + brain
              (Diagnosis & Recommendation); drawn first, since they run every case */}
          {[
            { id: VISION.id, hand: HAND_L, cx: 13, accent: '#7b828c' },
            { id: ALWAYS_ON.id, hand: HAND_R, cx: 87, accent: BRAND },
          ].map((core) => (
            <g key={`core-${core.id}`}>
              <motion.line
                x1={`${core.hand.x}%`} y1={`${core.hand.y}%`} x2={`${core.cx}%`} y2="26%"
                stroke={core.accent} strokeOpacity={0.45} strokeWidth={1.2} strokeLinecap="round"
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
                transition={{ delay: 0.4, duration: STRING_DRAW, ease: 'easeOut' }}
              />
              <motion.line
                x1={`${core.hand.x}%`} y1={`${core.hand.y}%`} x2={`${core.cx}%`} y2="26%"
                stroke={core.accent} strokeOpacity={0.9} strokeWidth={1.4}
                strokeLinecap="round" strokeDasharray="0.5 7"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                transition={{ delay: 0.4 + STRING_DRAW, duration: 0.3 }}
              >
                <animate attributeName="stroke-dashoffset" from="0" to="-30" dur="1.6s" repeatCount="indefinite" />
              </motion.line>
            </g>
          ))}
        </svg>

        {/* the puppeteer robot — the Supervisor.
            Outer div owns the horizontal centering so framer-motion's animated
            transform (the y bob) can't clobber the -translate-x-1/2. */}
        <div className="pointer-events-none absolute left-1/2 top-[1%] z-20 -translate-x-1/2">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: [0, -7, 0] }}
            transition={{ opacity: { duration: 0.6 }, y: { duration: 6, repeat: Infinity, ease: 'easeInOut' } }}
            className="relative"
          >
            {/* white halo blends the image's white background into the stage */}
            <div className="absolute left-1/2 top-1/2 h-[150%] w-[150%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/90 blur-2xl" />
            <img
              src={robosUrl}
              alt="Supervisor orchestrating the crew"
              className="relative w-[clamp(220px,30vw,300px)]"
              style={{
                WebkitMaskImage: 'linear-gradient(to bottom, #000 0%, #000 56%, transparent 80%)',
                maskImage: 'linear-gradient(to bottom, #000 0%, #000 56%, transparent 80%)',
              }}
            />
            <div className="absolute -bottom-1 left-1/2 h-3 w-40 -translate-x-1/2 rounded-[100%] bg-ink-900/10 blur-md" />
          </motion.div>
        </div>

        {/* Supervisor label */}
        <div className="absolute left-1/2 top-[32%] z-20 -translate-x-1/2 whitespace-nowrap rounded-md border border-ink-900/[0.10] bg-white/95 px-3 py-1 text-[10px] font-semibold text-ink-700 shadow-sm backdrop-blur-sm">
          Supervisor Orchestrator
        </div>

        {/* always-on core: Vision + Brain flanking */}
        <CoreNode agent={VISION} x={13} y={22} />
        <CoreNode agent={ALWAYS_ON} x={87} y={22} brain label="Diagnosis & Recommendation" />

        {/* specialist crew — invoked agents are called into their slots one at a
            time (DISPATCH_STEP apart); the not-invoked bench follows after */}
        {SPECIALISTS.map((s, i) => (
          <SpecNode
            key={s.id}
            agent={s}
            x={cols[i]}
            y={ROW_Y}
            invoked={invokedIds.has(s.id)}
            callDelay={callDelayById.get(s.id) ?? 0}
          />
        ))}

        {/* dispatch call-packets — a glowing signal travels down each invoked
            string from the supervisor's hand to the agent as it is called */}
        {SPECIALISTS.map((s, i) => {
          if (!invokedIds.has(s.id)) return null
          const hand = i < SPECIALISTS.length / 2 ? HAND_L : HAND_R
          const accent = s.safety ? AMBER : BRAND
          const cd = callDelayById.get(s.id) ?? 0
          return (
            <motion.span
              key={`pkt-${s.id}`}
              className="pointer-events-none absolute z-[15] h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
              style={{ background: accent, boxShadow: `0 0 10px 1px ${accent}` }}
              initial={{ left: `${hand.x}%`, top: `${hand.y}%`, opacity: 0, scale: 0.5 }}
              animate={{
                left: `${cols[i]}%`,
                top: `${ROW_Y - 6}%`,
                opacity: [0, 1, 1, 0],
                scale: [0.5, 1, 1, 0.7],
              }}
              transition={{ delay: cd, duration: STRING_DRAW + 0.1, ease: 'easeIn', times: [0, 0.15, 0.8, 1] }}
            />
          )
        })}
      </div>
    </div>
  )
}

function CoreNode({
  agent,
  x,
  y,
  brain,
  label,
}: {
  agent: CrewAgent
  x: number
  y: number
  brain?: boolean
  label?: string
}) {
  const Icon = ICON[agent.id] ?? Bot
  const accent = brain ? BRAND : '#5b626c'
  // Outer div centers (plain CSS); the inner motion.div animates so the entrance
  // + always-on heartbeat can't clobber the -translate centering.
  return (
    <div
      className="absolute z-20 -translate-x-1/2 -translate-y-1/2"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.35, type: 'spring', stiffness: 240, damping: 18 }}
        className="flex items-center gap-2.5 rounded-2xl border border-ink-900/[0.08] bg-white/95 px-3 py-2 shadow-card-soft backdrop-blur-sm"
      >
        <span
          className="relative flex h-9 w-9 items-center justify-center rounded-xl border"
          style={{
            borderColor: brain ? `${BRAND}44` : '#14171c1f',
            background: brain ? `${BRAND}0f` : '#ffffff',
            color: brain ? BRAND : '#5b626c',
          }}
        >
          {/* always-on heartbeat — this agent runs on every case */}
          <motion.span
            className="absolute inset-0 rounded-xl"
            animate={{ opacity: [0, 0.4, 0], scale: [0.9, 1.5, 1.7] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: 'easeOut', delay: 0.8 }}
            style={{ boxShadow: `0 0 0 1.5px ${accent}` }}
          />
          <Icon size={17} strokeWidth={2} />
        </span>
        <div className="max-w-[124px] leading-tight">
          <div className="text-[12px] font-semibold leading-tight text-ink-800">{label ?? agent.short}</div>
          <div className="text-[10px] font-medium text-ink-400">Always on</div>
        </div>
      </motion.div>
    </div>
  )
}

function SpecNode({
  agent,
  x,
  y,
  invoked,
  callDelay,
}: {
  agent: CrewAgent
  x: number
  y: number
  invoked: boolean
  callDelay: number
}) {
  const Icon = ICON[agent.id] ?? Bot
  const accent = invoked ? (agent.safety ? AMBER : BRAND) : '#9aa1aa'
  // Invoked nodes pop in just as their string reaches them; not-invoked settle in.
  const appear = invoked ? callDelay + 0.18 : callDelay
  // Outer div owns left/top + centering (plain CSS) so framer-motion's animated
  // transform on the inner card can't clobber the -translate-x/y centering —
  // that's what makes each node land exactly on its control string.
  return (
    <div
      className="absolute z-10 w-[9%] min-w-[72px] -translate-x-1/2 -translate-y-1/2"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.5, y: 8 }}
        animate={{ opacity: invoked ? 1 : 0.55, scale: 1, y: 0 }}
        transition={{ delay: appear, type: 'spring', stiffness: 240, damping: 18 }}
        className="flex w-full flex-col items-center rounded-xl border bg-white/95 px-1.5 py-2 text-center shadow-card-soft backdrop-blur-sm"
        style={{ borderColor: invoked ? `${accent}55` : '#e2e4e7' }}
      >
        <span
          className="relative flex h-8 w-8 items-center justify-center rounded-lg border"
          style={{
            background: invoked ? `${accent}10` : '#f6f6f4',
            borderColor: invoked ? `${accent}55` : '#e2e4e7',
            color: invoked ? accent : '#c2c7ce',
          }}
        >
          {/* "called" ring ping — fires once as the dispatch signal lands */}
          {invoked && (
            <motion.span
              className="absolute inset-0 rounded-lg"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: [0, 0.6, 0], scale: [0.8, 1.9, 2.2] }}
              transition={{ delay: callDelay + STRING_DRAW, duration: 0.75, ease: 'easeOut' }}
              style={{ boxShadow: `0 0 0 2px ${accent}` }}
            />
          )}
          <Icon size={15} strokeWidth={2} />
        </span>
        <div
          className="mt-1.5 max-w-full truncate text-[10px] font-semibold"
          style={{ color: invoked ? '#383f48' : '#a8adb4' }}
        >
          {agent.short}
        </div>
      </motion.div>
    </div>
  )
}

// ── Specialist card — shows what the real agent contributes. Not-invoked
//    agents render greyed (no Invoked/Standby badge). ───────────────────────
function SpecialistCard({ agent, invoked, delay }: { agent: CrewAgent; invoked: boolean; delay: number }) {
  const Icon = ICON[agent.id] ?? Bot
  const accent = agent.safety ? AMBER : BRAND
  const chrome = chromeFor(agent.id)
  const title = chrome.agentName || agent.name

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: invoked ? 1 : 0.8, y: 0, scale: 1 }}
      transition={{ delay, type: 'spring', stiffness: 240, damping: 20 }}
      className={clsx(
        'relative flex flex-col rounded-2xl border p-4 shadow-card-soft transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover',
        invoked ? 'border-ink-900/[0.08] bg-white' : 'border-ink-900/[0.06] bg-paper-50/60 opacity-80',
      )}
    >
      {/* "just got the call" ring-flash as the card lands on its dispatch beat */}
      {invoked && (
        <motion.span
          className="pointer-events-none absolute inset-0 rounded-2xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.55, 0] }}
          transition={{ delay: delay + 0.05, duration: 0.7, ease: 'easeOut' }}
          style={{ boxShadow: `inset 0 0 0 2px ${accent}, 0 0 18px -2px ${accent}` }}
        />
      )}
      {/* head row */}
      <div className="flex items-start gap-2.5">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border"
          style={
            invoked
              ? { borderColor: `${accent}44`, background: `${accent}12`, color: accent }
              : { borderColor: '#e2e4e7', background: '#f3f4f2', color: '#bdc2c9' }
          }
        >
          <Icon size={16} strokeWidth={2} />
        </span>
        <div className="min-w-0">
          <div className={clsx('font-mono text-[12.5px] font-semibold leading-tight', invoked ? 'text-ink-900' : 'text-ink-400')}>
            {title}
          </div>
          <div className="mt-0.5 text-[11px] font-medium leading-tight" style={{ color: invoked ? accent : '#a8adb4' }}>
            {chrome.team}
          </div>
        </div>
      </div>

      {/* description (from crew-registry invoke_when) */}
      {chrome.desc && (
        <p className={clsx('mt-2.5 text-[11px] leading-relaxed', invoked ? 'text-ink-500' : 'text-ink-400')}>
          {chrome.desc}
        </p>
      )}

      {/* skills */}
      {chrome.skills.length > 0 && (
        <div className="mt-3">
          <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-ink-400">Skills</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {chrome.skills.map((skill) => (
              <span
                key={skill}
                className={clsx(
                  'rounded-md border px-2 py-0.5 font-mono text-[10px]',
                  invoked ? 'border-ink-900/[0.08] bg-paper-50 text-ink-600' : 'border-ink-900/[0.06] bg-white text-ink-400',
                )}
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* contribution (what the real coded agent returns) */}
      <div className="mt-3 flex items-end justify-between gap-3 border-t border-ink-900/[0.06] pt-3.5">
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-ink-400">Contribution</div>
          <p className={clsx('mt-1.5 text-[11.5px] leading-relaxed', invoked ? 'text-ink-600' : 'text-ink-400')}>
            {chrome.contribution}
          </p>
        </div>
        <span className="flex h-7 w-7 shrink-0 items-center justify-center self-end rounded-lg border border-ink-900/[0.08] bg-white text-ink-400">
          <MessageSquare size={12} />
        </span>
      </div>
    </motion.div>
  )
}
