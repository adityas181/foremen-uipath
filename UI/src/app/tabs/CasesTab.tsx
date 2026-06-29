import { motion } from 'framer-motion'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  Factory,
  RadioTower,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  TrainFront,
  Wind,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import { useStore } from '../../store/store'
import { Badge, MetricCard, Trend } from '../../components/ui'
import { clsx } from '../../lib/format'
import { TONE_HEX, type Tone } from '../../lib/hues'
import { STAGES, type CaseView } from '../../types'
import isoCube from '../../assets/graphics/iso-cube-tall.jpeg'

const STATUS_TONE: Record<CaseView['status'], Tone> = {
  open: 'info',
  parked: 'warn',
  resolved: 'ok',
  closed: 'ok',
}

function riskTone(score: number): Tone {
  if (score >= 0.7) return 'danger'
  if (score >= 0.45) return 'warn'
  return 'ok'
}

// asset-class → icon + accent (purely presentational)
function classIcon(vertical: string): { Icon: LucideIcon; hex: string } {
  const v = vertical.toLowerCase()
  if (v.includes('wind')) return { Icon: Wind, hex: '#3ba7f0' }
  if (v.includes('telecom') || v.includes('tower')) return { Icon: RadioTower, hex: '#7c5cdb' }
  if (v.includes('manufact') || v.includes('mould')) return { Icon: Factory, hex: '#c77b08' }
  if (v.includes('hvac')) return { Icon: Activity, hex: '#1d84d6' }
  if (v.includes('rail')) return { Icon: TrainFront, hex: '#1aa251' }
  if (v.includes('solar') || v.includes('pv')) return { Icon: Sun, hex: '#e6ab3e' }
  return { Icon: Cpu, hex: '#2f6dff' }
}

type PriorCase = {
  id: string
  site: string
  vertical: string
  issue: string
  risk: number
  status: 'resolved' | 'closed'
  opened: string
  outcome: string
}

const PRIOR_CASES: PriorCase[] = [
  { id: 'CASE-WND-0512', site: 'GJ-WIND-2', vertical: 'Wind · turbine', issue: 'Gearbox bearing over-temperature', risk: 0.71, status: 'resolved', opened: '14 Jun', outcome: 'Crew dispatched · resolved' },
  { id: 'CASE-TWR-0473', site: 'DEL-COAST-4', vertical: 'Telecom · tower', issue: 'Coastal RF-jumper corrosion', risk: 0.82, status: 'closed', opened: '09 Jun', outcome: 'Skill promoted · trusted' },
  { id: 'CASE-IMM-2207', site: 'PLANT-W2', vertical: 'Manufacturing · moulder', issue: 'Auxiliary hydraulic vibration', risk: 0.54, status: 'resolved', opened: '05 Jun', outcome: 'Auto-resolved · no call' },
  { id: 'CASE-HVAC-1180', site: 'DC-NORTH-3', vertical: 'HVAC · chiller', issue: 'Compressor over-temp trip', risk: 0.61, status: 'closed', opened: '02 Jun', outcome: 'Work order raised' },
  { id: 'CASE-RAIL-3391', site: 'LINE-7 · KM42', vertical: 'Rail · signalling', issue: 'Intermittent point failure', risk: 0.47, status: 'closed', opened: '28 May', outcome: 'Trend flagged · monitored' },
]

export function CasesTab() {
  const order = useStore((s) => s.order)
  const cases = useStore((s) => s.cases)
  const activeCaseId = useStore((s) => s.activeCaseId)
  const selectCase = useStore((s) => s.selectCase)
  const navigate = useNavigate()

  const open = (id: string) => {
    selectCase(id)
    navigate('/app/console')
  }

  const liveCases = order.map((id) => cases[id]).filter(Boolean) as CaseView[]
  // Live row: live case(s) first, then prior cases styled as live cards to fill 3.
  const livePriors = PRIOR_CASES.slice(0, Math.max(0, 3 - liveCases.length))

  return (
    <div className="space-y-8">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute right-0 top-1/2 hidden h-[360px] w-[460px] -translate-y-1/2 lg:block">
          <img src={isoCube} alt="" className="absolute inset-0 h-full w-full object-contain mix-blend-multiply" />
        </div>
        <div className="relative max-w-2xl">
          <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-ink-400">
            Case Control Room
          </div>
          <h1 className="mt-4 font-serif text-[40px] font-normal leading-[1.05] tracking-[-0.015em] text-ink-900 sm:text-[52px]">
            Intelligent cases.
            <br />
            Autonomously resolved.
          </h1>
          <p className="mt-4 max-w-md text-[15px] leading-relaxed text-ink-500">
            From first signal to documented resolution — across every asset class.
          </p>
        </div>
      </section>

      {/* ── KPI row ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={<Activity size={20} />}
          label="Live cases"
          value={liveCases.length}
          tone="info"
          trend={<Trend dir="up">1 from yesterday</Trend>}
        />
        <MetricCard
          icon={<CheckCircle2 size={20} />}
          label="Resolved today"
          value={41}
          tone="ok"
          trend={<Trend dir="up" tone="ok">18% from yesterday</Trend>}
        />
        <MetricCard
          icon={<Clock size={20} />}
          label="Avg resolution time"
          value="7m 12s"
          tone="human"
          trend={<Trend dir="down">1.2m from yesterday</Trend>}
        />
        <MetricCard
          icon={<ShieldCheck size={20} />}
          label="Success rate"
          value="98.2%"
          tone="ok"
          trend={<Trend dir="up" tone="ok">1.8% from yesterday</Trend>}
        />
      </div>

      {/* ── Live cases ───────────────────────────────────────────────────── */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-500 opacity-70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-500" />
            </span>
            <h2 className="text-[16px] font-semibold tracking-tight text-ink-900">Live Cases</h2>
          </div>
          <button
            onClick={() => navigate('/app/console')}
            className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-brand-600 transition-colors hover:text-brand-700"
          >
            View in Console <ArrowRight size={14} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {liveCases.map((c, i) => (
            <LiveCaseCard key={c.case_id} c={c} active={c.case_id === activeCaseId} index={i} onOpen={open} />
          ))}
          {livePriors.map((p, i) => (
            <LivePriorCard key={p.id} p={p} index={liveCases.length + i} />
          ))}
        </div>
      </section>

      {/* ── Recent cases table ───────────────────────────────────────────── */}
      <RecentTable rows={PRIOR_CASES} />
    </div>
  )
}

// ── Live case card ──────────────────────────────────────────────────────────
function LiveCaseCard({
  c,
  active,
  index,
  onOpen,
}: {
  c: CaseView
  active: boolean
  index: number
  onOpen: (id: string) => void
}) {
  const stage = STAGES.find((s) => s.id === c.stage)
  const { Icon, hex } = classIcon(c.title)
  const statusLabel = c.status === 'parked' ? 'Review' : c.status === 'open' ? 'Open' : c.status
  return (
    <motion.button
      type="button"
      onClick={() => onOpen(c.case_id)}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={clsx(
        'group flex w-full flex-col rounded-2xl border bg-white p-5 text-left shadow-card-soft transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover',
        active ? 'border-brand-400/50 ring-1 ring-brand-400/25' : 'border-ink-900/[0.07]',
      )}
    >
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.1em] text-brand-600">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500" /> Live
        </span>
        <Badge tone={STATUS_TONE[c.status]}>{statusLabel}</Badge>
      </div>
      <div className="mt-4 flex items-start gap-3.5">
        <span
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
          style={{ background: `${hex}12`, color: hex, border: `1px solid ${hex}24` }}
        >
          <Icon size={22} />
        </span>
        <div className="min-w-0">
          <h3 className="font-display text-[16px] font-semibold leading-snug tracking-[-0.01em] text-ink-900">
            {c.title}
          </h3>
          <div className="mt-1 font-mono text-[10.5px] uppercase tracking-wide text-ink-400">
            {c.site_id} · {c.case_id}
          </div>
        </div>
      </div>
      <CaseFooter stageLabel={stage?.label ?? c.stage} detected={c.opened_at} risk={c.risk_score} />
    </motion.button>
  )
}

function LivePriorCard({ p, index }: { p: PriorCase; index: number }) {
  const { Icon, hex } = classIcon(p.vertical)
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="group flex flex-col rounded-2xl border border-ink-900/[0.07] bg-white p-5 shadow-card-soft transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover"
    >
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.1em] text-ink-400">
          <span className="h-1.5 w-1.5 rounded-full bg-ink-300" /> Prior
        </span>
        <Badge tone="ok">{p.status === 'resolved' ? 'Open' : 'Review'}</Badge>
      </div>
      <div className="mt-4 flex items-start gap-3.5">
        <span
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
          style={{ background: `${hex}12`, color: hex, border: `1px solid ${hex}24` }}
        >
          <Icon size={22} />
        </span>
        <div className="min-w-0">
          <h3 className="font-display text-[16px] font-semibold leading-snug tracking-[-0.01em] text-ink-900">
            {p.issue}
          </h3>
          <div className="mt-1 font-mono text-[10.5px] uppercase tracking-wide text-ink-400">
            {p.site} · {p.id}
          </div>
        </div>
      </div>
      <CaseFooter stageLabel="Resolved" detected={p.opened} risk={p.risk} />
    </motion.div>
  )
}

function CaseFooter({ stageLabel, detected, risk }: { stageLabel: string; detected: string; risk: number | null }) {
  return (
    <div className="mt-4 flex items-center gap-3 border-t border-ink-900/[0.06] pt-3.5 text-[11px]">
      <span className="text-ink-400">Stage</span>
      <span className="rounded-md bg-ink-900/[0.05] px-1.5 py-0.5 font-medium text-ink-700">{stageLabel}</span>
      <span className="text-ink-300">·</span>
      <span className="text-ink-400">Detected {detected}</span>
      <span className="ml-auto flex items-center gap-1.5">
        <span className="text-ink-400">Risk</span>
        {risk === null ? (
          <span className="font-mono text-ink-400">—</span>
        ) : (
          <span className="font-mono font-semibold" style={{ color: TONE_HEX[riskTone(risk)] }}>
            {risk.toFixed(2)}
          </span>
        )}
      </span>
    </div>
  )
}

// ── Recent cases table ──────────────────────────────────────────────────────
function RecentTable({ rows }: { rows: PriorCase[] }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-ink-900/[0.07] bg-white shadow-card-soft">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <h2 className="flex items-center gap-2 text-[15px] font-semibold tracking-tight text-ink-900">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-ink-900/[0.05] text-ink-500">
            <Activity size={13} />
          </span>
          Recent Cases
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <FilterSelect label="All Asset Classes" />
          <FilterSelect label="All Status" />
          <div className="flex items-center gap-2 rounded-lg border border-ink-900/[0.10] bg-paper-50 px-3 py-1.5">
            <Search size={13} className="text-ink-400" />
            <span className="text-[12px] text-ink-400">Search cases…</span>
          </div>
          <button className="flex h-8 w-8 items-center justify-center rounded-lg border border-ink-900/[0.10] bg-white text-ink-400 transition-colors hover:text-ink-700">
            <SlidersHorizontal size={14} />
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] border-collapse text-left">
          <thead>
            <tr className="border-y border-ink-900/[0.06] text-[10.5px] font-semibold uppercase tracking-[0.08em] text-ink-400">
              <th className="px-5 py-2.5 font-semibold">Case</th>
              <th className="px-3 py-2.5 font-semibold">Asset class</th>
              <th className="px-3 py-2.5 font-semibold">Issue</th>
              <th className="px-3 py-2.5 font-semibold">Risk</th>
              <th className="px-3 py-2.5 font-semibold">Status</th>
              <th className="px-3 py-2.5 font-semibold">Opened</th>
              <th className="px-5 py-2.5 font-semibold">Outcome</th>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const { Icon, hex } = classIcon(r.vertical)
              return (
                <tr
                  key={r.id}
                  className="border-b border-ink-900/[0.05] transition-colors last:border-0 hover:bg-ink-900/[0.015]"
                >
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <span
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
                        style={{ background: `${hex}12`, color: hex }}
                      >
                        <Icon size={15} />
                      </span>
                      <div>
                        <div className="font-mono text-[12px] font-medium text-ink-900">{r.id}</div>
                        <div className="mt-0.5 font-mono text-[10.5px] text-ink-400">{r.site}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3.5">
                    <span className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-600">
                      <span className="h-1.5 w-1.5 rounded-full" style={{ background: hex }} />
                      {r.vertical}
                    </span>
                  </td>
                  <td className="px-3 py-3.5 text-[13px] font-medium text-ink-800">{r.issue}</td>
                  <td className="px-3 py-3.5">
                    <span className="font-mono text-[12.5px] font-semibold" style={{ color: TONE_HEX[riskTone(r.risk)] }}>
                      {r.risk.toFixed(2)}
                    </span>
                  </td>
                  <td className="px-3 py-3.5">
                    <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-ink-700">
                      <span className="h-2 w-2 rounded-full" style={{ background: TONE_HEX[STATUS_TONE[r.status]] }} />
                      {r.status[0].toUpperCase() + r.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-3 py-3.5 font-mono text-[11.5px] text-ink-500">{r.opened}</td>
                  <td className="px-5 py-3.5">
                    <span className="inline-flex items-center gap-1.5 text-[12px] text-ink-600">
                      <span className="h-1.5 w-1.5 rounded-full bg-ink-300" />
                      {r.outcome}
                    </span>
                  </td>
                  <td className="px-3 py-3.5 text-right">
                    <ChevronRight size={15} className="text-ink-300" />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-center border-t border-ink-900/[0.06] py-3.5">
        <button className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-brand-600 transition-colors hover:text-brand-700">
          View all cases <ArrowUpRight size={14} />
        </button>
      </div>
    </section>
  )
}

function FilterSelect({ label }: { label: string }) {
  return (
    <button className="inline-flex items-center gap-2 rounded-lg border border-ink-900/[0.10] bg-white px-3 py-1.5 text-[12px] font-medium text-ink-600 transition-colors hover:border-ink-900/20">
      {label}
      <ChevronRight size={13} className="rotate-90 text-ink-400" />
    </button>
  )
}
