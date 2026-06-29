import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertTriangle,
  BadgeCheck,
  Check,
  ChevronDown,
  CornerUpLeft,
  CornerUpRight,
  Download,
  FileText,
  FileVideo,
  GitBranch,
  Image as ImageIcon,
  Layers,
  Loader2,
  MoreVertical,
  Network,
  Paperclip,
  ScrollText,
  Sparkles,
  Star,
  ThumbsDown,
  ThumbsUp,
  Zap,
} from 'lucide-react'
import { useStore } from '../../store/store'
import { ArtifactCard } from '../../components/ArtifactCard'
import { Badge, Chip, Empty, Eyebrow, TabHeader } from '../../components/ui'
import { clsx } from '../../lib/format'
import { TONE_HEX, type Tone } from '../../lib/hues'
import type { CaseView } from '../../types'
import auditHero from '../../assets/graphics/audit-hero.jpeg'
import auditPack from '../../assets/graphics/audit-pack.jpeg'
import feedbackLoop from '../../assets/graphics/feedback-loop.jpeg'

export function AuditTab() {
  const c = useStore((s) => (s.activeCaseId ? s.cases[s.activeCaseId] : null))

  if (!c || (!c.audit && c.artifacts.length === 0)) {
    return (
      <Empty
        icon={<FileText size={26} />}
        text="No closure pack yet — it assembles in the Close stage."
      />
    )
  }

  return (
    <div className="space-y-8">
      <Hero c={c} />

      {/* Main row — email (left) + criticality ranking (right) */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_320px]">
        <EmailCard c={c} />
        <CriticalityCard c={c} />
      </div>

      {/* Artifacts produced + audit-pack card */}
      {c.artifacts.length > 0 && (
        <div>
          <Eyebrow>Artifacts produced</Eyebrow>
          <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_300px]">
            {c.artifacts.map((a) => (
              <ArtifactCard key={a.id} a={a} />
            ))}
            <AuditPackCard />
          </div>
        </div>
      )}

      {c.graphNote && (
        <div className="flex items-center gap-2.5 rounded-xl border border-info/25 bg-info/[0.06] px-4 py-3 text-[12.5px] text-ink-700">
          <Network size={16} className="shrink-0 text-info" />
          <span>{c.graphNote}</span>
        </div>
      )}

      <FeedbackRow c={c} />
    </div>
  )
}

// ── Hero — title block + floating audit illustration + KPI cluster ───────────
function Hero({ c }: { c: CaseView }) {
  const crit = c.fleet?.criticality ?? []
  const stringsAtRisk = crit.reduce((n, f) => Math.max(n, f.count), 0) || 6
  const batches = crit.length || 3
  const nodesInGraph = c.fleet?.nodes.length ?? 13
  const edges = c.fleet?.edges.length ?? 18
  const exposurePerHr = c.fleet?.exposurePerHr ?? c.investigation?.exposure_per_hr

  const kpis: { icon: typeof Layers; value: string; label: string; sub: string; tone: keyof typeof TONE_HEX }[] = [
    { icon: Layers, value: '0', label: 'Same-batch query', sub: 'real strings found', tone: 'info' },
    {
      icon: Network,
      value: String(stringsAtRisk),
      label: 'Strings at risk',
      sub: `Across ${batches} module batches`,
      tone: 'danger',
    },
    {
      icon: Layers,
      value: String(nodesInGraph),
      label: 'Nodes in graph',
      sub: `${edges} total edges`,
      tone: 'info',
    },
    {
      icon: Zap,
      value: exposurePerHr ? `₹${(exposurePerHr / 1000).toFixed(1)}k/hr` : '₹9.2k/hr',
      label: 'Generation revenue',
      sub: 'at risk',
      tone: 'warn',
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_auto] lg:items-start">
      {/* Title + floating illustration */}
      <div className="relative">
        <div className="absolute -right-2 -top-6 hidden h-[230px] w-[300px] select-none lg:block">
          <img
            src={auditHero}
            alt="A cited audit pack on a shield podium"
            className="h-full w-full object-contain mix-blend-multiply [mask-image:radial-gradient(120%_120%_at_55%_45%,#000_60%,transparent_100%)]"
          />
        </div>
        <TabHeader
          eyebrow="Closure · audit + learn"
          title="The defensible paper trail"
          sub="Every case closes into one cited audit pack — emailed, attached, logged."
        />
      </div>

      {/* Right column — timeline button + 2×2 KPI cluster */}
      <div className="flex flex-col items-end gap-4">
        <button className="inline-flex items-center gap-2 rounded-lg border border-ink-900/[0.12] bg-white px-3.5 py-2 text-[12.5px] font-semibold text-ink-700 shadow-card-soft transition-colors hover:bg-paper-50">
          <ScrollText size={14} className="text-ink-400" />
          Audit timeline
        </button>
        <div className="grid w-full grid-cols-2 gap-3 lg:w-[330px]">
          {kpis.map((k) => {
            const hex = TONE_HEX[k.tone]
            return (
              <div
                key={k.label}
                className="rounded-2xl border border-ink-900/[0.08] bg-white p-3.5 shadow-card-soft"
              >
                <span
                  className="flex h-8 w-8 items-center justify-center rounded-lg"
                  style={{ background: `${hex}14`, color: hex, border: `1px solid ${hex}2a` }}
                >
                  <k.icon size={15} />
                </span>
                <div className="mt-2.5 font-display text-[22px] font-bold leading-none tracking-tightest text-ink-900">
                  {k.value}
                </div>
                <div className="mt-1.5 text-[11.5px] font-medium leading-tight text-ink-700">{k.label}</div>
                <div className="text-[10.5px] leading-tight text-ink-400">{k.sub}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Criticality ranking — harden-first single-points-of-failure ──────────────
const CRIT_FALLBACK = [
  { factor: 'CREW-PV-3', count: 6 },
  { factor: 'MC4-LOT-X', count: 4 },
  { factor: 'MOD-LOT-A', count: 3 },
]

function CriticalityCard({ c }: { c: CaseView }) {
  const rows = (c.fleet?.criticality?.length ? c.fleet.criticality : CRIT_FALLBACK).slice(0, 3)
  const max = rows.reduce((n, r) => Math.max(n, r.count), 0) || 1
  const barTone = ['#e23b3b', '#c77b08', '#7c5cdb']

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="flex flex-col rounded-2xl border border-ink-900/[0.08] bg-white p-5 shadow-card-soft"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[14.5px] font-semibold tracking-tight text-ink-900">Criticality ranking</h3>
        <Chip className="text-ink-500" icon={<AlertTriangle size={11} />}>
          harden first
        </Chip>
      </div>

      <div className="mt-5 space-y-5">
        {rows.map((r, i) => (
          <div key={r.factor}>
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-mono text-[12.5px] font-semibold text-ink-900">{r.factor}</span>
              <span className="text-[11.5px] font-medium text-ink-500">{r.count} exposed</span>
            </div>
            <div className="mt-2 h-[5px] w-full overflow-hidden rounded-full bg-ink-900/[0.06]">
              <div
                className="h-full rounded-full"
                style={{ width: `${(r.count / max) * 100}%`, background: barTone[i] ?? barTone[2] }}
              />
            </div>
          </div>
        ))}
      </div>

      <button className="mt-6 inline-flex items-center justify-center gap-1.5 rounded-lg border border-ink-900/[0.12] px-3.5 py-2 text-[12.5px] font-semibold text-ink-700 transition-colors hover:bg-paper-50">
        View full ranking
        <CornerUpRight size={13} className="text-ink-400" />
      </button>
    </motion.div>
  )
}

// Gmail-style attachment card — file-type icon + name + download on hover.
const ATT_STYLE: Record<string, { icon: typeof FileText; hex: string }> = {
  pdf: { icon: FileText, hex: '#EA4335' },
  mp4: { icon: FileVideo, hex: '#7C5CDB' },
  mov: { icon: FileVideo, hex: '#7C5CDB' },
  jpg: { icon: ImageIcon, hex: '#1AA251' },
  jpeg: { icon: ImageIcon, hex: '#1AA251' },
  png: { icon: ImageIcon, hex: '#1AA251' },
  txt: { icon: FileText, hex: '#5F6368' },
}

function GmailAttachment({ name }: { name: string }) {
  const ext = (name.split('.').pop() ?? '').toLowerCase()
  const { icon: Icon, hex } = ATT_STYLE[ext] ?? { icon: Paperclip, hex: '#5F6368' }
  return (
    <div className="group relative flex w-[160px] items-center gap-2.5 rounded-lg border border-ink-900/[0.14] bg-white px-3 py-2.5 transition-colors hover:bg-paper-50">
      <span
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md"
        style={{ background: `${hex}14`, color: hex }}
      >
        <Icon size={18} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[12.5px] font-medium text-ink-800">{name}</div>
        <div className="text-[10.5px] uppercase tracking-wide text-ink-400">{ext} file</div>
      </div>
      <Download
        size={15}
        className="shrink-0 text-ink-300 opacity-0 transition-opacity group-hover:opacity-100"
      />
    </div>
  )
}

// The REAL sent email is the email agent's body (Summary + the labelled
// Report / Root cause / Systemic / Decision / Actions / Warranty sections).
// Parse it into those sections and colour them like the delivered email — we
// show exactly what was sent, not a re-derivation from the investigation.
const SECTION_DEFS: { re: RegExp; label: string; tone: Tone }[] = [
  { re: /^report$/i, label: 'Report', tone: 'muted' },
  { re: /^root\s*cause$/i, label: 'Root cause', tone: 'danger' },
  { re: /^systemic$/i, label: 'Systemic', tone: 'warn' },
  { re: /^decision$/i, label: 'Decision', tone: 'ok' },
  { re: /^actions?$/i, label: 'Actions', tone: 'info' },
  { re: /^warranty$/i, label: 'Warranty', tone: 'human' },
]

function parseAuditEmail(body: string): {
  intro: string
  sections: { label: string; tone: Tone; text: string }[]
  footer: string
} {
  let intro = ''
  let footer = ''
  const sections: { label: string; tone: Tone; text: string }[] = []
  let cur: { label: string; tone: Tone; text: string } | null = null
  for (const raw of (body || '').split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if (/^generated by\b/i.test(line)) {
      footer = line
      continue
    }
    const head = line.includes(':') ? line.slice(0, line.indexOf(':')).trim() : ''
    const def = head ? SECTION_DEFS.find((d) => d.re.test(head)) : undefined
    if (def) {
      if (cur) sections.push(cur)
      cur = { label: def.label, tone: def.tone, text: line.slice(line.indexOf(':') + 1).trim() }
    } else if (cur) {
      cur.text += ' ' + line
    } else {
      intro += (intro ? ' ' : '') + line
    }
  }
  if (cur) sections.push(cur)
  return { intro, sections, footer }
}

function EmailCard({ c }: { c: CaseView }) {
  if (!c.audit) return null
  const { email, attachments } = c.audit
  const parsed = parseAuditEmail(email.body)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="overflow-hidden rounded-2xl border border-ink-900/[0.08] bg-white shadow-card-soft"
    >
      {/* Subject + label */}
      <div className="flex items-start justify-between gap-3 px-6 pt-5">
        <h2 className="text-[19px] font-normal leading-snug tracking-tight text-ink-900">{email.subject}</h2>
        <div className="mt-1 flex shrink-0 items-center gap-2.5">
          <Badge tone="ok">Sent</Badge>
          <span className="hidden text-[12px] text-ink-400 sm:inline">just now</span>
          <div className="hidden items-center gap-2.5 text-ink-300 sm:flex">
            <Star size={15} />
            <CornerUpLeft size={15} />
            <MoreVertical size={15} />
          </div>
        </div>
      </div>

      {/* Sender row — Gmail header */}
      <div className="flex items-start gap-3.5 px-6 py-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-violet text-[15px] font-semibold text-white">
          F
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-1.5">
            <span className="text-[14px] font-semibold text-ink-900">FOREMAN</span>
            <span className="text-[12.5px] text-ink-400">&lt;audit@foreman.ops&gt;</span>
          </div>
          <button className="mt-0.5 flex items-center gap-1 text-[12.5px] text-ink-500">
            to {email.to}
            <ChevronDown size={14} className="text-ink-400" />
          </button>
        </div>
      </div>

      {/* Body — exactly the email that was sent, by section */}
      <div className="space-y-3 px-6 pb-5 pl-[4.6rem] pr-6">
        {parsed.intro && <p className="text-[13.5px] leading-relaxed text-ink-700">{parsed.intro}</p>}
        {parsed.sections.length > 0 ? (
          <div className="space-y-2.5">
            {parsed.sections.map((s) => {
              const hex = TONE_HEX[s.tone]
              return (
                <div
                  key={s.label}
                  className="rounded-r-md border-l-[3px] bg-ink-900/[0.018] py-2 pl-3.5 pr-3.5"
                  style={{ borderColor: hex }}
                >
                  <div
                    className="text-[10.5px] font-semibold uppercase tracking-[0.12em]"
                    style={{ color: hex }}
                  >
                    {s.label}
                  </div>
                  <div className="mt-1 text-[13px] leading-relaxed text-ink-700">{s.text}</div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="whitespace-pre-line text-[13.5px] leading-relaxed text-ink-700">{email.body}</div>
        )}
        {parsed.footer && <p className="pt-0.5 text-[12px] italic text-ink-400">{parsed.footer}</p>}
      </div>

      {/* Attachments — Gmail cards */}
      {attachments.length > 0 && (
        <div className="px-6 pb-6 pl-[4.6rem]">
          <div className="mb-2.5 flex items-center gap-1.5 text-[12.5px] text-ink-500">
            <Paperclip size={13} />
            {attachments.length} attachment{attachments.length === 1 ? '' : 's'}
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            {attachments.slice(0, 3).map((att) => (
              <GmailAttachment key={att} name={att} />
            ))}
            {attachments.length > 3 && (
              <span className="flex h-[58px] w-[52px] items-center justify-center rounded-lg border border-ink-900/[0.14] bg-paper-50 text-[12.5px] font-semibold text-ink-500">
                +{attachments.length - 3}
              </span>
            )}
          </div>
          <button className="mt-3.5 inline-flex items-center gap-1.5 rounded-full border border-ink-900/[0.14] px-4 py-1.5 text-[12.5px] font-medium text-ink-700 transition-colors hover:bg-paper-50">
            View all attachments
            <CornerUpRight size={13} className="text-ink-400" />
          </button>
        </div>
      )}

      {/* Reply bar */}
      <div className="flex items-center gap-2 border-t border-ink-900/[0.06] px-6 py-3">
        <button className="inline-flex items-center gap-2 rounded-full border border-ink-900/[0.14] px-4 py-1.5 text-[13px] font-medium text-ink-700 transition-colors hover:bg-paper-50">
          <CornerUpLeft size={14} /> Reply
        </button>
        <button className="inline-flex items-center gap-2 rounded-full border border-ink-900/[0.14] px-4 py-1.5 text-[13px] font-medium text-ink-700 transition-colors hover:bg-paper-50">
          <CornerUpRight size={14} /> Forward
        </button>
      </div>
    </motion.div>
  )
}

// ── Audit pack generated — folder + stamp graphic + three green checks ───────
function AuditPackCard() {
  const checks = ['Cited evidence', 'Attachments included', 'Email dispatched']
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="flex flex-col justify-between gap-4 overflow-hidden rounded-2xl border border-ink-900/[0.07] bg-gradient-to-br from-paper-50 via-white to-white p-5 shadow-card-soft"
    >
      <div className="flex items-start gap-3">
        <img
          src={auditPack}
          alt="A stamped audit-pack folder"
          className="h-16 w-16 shrink-0 object-contain mix-blend-multiply"
        />
        <h3 className="mt-1 text-[14.5px] font-semibold leading-snug tracking-tight text-ink-900">
          Audit pack generated
        </h3>
      </div>
      <ul className="space-y-2.5">
        {checks.map((label) => (
          <li key={label} className="flex items-center gap-2.5 text-[12.5px] font-medium text-ink-700">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ok/12 text-ok">
              <Check size={13} strokeWidth={2.6} />
            </span>
            {label}
          </li>
        ))}
      </ul>
    </motion.div>
  )
}

function FeedbackRow({ c }: { c: CaseView }) {
  const submit = useStore((s) => s.submitFeedback)
  const [verdict, setVerdict] = useState<'up' | 'down' | null>(c.feedback ?? null)
  const [phase, setPhase] = useState<'idle' | 'processing' | 'done'>(c.feedback ? 'done' : 'idle')
  const [runId, setRunId] = useState(0)

  // The gate is always clickable. Picking a verdict kicks off the write-back
  // sequence (processed in real-time), then reveals what it did. Also nudges the
  // store so the thumb persists — best-effort, a live case has no replay.
  const pick = (v: 'up' | 'down') => {
    if (phase === 'processing') return
    setVerdict(v)
    setPhase('processing')
    setRunId((r) => r + 1)
    try {
      submit(v)
    } catch {
      /* live case (no replay engine): the reveal below is the source of truth */
    }
  }

  const blurb =
    phase === 'processing'
      ? verdict === 'up'
        ? 'Writing the learning back to FOREMAN’s memory — recording the root in the Knowledge Graph and promoting the Skill…'
        : 'Logging this case as a counter-example…'
      : verdict === 'up'
        ? 'Approved — this case is now part of FOREMAN’s memory: the root cause was recorded in the Knowledge Graph and the repair was written back as a reusable Skill.'
        : verdict === 'down'
          ? 'Logged as a counter-example — nothing was written to the Knowledge Graph or the skill library.'
          : 'Your call: approve to learn from this case — the Knowledge Graph records the root and the repair becomes a reusable Skill. Reject to keep it as a counter-example.'

  return (
    <div className={clsx('panel overflow-hidden transition-shadow', !verdict && 'shadow-glow ring-1 ring-brand-400/40')}>
      <div className="grid grid-cols-1 items-stretch lg:grid-cols-[300px_1fr]">
        {/* Left — the human-feedback-loop graphic */}
        <div className="relative hidden items-center justify-center overflow-hidden border-r border-ink-900/[0.06] bg-mesh-pastel-soft p-7 lg:flex">
          <img
            src={feedbackLoop}
            alt="Human feedback loop — a thumbs-up or thumbs-down feeds the learning"
            className="relative w-full max-w-[220px] mix-blend-multiply drop-shadow-[0_24px_48px_rgba(20,23,28,0.14)]"
          />
        </div>

        {/* Right — heading, prompt, the interactive gate */}
        <div className="p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-brand-600">
                Human feedback
              </div>
              <h3 className="mt-1 font-display text-xl font-bold tracking-tightest text-ink-900">
                The learning gate
              </h3>
            </div>
            {phase === 'processing' ? (
              <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-brand-500/10 px-2.5 py-1 text-[11px] font-semibold text-brand-700">
                <Loader2 size={11} className="animate-spin" />
                Processing
              </span>
            ) : verdict === 'up' ? (
              <Badge tone="ok">Learned</Badge>
            ) : verdict === 'down' ? (
              <Badge tone="danger">Not learned</Badge>
            ) : (
              <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-brand-500/10 px-2.5 py-1 text-[11px] font-semibold text-brand-700">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-500 opacity-70" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-500" />
                </span>
                Your call
              </span>
            )}
          </div>

          <p className="mt-2.5 max-w-md text-[13px] leading-relaxed text-ink-500">{blurb}</p>

          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FeedbackButton
              active={verdict === 'up'}
              tone="ok"
              icon={<ThumbsUp size={20} />}
              label="Learn from this case"
              activeLabel={phase === 'processing' ? 'Writing back…' : 'Captured — skill written'}
              dim={verdict === 'down'}
              onVote={() => pick('up')}
            />
            <FeedbackButton
              active={verdict === 'down'}
              tone="danger"
              icon={<ThumbsDown size={20} />}
              label="Don't learn — counter-example"
              activeLabel={phase === 'processing' ? 'Logging…' : 'Logged — kept as a counter-example'}
              dim={verdict === 'up'}
              onVote={() => pick('down')}
            />
          </div>

          {/* the learning loop — each section writes back in real-time (loader →
              done) so the skill library + Knowledge Graph both read as live */}
          <AnimatePresence initial={false} mode="wait">
            {verdict === 'up' && phase !== 'idle' ? (
              <LearningApplied key={`learn-${runId}`} instant={phase === 'done'} onDone={() => setPhase('done')} />
            ) : verdict === 'down' && phase !== 'idle' ? (
              <CounterExample key={`counter-${runId}`} instant={phase === 'done'} onDone={() => setPhase('done')} />
            ) : null}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

function FeedbackButton({
  active,
  tone,
  icon,
  label,
  activeLabel,
  dim,
  onVote,
}: {
  active: boolean
  tone: 'ok' | 'danger'
  icon: React.ReactNode
  label: string
  activeLabel: string
  dim: boolean
  onVote: () => void
}) {
  const hex = tone === 'ok' ? '#1aa251' : '#e23b3b'
  return (
    <button
      type="button"
      onClick={onVote}
      className={clsx(
        'flex items-center gap-3.5 rounded-xl border p-4 text-left transition-all',
        active
          ? 'border-transparent'
          : clsx(
              'cursor-pointer border-ink-900/[0.10] bg-white hover:-translate-y-0.5 hover:shadow-card-light',
              dim && 'opacity-50',
            ),
      )}
      style={
        active
          ? { background: `${hex}1f`, border: `1px solid ${hex}44`, boxShadow: `0 0 24px -8px ${hex}` }
          : undefined
      }
    >
      <span
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
        style={active ? { background: `${hex}26`, color: hex } : { background: `${hex}14`, color: hex }}
      >
        {icon}
      </span>
      <span className="min-w-0">
        <span className={clsx('block text-[13px] font-semibold', active ? 'text-ink-900' : 'text-ink-700')}>
          {label}
        </span>
        {active && (
          <span className="mt-0.5 block text-[11.5px] font-medium" style={{ color: hex }}>
            {activeLabel}
          </span>
        )}
      </span>
    </button>
  )
}

// ── The learning loop — each section writes back in real-time (loader → done) ───
type LearnCard = {
  key: string
  icon: React.ReactNode
  tone: Tone
  title: string
  working: string
  pending: string
  id: string
  lines: string[]
  pills: string[]
  startAt: number
  doneAt: number
}

type LearnStatus = 'pending' | 'processing' | 'done'

function LearningApplied({ onDone, instant }: { onDone: () => void; instant?: boolean }) {
  // Sequential write-back: the Skill is written first (~10s), THEN the Knowledge
  // Graph is updated (~10s) — total ~20s. The graph card waits (pending) until the
  // Skill is done, so the two never process at the same time.
  const cards: LearnCard[] = [
    {
      key: 'skill',
      icon: <Sparkles size={14} />,
      tone: 'ok',
      title: 'Skill written to the library',
      working: 'Writing + promoting the Skill…',
      pending: 'Queued…',
      id: 'SK-PV-MC4-CROSSMATE',
      lines: [
        'Diagnosis · loose / cross-mated MC4 crimp → high-resistance joint → thermal runaway',
        'Recipe · isolate + LOTO → cut out connector → re-terminate matched genuine pair → IR scan',
      ],
      pills: ['Candidate → Trusted', 'approvals 3 → 4', 'PV · MC4'],
      startAt: 0,
      doneAt: 10000,
    },
    {
      key: 'graph',
      icon: <Network size={14} />,
      tone: 'info',
      title: 'Knowledge Graph updated',
      working: 'Recording the root + linking the affected strings…',
      pending: 'Waiting for the Skill to be written…',
      id: 'MC4-LOT-X',
      lines: [
        'Root cause recorded · cross-mated connector lot linked to 3 affected strings',
        'Skill linked to equipment_class = PV-MC4 for future hard-gate matches',
      ],
      pills: ['+1 root node', '+3 confirmed edges', 'skill ↔ match-key'],
      startAt: 10000,
      doneAt: 20000,
    },
  ]
  const [status, setStatus] = useState<Record<string, LearnStatus>>(() =>
    instant
      ? Object.fromEntries(cards.map((c) => [c.key, 'done' as LearnStatus]))
      : Object.fromEntries(cards.map((c) => [c.key, (c.startAt === 0 ? 'processing' : 'pending') as LearnStatus])),
  )
  useEffect(() => {
    if (instant) return
    const timers: ReturnType<typeof setTimeout>[] = []
    cards.forEach((c) => {
      if (c.startAt > 0)
        timers.push(setTimeout(() => setStatus((p) => ({ ...p, [c.key]: 'processing' })), c.startAt))
      timers.push(setTimeout(() => setStatus((p) => ({ ...p, [c.key]: 'done' })), c.doneAt))
    })
    const last = Math.max(...cards.map((c) => c.doneAt))
    const fin = setTimeout(onDone, last + 300)
    return () => {
      timers.forEach(clearTimeout)
      clearTimeout(fin)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const allDone = cards.every((c) => status[c.key] === 'done')
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-5 rounded-xl border border-ok/25 bg-ok/[0.04] p-4">
        <div className="flex items-center gap-2 text-[12px] font-semibold text-ok">
          {allDone ? <BadgeCheck size={15} /> : <Loader2 size={15} className="animate-spin" />}
          {allDone
            ? 'Learning applied — written back to FOREMAN’s memory'
            : 'Writing the learning back to FOREMAN’s memory…'}
        </div>
        <div className="mt-3.5 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {cards.map((s) => {
            const hex = TONE_HEX[s.tone]
            const st = status[s.key]
            return (
              <div
                key={s.key}
                className={clsx(
                  'rounded-lg border border-ink-900/[0.08] bg-white p-3.5 transition-opacity',
                  st === 'pending' && 'opacity-60',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-2 text-[12.5px] font-semibold text-ink-900">
                    <span
                      className="flex h-6 w-6 items-center justify-center rounded-md"
                      style={{ background: `${hex}14`, color: hex }}
                    >
                      {s.icon}
                    </span>
                    {s.title}
                  </span>
                  {st === 'done' ? (
                    <Check size={15} className="text-ok" />
                  ) : st === 'processing' ? (
                    <Loader2 size={15} className="animate-spin" style={{ color: hex }} />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-ink-300" />
                  )}
                </div>
                {st === 'done' ? (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <div className="mt-1.5 font-mono text-[11px] text-ink-500">{s.id}</div>
                    <ul className="mt-2 space-y-1">
                      {s.lines.map((l) => (
                        <li key={l} className="text-[11.5px] leading-relaxed text-ink-600">
                          {l}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                      {s.pills.map((p) => (
                        <span
                          key={p}
                          className="rounded-md border px-2 py-0.5 font-mono text-[10px]"
                          style={{ borderColor: `${hex}33`, background: `${hex}0d`, color: hex }}
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </motion.div>
                ) : st === 'processing' ? (
                  <div className="mt-2.5 flex items-center gap-2 text-[11.5px] text-ink-400">
                    <span className="inline-flex gap-1">
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-300 [animation-delay:0ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-300 [animation-delay:120ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-300 [animation-delay:240ms]" />
                    </span>
                    {s.working}
                  </div>
                ) : (
                  <div className="mt-2.5 text-[11.5px] text-ink-400">{s.pending}</div>
                )}
              </div>
            )
          })}
        </div>
        <div className="mt-3 flex items-center gap-2 text-[11.5px] text-ink-500">
          <GitBranch size={13} className="text-ink-400" />
          {allDone
            ? 'The next MC4 case with this signature auto-matches this Skill on the hard gate.'
            : 'Linking this learning so the next matching case resolves instantly…'}
        </div>
      </div>
    </motion.div>
  )
}

function CounterExample({ onDone, instant }: { onDone: () => void; instant?: boolean }) {
  const [done, setDone] = useState(!!instant)
  useEffect(() => {
    if (instant) return
    const t = setTimeout(() => setDone(true), 2500)
    const fin = setTimeout(onDone, 2800)
    return () => {
      clearTimeout(t)
      clearTimeout(fin)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-5 rounded-xl border border-danger/25 bg-danger/[0.04] p-4">
        <div className="flex items-center gap-2 text-[12px] font-semibold text-danger">
          {done ? <ThumbsDown size={14} /> : <Loader2 size={14} className="animate-spin" />}
          {done ? 'Kept as a counter-example' : 'Logging counter-example…'}
        </div>
        {done && (
          <p className="mt-2 text-[11.5px] leading-relaxed text-ink-600">
            Nothing was written to the Knowledge Graph or the skill library. This case is stored as a
            negative example so FOREMAN won’t learn the wrong pattern from it.
          </p>
        )}
      </div>
    </motion.div>
  )
}
