import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowRight,
  AudioLines,
  Eye,
  FileText,
  Flame,
  Network,
  Phone,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Zap,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useStore } from '../../store/store'
import { WhatsAppThread } from '../../components/WhatsAppThread'
import { ActivityLog } from '../../components/ActivityLog'
import { TaskCard } from '../../components/TaskCard'
import { StageRail } from '../../components/StageRail'
import { RiskGauge } from '../../components/RiskMeter'
import { Badge, Chip, Donut, Empty, PanelHeader, Sparkline } from '../../components/ui'
import { CREW_ICON } from '../../data/crewIcons'
import { ALWAYS_ON, SPECIALISTS, VISION, invocationFor, type CrewAgent } from '../../data/crew'
import { clsx, inrCompact, pct } from '../../lib/format'
import type { CaseView, PerceptionFinding } from '../../types'
import isoSlabs from '../../assets/graphics/iso-cube-slabs.jpeg'
import shieldBolt from '../../assets/graphics/shield-bolt.jpeg'

const MODALITY_ICON = { image: ScanSearch, audio: AudioLines, thermal: Flame, text: FileText } as const

const SCENARIO_TAG: Record<'A' | 'B' | 'C', string> = {
  A: 'RF · from scratch',
  B: 'cited',
  C: 'MC4 cross-mating',
}

export function ConsoleTab() {
  const c = useStore((s) => (s.activeCaseId ? s.cases[s.activeCaseId] : null))
  if (!c) return <Empty text="No active case — press play in the top bar." />

  return (
    <div className="space-y-7">
      <CaseHeader c={c} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left — WhatsApp + Action Center */}
        <div className="space-y-6 lg:col-span-4">
          <div className="panel h-[460px] overflow-hidden">
            <WhatsAppThread messages={c.chat} name={c.worker_name} phone={c.worker_phone} />
          </div>
          {c.tasks.length > 0 && (
            <div className="space-y-3">
              {c.tasks.map((t) => (
                <TaskCard key={t.id} task={t} />
              ))}
            </div>
          )}
          {c.tasks.some((t) => t.kind === 'approve_call') && <ActionCenterCTA />}
        </div>

        {/* Center — findings */}
        <div className="space-y-6 lg:col-span-5">
          <SkillBanner c={c} />
          <PerceptionCard c={c} />
          <CrewStrip c={c} />
          <InvestigationCard c={c} />
          <CallDecision c={c} />
        </div>

        {/* Right — live activity */}
        <div className="lg:col-span-3">
          <div className="panel sticky top-[136px] flex h-[640px] flex-col">
            <PanelHeader
              title="Live activity"
              icon={<AudioLines size={15} />}
              right={<Chip>{c.log.length} events</Chip>}
              className="border-b border-ink-900/[0.07]"
            />
            <div className="min-h-0 flex-1">
              <ActivityLog entries={c.log} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function CaseHeader({ c }: { c: CaseView }) {
  return (
    <div className="section-card relative overflow-hidden p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Chip className="!text-[10px]">Case {c.scenario}</Chip>
            <Chip className="!text-[10px]">{SCENARIO_TAG[c.scenario]}</Chip>
            {c.skillHit && (
              <Badge tone="ok">
                <Sparkles size={11} /> Matched: {c.skillHit.source}
              </Badge>
            )}
          </div>
          <h2 className="mt-3 flex items-center gap-2.5 font-serif text-[26px] font-normal leading-[1.12] tracking-[-0.012em] text-ink-900 sm:text-[31px]">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-500/[0.1] text-brand-600">
              <Zap size={18} fill="currentColor" />
            </span>
            {c.title}
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-ink-500">
            <span>{c.case_id}</span>
            <span className="text-ink-300">·</span>
            <span>{c.site_id}</span>
            <span className="text-ink-300">·</span>
            <span>{c.worker_name}</span>
            <span className="text-ink-300">·</span>
            <span>opened {c.opened_at}</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <img src={isoSlabs} alt="" className="hidden h-[88px] w-[88px] object-contain mix-blend-multiply 2xl:block" />
          <div className="grid grid-cols-3 gap-3">
            <SparkKpi
              label="Exposure / hr"
              value={c.investigation ? inrCompact(c.investigation.exposure_per_hr ?? 0) : '—'}
              data={[3, 4, 3.6, 5, 4.4, 6, 7, 9.2]}
              color="#e23b3b"
            />
            <SparkKpi
              label="Fleet affected"
              value={c.fleet ? String(c.fleet.affected.length) : '—'}
              data={[1, 2, 2, 3, 4, 5, 6, 6]}
              color="#e23b3b"
            />
            <SparkKpi
              label="Confidence"
              value={c.investigation ? pct(c.investigation.confidence) : '—'}
              data={[70, 74, 78, 82, 85, 88, 91, 93]}
              color="#1aa251"
            />
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 items-center gap-6 border-t border-ink-900/[0.06] pt-6 lg:grid-cols-[1fr_300px]">
        <StageRail stage={c.stage} status={c.status} />
        <div className="lg:border-l lg:border-ink-900/[0.06] lg:pl-6">
          <RiskGauge value={c.risk_score} />
        </div>
      </div>
    </div>
  )
}

function SparkKpi({ label, value, data, color }: { label: string; value: string; data: number[]; color: string }) {
  return (
    <div className="flex w-[112px] flex-col rounded-xl border border-ink-900/[0.07] bg-white px-3 py-2.5 shadow-card-soft">
      <div className="text-[9px] font-semibold uppercase tracking-[0.1em] text-ink-400">{label}</div>
      <div className="mt-1 font-display text-[20px] font-bold leading-none tracking-tightest text-ink-900">
        {value}
      </div>
      <Sparkline data={data} color={color} width={88} height={22} className="mt-2" />
    </div>
  )
}

function SkillBanner({ c }: { c: CaseView }) {
  if (!c.skillHit && !c.skillWritten) {
    if (c.stage === 'perceive' && c.scenario === 'A')
      return (
        <div className="rounded-2xl border border-warn/25 bg-warn/[0.05] px-4 py-3 text-[12.5px] text-ink-700">
          <span className="font-semibold text-warn">No skill matched</span> — nothing learned yet. The
          crew will reason from scratch.
        </div>
      )
    return null
  }
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3 rounded-2xl border border-ok/30 bg-ok/[0.06] px-4 py-3"
      >
        <Sparkles size={18} className="shrink-0 text-ok" />
        <div className="text-[12.5px] text-ink-700">
          {c.skillHit ? (
            <>
              <span className="font-semibold text-ok">Seen this before.</span> Matched{' '}
              <span className="font-mono">{c.skillHit.id}</span> ({c.skillHit.status}) from{' '}
              <span className="font-mono">{c.skillHit.source}</span> — passed the hard gate.
            </>
          ) : (
            <>
              <span className="font-semibold text-ok">New skill written.</span> Distilled{' '}
              <span className="font-mono">{c.skillWritten!.id}</span> as a candidate.
            </>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  )
}

function PerceptionCard({ c }: { c: CaseView }) {
  if (!c.perception) return null
  const p = c.perception
  // Prefer the horizontal findings list; fall back to the legacy telecom fields.
  const findings: PerceptionFinding[] =
    p.findings ?? [
      ...(p.corrosion
        ? [{
            modality: 'image' as const,
            label: 'Corrosion',
            detail: p.corrosion.present ? `present · ${p.corrosion.severity}` : 'none',
            severity: p.corrosion.present ? p.corrosion.severity : undefined,
          }]
        : []),
      ...(p.generator_audio
        ? [{
            modality: 'audio' as const,
            label: 'Generator audio',
            detail:
              p.generator_audio.anomaly === 'none'
                ? 'normal'
                : `${p.generator_audio.anomaly} · ${pct(p.generator_audio.confidence)}`,
          }]
        : []),
    ]
  return (
    <div className="panel p-4">
      <PanelHeader title="Perception · Vision" icon={<Eye size={15} />} className="!px-0 !py-0 pb-3" />
      <div className={clsx('grid gap-3', findings.length > 1 ? 'grid-cols-2' : 'grid-cols-1')}>
        {findings.map((f, i) => {
          const Icon = MODALITY_ICON[f.modality] ?? ScanSearch
          const hot = f.severity === 'high' || f.severity === 'critical'
          return (
            <div
              key={i}
              className="rounded-xl border border-ink-900/[0.07] bg-ink-900/[0.02] p-3"
              style={hot ? { borderColor: '#e23b3b40', background: '#e23b3b0a' } : undefined}
            >
              <div className="flex items-center gap-2 text-[11px] text-ink-500">
                <Icon size={13} /> {f.label}
              </div>
              <div className="mt-1 text-sm font-semibold" style={{ color: hot ? '#e23b3b' : '#14171c' }}>
                {f.detail ?? (f.confidence != null ? pct(f.confidence) : '—')}
              </div>
            </div>
          )
        })}
      </div>
      {(c.asset_note || p.issues.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {p.issues.map((i) => (
            <Chip key={i}>{i}</Chip>
          ))}
          {c.asset_note && <Chip className="text-ink-400">{c.asset_note}</Chip>}
        </div>
      )}
    </div>
  )
}

type CrewStatus = 'queued' | 'running' | 'done'

function CrewStrip({ c }: { c: CaseView }) {
  if (!c.crewAssembled && !c.reachedStages.includes('perceive')) return null
  const { invoked, skipped } = invocationFor(c.scenario)
  const byId = Object.fromEntries(SPECIALISTS.map((s) => [s.id, s]))
  const past = (['escalate', 'resolve', 'close'] as const).some((s) => c.reachedStages.includes(s))
  const atInvestigate = c.reachedStages.includes('investigate')
  // Perceive: only the always-on core (Vision + Brain) works. The dynamic crew is
  // assembled later, at Investigate — so the specialists only appear from then.
  const coreStatus: CrewStatus = atInvestigate ? 'done' : 'running'
  const specStatus: CrewStatus = past ? 'done' : 'running'

  return (
    <div className="panel p-4">
      <div className="mb-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[13px] font-semibold text-ink-900">
          <Network size={14} className="text-ink-400" />
          {atInvestigate ? 'Crew · assembled for this case' : 'Perceiving · vision + brain'}
        </div>
        <Link to="/app/crew" className="text-[11px] font-medium text-ink-400 transition-colors hover:text-ink-700">
          all {SPECIALISTS.length} →
        </Link>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <CrewChip agent={VISION} status={coreStatus} brain />
        <CrewChip agent={ALWAYS_ON} status={coreStatus} brain />
        {atInvestigate &&
          invoked.map((inv) => {
            const a = byId[inv.id]
            return a ? <CrewChip key={inv.id} agent={a} status={specStatus} /> : null
          })}
        {atInvestigate && skipped.length > 0 && (
          <span className="rounded-md border border-ink-900/[0.07] bg-paper-50 px-2.5 py-1 text-[10.5px] text-ink-400">
            +{skipped.length} held back
          </span>
        )}
      </div>
    </div>
  )
}

function CrewChip({ agent, status, brain }: { agent: CrewAgent; status: CrewStatus; brain?: boolean }) {
  const Icon = CREW_ICON[agent.id] ?? Network
  const accent = agent.safety ? '#c77b08' : '#2f6dff'
  const dot = status === 'done' ? '#1aa251' : status === 'running' ? accent : '#cbd0d6'
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11px] font-medium text-ink-700"
      style={{ borderColor: `${accent}${brain ? '4d' : '2b'}`, background: brain ? `${accent}14` : `${accent}08` }}
    >
      <Icon size={13} style={{ color: accent }} />
      {agent.short}
      <span
        className={clsx('h-1.5 w-1.5 rounded-full', status === 'running' && 'animate-pulse')}
        style={{ background: dot, boxShadow: status !== 'queued' ? `0 0 6px ${dot}` : undefined }}
      />
    </span>
  )
}

function InvestigationCard({ c }: { c: CaseView }) {
  const navigate = useNavigate()
  if (!c.investigation) return null
  const inv = c.investigation
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="panel p-4">
      <PanelHeader title="Merged recommendation" icon={<TriangleAlert size={15} />} className="!px-0 !py-0 pb-3" />
      <div className="rounded-xl border border-brand-400/20 bg-brand-500/[0.05] p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-400">Root cause</div>
            <div className="mt-1 text-[14.5px] font-semibold leading-snug text-ink-900">{inv.root_cause}</div>
          </div>
          <Donut
            value={Math.round(inv.confidence * 100)}
            size={62}
            stroke={6}
            color="#2f6dff"
            className="shrink-0"
            center={<div className="font-display text-[13px] font-bold text-ink-900">{pct(inv.confidence)}</div>}
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {inv.systemic && (
            <Badge tone="danger">
              systemic · {inv.fleet_affected} {c.fleet?.unitNoun ?? 'site'}s
            </Badge>
          )}
          {inv.alternatives_ruled_out.map((a) => (
            <Chip key={a}>ruled out · {a}</Chip>
          ))}
        </div>
        <div className="mt-3 border-t border-ink-900/[0.07] pt-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-400">Recommendation</div>
          <div className="mt-0.5 text-[13px] leading-relaxed text-ink-900">{inv.recommendation}</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2.5">
        <button
          onClick={() => navigate('/app/calls')}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-[12.5px] font-semibold text-white shadow-[0_6px_16px_-6px_rgba(47,109,255,0.6)] transition-all hover:bg-brand-600"
        >
          Escalate to Action Center <ArrowRight size={14} />
        </button>
        <button
          onClick={() => navigate('/app/audit')}
          className="inline-flex items-center gap-2 rounded-lg border border-ink-900/[0.12] bg-white px-4 py-2 text-[12.5px] font-semibold text-ink-700 transition-colors hover:border-ink-900/25 hover:text-ink-900"
        >
          Simulate Outcome
        </button>
      </div>
    </motion.div>
  )
}

function ActionCenterCTA() {
  const navigate = useNavigate()
  return (
    <div className="relative overflow-hidden rounded-2xl border border-warn/25 bg-gradient-to-br from-warn/[0.06] to-white p-4">
      <img src={shieldBolt} alt="" className="pointer-events-none absolute -right-3 -top-2 h-24 w-24 object-contain opacity-90" />
      <div className="relative max-w-[78%]">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-warn">
          <ShieldCheck size={14} /> Action Center
        </div>
        <p className="mt-2 text-[12.5px] leading-relaxed text-ink-600">
          High DC-arc risk on RJ-SOLAR-1 — strings exposed via the same connector lot. Guarded human gate.
        </p>
        <button
          onClick={() => navigate('/app/calls')}
          className="mt-3 inline-flex items-center gap-2 rounded-lg bg-brand-500 px-3.5 py-2 text-[12px] font-semibold text-white shadow-[0_6px_16px_-6px_rgba(47,109,255,0.6)] transition-all hover:bg-brand-600"
        >
          Open Action Center <ArrowRight size={14} />
        </button>
      </div>
    </div>
  )
}

function CallDecision({ c }: { c: CaseView }) {
  const d = c.call.decision
  if (!d) return null
  return (
    <div className="panel flex items-center gap-3 p-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ok/15 text-ok">
        <Phone size={18} />
      </div>
      <div className="text-[12.5px]">
        <div className="font-semibold text-ink-900">
          Authorised by voice · {d.by} @ {d.at}
        </div>
        <div className="text-ink-500">
          {d.actions.map((a) => (
            <span key={a} className="mr-1.5 font-mono text-[11px] text-ok">
              {a}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
