import { useEffect, useRef, useState, type MouseEvent, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  CheckCircle2,
  Download,
  Globe,
  Lock,
  Pause,
  Phone,
  Play,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { useStore } from '../../store/store'
import { Empty } from '../../components/ui'
import { clsx } from '../../lib/format'
import { resolveMediaUrl } from '../../config'
import phoneCall from '../../assets/phone-call.jpg'
import type { CallState, CaseView } from '../../types'

// Presentation-only chrome constants (pure labels / demo numbers).
const CALL_ID = 'CA-9f25d8e8'
const AI_SUGGESTIONS = ['Isolate string guidance', 'Connector requalification SOP', 'Fleet audit checklist']

// Build a snake_case id from a role label, purely for display chrome.
function roleSlug(role?: string) {
  return (role || 'site_epc_manager').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
}

export function CallsTab() {
  const c = useStore((s) => (s.activeCaseId ? s.cases[s.activeCaseId] : null))
  const navigate = useNavigate()
  // Live voice data, straight from the case (streamed from the voice agent).
  const call: CallState = c?.call ?? { status: 'idle', lines: [] }
  // The recording only exists once call.audioUrl is set (delivered after the call).
  const audioSrc = resolveMediaUrl(call.audioUrl)
  const measured = useAudioDuration(audioSrc)
  const duration = measured || call.audioDuration || 0
  // The case has escalated (or is high-risk) but the call hasn't streamed in yet.
  const forcePending =
    call.status === 'idle' &&
    !!c &&
    (c.reachedStages.includes('escalate') || (c.risk_score != null && c.risk_score >= 0.7))

  if (!c) return <Empty icon={<Phone size={22} />} text="No active case yet." />

  const hasTranscript = call.lines.length > 0

  return (
    <div className="space-y-6">
      <CallStage c={c} call={call} forcePending={forcePending} />

      {(hasTranscript || call.decision) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-7">{hasTranscript && <Transcript call={call} />}</div>
          <div className="lg:col-span-5">
            {call.decision ? (
              <DecisionCard c={c} call={call} audioSrc={audioSrc} duration={duration} />
            ) : (
              <DecisionPending />
            )}
          </div>
        </div>
      )}

      <SuggestionsBar onOpen={() => navigate('/app/console')} />
    </div>
  )
}

// Read a media file's real duration (seconds) off its metadata.
function useAudioDuration(src?: string): number {
  const [d, setD] = useState(0)
  useEffect(() => {
    if (!src) {
      setD(0)
      return
    }
    const a = new Audio()
    a.preload = 'metadata'
    const on = () => { if (isFinite(a.duration)) setD(a.duration) }
    a.addEventListener('loadedmetadata', on)
    a.src = src
    return () => { a.removeEventListener('loadedmetadata', on); a.src = '' }
  }, [src])
  return d
}

function fmtDur(sec: number): string {
  if (!sec || !isFinite(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

// ── Cinematic call hero (phone-wave image + adaptive state) ─────────────────
function CallStage({
  c,
  call,
  forcePending,
}: {
  c: CaseView
  call: CallState
  forcePending?: boolean
}) {
  const dialing = call.status === 'dialing'
  const connected = call.status === 'connected'
  const ended = call.status === 'ended'
  const idle = call.status === 'idle'
  const risk = c.risk_score
  const pending = forcePending || (idle && risk != null && risk >= 0.7)
  const resolved = !forcePending && idle && risk != null && risk < 0.7
  const live = dialing || connected

  const title = ended
    ? 'Authorised by voice'
    : connected
      ? 'Connected'
      : dialing
        ? 'Dialing the approver…'
        : pending
          ? 'Escalation pending'
          : resolved
            ? 'No call needed'
            : 'Standing by'

  const showMeta = ended || connected

  return (
    <div className="panel relative overflow-hidden rounded-2xl">
      <div className="relative min-h-[280px] w-full overflow-hidden bg-carbon-950 sm:min-h-[300px]">
        {/* phone-wave image, right side, faded into the dark stage */}
        <img
          src={phoneCall}
          alt=""
          className="absolute right-0 top-0 h-full w-[62%] object-cover"
          style={{
            maskImage: 'linear-gradient(to right, transparent 0%, #000 40%)',
            WebkitMaskImage: 'linear-gradient(to right, transparent 0%, #000 40%)',
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-carbon-950 via-carbon-950/78 to-carbon-950/5" />
        <div className="absolute inset-0 bg-gradient-to-t from-carbon-950/65 to-transparent" />

        {/* purple/blue waveform glow */}
        <div
          className={clsx(
            'pointer-events-none absolute right-[20%] top-1/2 h-48 w-80 -translate-y-1/2 rounded-full blur-3xl',
            live && 'animate-pulse',
          )}
          style={{
            background: live
              ? connected
                ? 'rgba(80,180,255,0.34)'
                : 'rgba(245,166,35,0.30)'
              : 'radial-gradient(closest-side, rgba(124,92,219,0.42), rgba(47,109,255,0.22), transparent)',
          }}
        />

        {/* content */}
        <div className="relative flex min-h-[280px] flex-col justify-center p-7 sm:min-h-[300px] sm:p-9">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-violet-300/80">
            <Phone size={13} /> Escalation · Twilio Voice
          </div>

          <div className="mt-3.5 flex flex-wrap items-center gap-3">
            <h2 className="font-serif text-[34px] font-normal leading-[1.02] tracking-[-0.01em] text-white sm:text-[42px]">
              {title}
            </h2>
            <CallPill status={call.status} pending={pending} resolved={resolved} />
          </div>

          <div className="mt-3 max-w-md text-[13.5px] leading-relaxed text-white/75">
            {idle ? (
              pending ? (
                'Awaiting Action Center approval — once the human approves, FOREMAN places the escalation call to the approver.'
              ) : resolved ? (
                <>Risk <span className="font-mono font-semibold text-white">{risk}</span> is below the 0.70 threshold — auto-resolved and logged.</>
              ) : (
                'A call only happens when the risk score crosses 0.70.'
              )
            ) : (
              <span className="inline-flex items-center gap-2">
                <span className="text-white/50">to</span>
                <span className="font-semibold text-white">{call.toRole}</span>
                <span className="text-white/30">·</span>
                <span className="font-mono text-white/80">{call.to}</span>
              </span>
            )}
          </div>

          {showMeta && (
            <div className="mt-6 flex flex-wrap items-center gap-x-7 gap-y-2 text-[12.5px] text-white/70">
              <span className="inline-flex items-center gap-2">
                <Globe size={14} className="text-white/45" />
                <span className="text-white/50">Language:</span>
                <span className="text-white/90">English (India)</span>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function CallPill({
  status,
  pending,
  resolved,
}: {
  status: CallState['status']
  pending?: boolean
  resolved?: boolean
}) {
  if (status === 'dialing') return <DarkPill hex="#f5a623" pulse>Dialing…</DarkPill>
  if (status === 'connected') return <DarkPill hex="#34c759" live>Connected</DarkPill>
  if (status === 'ended') return <DarkPill hex="#34c759">Authorised</DarkPill>
  if (pending) return <DarkPill hex="#f5a623" pulse>Escalation pending</DarkPill>
  if (resolved) return <DarkPill hex="#34c759">Auto-resolved</DarkPill>
  return <DarkPill hex="#9aa1aa">Idle</DarkPill>
}

function DarkPill({ children, hex, pulse, live }: { children: ReactNode; hex: string; pulse?: boolean; live?: boolean }) {
  return (
    <span
      className={clsx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] font-semibold', pulse && 'animate-pulse')}
      style={{ background: `${hex}22`, color: hex, border: `1px solid ${hex}44` }}
    >
      <span className="relative flex h-2 w-2">
        {live && <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-70" style={{ background: hex }} />}
        <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: hex }} />
      </span>
      {children}
    </span>
  )
}

// ── Small dark agent/robot avatar for FOREMAN bubbles ───────────────────────
function ForemanAvatar() {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-carbon-950 text-brand-300 ring-1 ring-inset ring-white/10">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4" y="8" width="16" height="11" rx="3" />
        <path d="M12 5v3" />
        <circle cx="12" cy="4" r="1.4" fill="currentColor" stroke="none" />
        <circle cx="9" cy="13" r="1.1" fill="currentColor" stroke="none" />
        <circle cx="15" cy="13" r="1.1" fill="currentColor" stroke="none" />
        <path d="M9.5 16h5" />
      </svg>
    </span>
  )
}

function ManagerAvatar() {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-ink-900/[0.05] text-ink-400 ring-1 ring-inset ring-ink-900/[0.06]">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="8" r="3.4" />
        <path d="M5 19c0-3.3 3.1-5 7-5s7 1.7 7 5" />
      </svg>
    </span>
  )
}

// ── Transcript ───────────────────────────────────────────────────────────────
function Transcript({ call }: { call: CallState }) {
  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-5 pt-5">
        <div className="flex items-center gap-2 text-[15px] font-semibold tracking-tight text-ink-900">
          <Phone size={15} className="text-brand-500" /> Live transcript
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-ok/25 bg-ok/[0.08] px-2.5 py-1 text-[11px] font-semibold text-ok">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ok opacity-70" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-ok" />
          </span>
          Real-time · Secure
        </span>
      </div>

      <div className="space-y-4 px-5 py-5">
        <AnimatePresence initial>
          {call.lines.map((line, i) => {
            const foreman = line.speaker === 'foreman'
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                className={clsx('flex items-start gap-2.5', foreman ? 'justify-start' : 'flex-row-reverse justify-start')}
              >
                {foreman ? <ForemanAvatar /> : <ManagerAvatar />}
                <div
                  className={clsx(
                    'max-w-[80%] rounded-2xl border px-3.5 py-2.5',
                    foreman
                      ? 'rounded-tl-sm border-brand-400/20 bg-brand-500/[0.06]'
                      : 'rounded-tr-sm border-ink-900/[0.07] bg-ink-900/[0.035]',
                  )}
                >
                  <div
                    className={clsx(
                      'mb-1 flex items-center gap-2 font-mono text-[10px] font-semibold uppercase tracking-[0.14em]',
                      foreman ? 'text-brand-600/85' : 'justify-end text-ink-400',
                    )}
                  >
                    {foreman ? 'FOREMAN' : 'MANAGER'}
                  </div>
                  <div className={clsx('text-[13px] leading-relaxed text-ink-900', !foreman && 'text-right')}>{line.text}</div>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>

      <div className="flex items-center justify-center gap-3 border-t border-ink-900/[0.06] bg-paper-50/60 px-5 py-3">
        <WaveDots className="text-ink-300" />
        <span className="text-[11.5px] font-medium text-brand-500">+ Live transcription</span>
        <WaveDots className="text-ink-300" />
      </div>
    </div>
  )
}

// Faint dotted equalizer used in the transcription footer.
function WaveDots({ className }: { className?: string }) {
  return (
    <div className={clsx('flex items-end gap-[3px]', className)} aria-hidden>
      {[5, 9, 4, 11, 6, 8, 4, 10, 5, 7, 4, 9].map((h, i) => (
        <span key={i} className="w-[2px] rounded-full bg-current opacity-50" style={{ height: h }} />
      ))}
    </div>
  )
}

// Shown after the call cuts while Twilio is still delivering the recording.
function RecordingPending() {
  return (
    <div className="mt-4 flex items-center gap-3 rounded-xl border border-ink-900/[0.07] bg-paper-50/70 px-3.5 py-3">
      <span className="relative flex h-2.5 w-2.5 shrink-0">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ok opacity-60" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-ok" />
      </span>
      <span className="text-[12px] font-medium text-ink-500">Processing call recording…</span>
    </div>
  )
}

// Functional recording player — green waveform fills with playback progress.
const WAVE_BARS = Array.from({ length: 56 }, (_, i) =>
  4 + Math.round(Math.abs(Math.sin(i * 0.7) * Math.cos(i * 0.31)) * 22),
)

function RecordingPlayer({ src, duration }: { src?: string; duration: number }) {
  const ref = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [cur, setCur] = useState(0)
  const dur = duration || ref.current?.duration || 0
  const progress = dur ? Math.min(1, cur / dur) : 0

  const toggle = () => {
    const a = ref.current
    if (!a) return
    if (a.paused) {
      a.play()
      setPlaying(true)
    } else {
      a.pause()
      setPlaying(false)
    }
  }

  const seek = (e: MouseEvent<HTMLDivElement>) => {
    const a = ref.current
    if (!a || !dur) return
    const r = e.currentTarget.getBoundingClientRect()
    a.currentTime = ((e.clientX - r.left) / r.width) * dur
    setCur(a.currentTime)
  }

  return (
    <div className="mt-4 flex items-center gap-3 rounded-xl border border-ink-900/[0.07] bg-paper-50/70 px-3 py-2.5">
      <audio
        ref={ref}
        src={src}
        preload="metadata"
        onTimeUpdate={(e) => setCur(e.currentTarget.currentTime)}
        onEnded={() => {
          setPlaying(false)
          setCur(0)
        }}
      />
      <button
        type="button"
        onClick={toggle}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ok text-white shadow-[0_2px_8px_rgba(52,199,89,0.4)] transition-transform hover:scale-105"
        aria-label={playing ? 'Pause recording' : 'Play recording'}
      >
        {playing ? <Pause size={15} className="fill-current" /> : <Play size={15} className="ml-0.5 fill-current" />}
      </button>
      <div className="flex h-9 flex-1 cursor-pointer items-center gap-[2.5px]" onClick={seek}>
        {WAVE_BARS.map((h, i) => {
          const on = i / WAVE_BARS.length <= progress
          return (
            <span
              key={i}
              className="w-[2.5px] rounded-full transition-colors"
              style={{ height: h, background: on ? '#34c759' : 'rgba(52,199,89,0.26)' }}
            />
          )
        })}
      </div>
      <span className="shrink-0 font-mono text-[12px] font-medium text-ink-500">
        {playing || cur ? fmtDur(cur) : fmtDur(dur)}
      </span>
      {src ? (
        <a
          href={src}
          download
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-ink-900/[0.1] bg-white text-ink-500 transition-colors hover:text-ink-900"
          aria-label="Download recording"
        >
          <Download size={14} />
        </a>
      ) : null}
    </div>
  )
}

// ── Decision ─────────────────────────────────────────────────────────────────
function DecisionPending() {
  return (
    <div className="panel flex h-full min-h-[160px] items-center justify-center p-5">
      <Empty icon={<ShieldCheck size={20} />} text="Awaiting the decision on the line…" />
    </div>
  )
}

function DecisionCard({
  c,
  call,
  audioSrc,
  duration,
}: {
  c: CaseView
  call: CallState
  audioSrc?: string
  duration: number
}) {
  const d = call.decision
  if (!d) return null
  const slug = roleSlug(call.toRole)

  const meta: { label: string; value: ReactNode; mono?: boolean }[] = [
    { label: 'Case ID', value: c.case_id, mono: true },
    { label: 'Asset', value: c.site_id, mono: true },
    { label: 'Channel', value: 'Twilio Voice' },
    { label: 'Region', value: 'IN · DEL' },
    { label: 'Call ID', value: CALL_ID, mono: true },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="panel p-5"
    >
      {/* header */}
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-ok/12 text-ok ring-1 ring-inset ring-ok/25">
          <CheckCircle2 size={22} />
        </div>
        <div>
          <div className="font-display text-lg font-bold tracking-tightest text-ink-900">Authorised by voice</div>
          <div className="mt-0.5 font-mono text-[11.5px] text-ink-500">{slug}</div>
        </div>
      </div>

      {/* recording — appears once Twilio delivers it (a few seconds after the call) */}
      {audioSrc ? <RecordingPlayer src={audioSrc} duration={duration} /> : <RecordingPending />}

      {/* authorised actions */}
      <div className="mt-5">
        <div className="text-[12px] font-semibold tracking-tight text-ink-900">Authorised actions</div>
        <div className="mt-2.5 flex flex-wrap gap-2">
          {d.actions.map((a) => (
            <span
              key={a}
              className="inline-flex items-center gap-1.5 rounded-full border border-ok/30 bg-ok/[0.08] px-2.5 py-1 font-mono text-[11.5px] font-semibold text-ok"
            >
              <CheckCircle2 size={11} />
              {a}
            </span>
          ))}
        </div>
      </div>

      {/* verified caller + call security */}
      <div className="mt-5 grid grid-cols-1 gap-3 border-t border-ink-900/[0.06] pt-5 sm:grid-cols-2">
        <InfoBlock
          icon={<ShieldCheck size={16} />}
          label="Verified caller"
          title={call.toRole || 'Site EPC Manager'}
          sub={call.to || '+91-98xxxxxxx'}
          mono
          badge={
            <span className="inline-flex items-center gap-1 rounded-full border border-ok/30 bg-ok/[0.08] px-2 py-0.5 text-[10px] font-semibold text-ok">
              <span className="h-1.5 w-1.5 rounded-full bg-ok" /> Verified
            </span>
          }
        />
        <InfoBlock
          icon={<Lock size={16} />}
          label="Call security"
          title="End-to-end encrypted"
          sub="Twilio Voice · TLS 1.3"
        />
      </div>

      {/* call metadata */}
      <div className="mt-5 border-t border-ink-900/[0.06] pt-5">
        <div className="text-[12px] font-semibold tracking-tight text-ink-900">Call metadata</div>
        <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-4 sm:grid-cols-5">
          {meta.map((m) => (
            <div key={m.label} className="min-w-0">
              <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-ink-400">{m.label}</div>
              <div className={clsx('mt-1 truncate text-[12.5px] text-ink-900', m.mono ? 'font-mono' : 'font-medium')}>
                {m.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}

function InfoBlock({
  icon,
  label,
  title,
  sub,
  badge,
  mono,
}: {
  icon: ReactNode
  label: string
  title: ReactNode
  sub: ReactNode
  badge?: ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-ink-900/[0.06] bg-paper-50/60 p-3">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ink-900/[0.05] text-ink-500">
        {icon}
      </span>
      <div className="min-w-0">
        <div className="text-[11px] font-medium text-ink-400">{label}</div>
        <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[12.5px] font-semibold text-ink-900">
          {title}
          {badge}
        </div>
        <div className={clsx('mt-0.5 truncate text-[11.5px] text-ink-500', mono && 'font-mono')}>{sub}</div>
      </div>
    </div>
  )
}

// ── AI suggestions footer bar ────────────────────────────────────────────────
function SuggestionsBar({ onOpen }: { onOpen: () => void }) {
  return (
    <div className="panel flex flex-wrap items-center justify-between gap-4 px-5 py-3.5">
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-500/10 text-brand-500 ring-1 ring-inset ring-brand-500/15">
          <Sparkles size={15} />
        </span>
        <span className="text-[12.5px] font-semibold tracking-tight text-ink-700">AI suggestions (context aware)</span>
        <div className="flex flex-wrap items-center gap-2">
          {AI_SUGGESTIONS.map((s) => (
            <span
              key={s}
              className="inline-flex items-center rounded-full border border-ink-900/[0.1] bg-white px-3 py-1 text-[11.5px] font-medium text-ink-600 transition-colors hover:border-ink-900/25 hover:text-ink-900"
            >
              {s}
            </span>
          ))}
        </div>
      </div>
      <button
        type="button"
        onClick={onOpen}
        className="inline-flex items-center gap-1.5 rounded-lg bg-brand-500 px-3.5 py-1.5 text-[12px] font-semibold tracking-tight text-white shadow-[0_1px_2px_rgba(47,109,255,0.3)] transition-colors hover:bg-brand-600"
      >
        Open Case in Console <ArrowRight size={14} />
      </button>
    </div>
  )
}
