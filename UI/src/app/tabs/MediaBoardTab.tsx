import { useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import { motion } from 'framer-motion'
import {
  AudioLines,
  Clock,
  Download,
  ExternalLink,
  FileText,
  Image as ImageIcon,
  Images,
  Maximize2,
  MapPin,
  MessageCircle,
  MessageSquareText,
  Pause,
  Play,
  Sparkles,
  User,
  Video,
  ZoomIn,
} from 'lucide-react'
import { useStore } from '../../store/store'
import { Empty, TabHeader } from '../../components/ui'
import { clsx } from '../../lib/format'
import {
  REAL_SOP_NAME,
  REAL_SOP_URL,
  REAL_VIDEO_URL,
  isMediaMessage,
  isSopMessage,
} from '../../lib/livePresentation'
import type { CaseView, ChatMessage, MediaItem } from '../../types'

export function MediaBoardTab() {
  const c = useStore((s) => (s.activeCaseId ? s.cases[s.activeCaseId] : null))
  if (!c) return <Empty icon={<Images size={26} />} text="No active case — press play in the top bar." />

  const media = c.media ?? []
  const videos = media.filter((m) => m.kind === 'video')
  const images = media.filter((m) => m.kind === 'image')
  const audios = media.filter((m) => m.kind === 'audio')
  const docs = media.filter((m) => m.kind === 'document')
  // Prefer the worker's real text report over the "(sent a photo / video)" placeholder.
  const report =
    c.chat.find((m) => m.from === 'worker' && !isMediaMessage(m.text) && m.text.trim().length > 0) ??
    c.chat.find((m) => m.from === 'worker')
  const hasSop = videos.length > 0 || c.chat.some((m) => isSopMessage(m.from, m.text))

  const counts: { icon: LucideIcon; value: number; label: string }[] = [
    { icon: Video, value: videos.length, label: 'Video' },
    { icon: Images, value: images.length, label: images.length === 1 ? 'Image' : 'Images' },
    { icon: AudioLines, value: audios.length, label: 'Audio' },
    { icon: FileText, value: docs.length, label: 'Document' },
  ]

  return (
    <div className="space-y-7">
      <TabHeader
        eyebrow="Multimodal capture"
        title="MediaBoard"
        sub="Everything captured on the channel — video, images, audio and documents, rendered in one view."
        right={
          media.length > 0 ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {counts.map((k) => (
                <CountCard key={k.label} icon={k.icon} value={k.value} label={k.label} />
              ))}
            </div>
          ) : undefined
        }
      />

      <SourceStrip c={c} />

      {media.length === 0 ? (
        <div className="panel">
          <Empty icon={<Images size={24} />} text="No media yet — it arrives at Intake when the engineer sends it." />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
            {report && (
              <div className="lg:col-span-7">
                <TextReport msg={report} name={c.worker_name} />
              </div>
            )}
            {c.skillHit && (
              <div className={clsx(report ? 'lg:col-span-5' : 'lg:col-span-12')}>
                <MatchCard id={c.skillHit.id} source={c.skillHit.source} />
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
            {videos[0] && (
              <div className="lg:col-span-7">
                <VideoCard m={videos[0]} />
              </div>
            )}
            {audios[0] && (
              <div className="lg:col-span-5">
                <AudioCard m={audios[0]} />
              </div>
            )}
          </div>

          {(images.length > 0 || docs.length > 0) && (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
              {images.length > 0 && (
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:col-span-8">
                  {images.map((img) => (
                    <ImageCard key={img.label} m={img} />
                  ))}
                </div>
              )}
              {docs[0] && (
                <div className="lg:col-span-4">
                  <DocumentCard m={docs[0]} />
                </div>
              )}
            </div>
          )}

          {/* SOP — auto-attached install spec, always last */}
          {hasSop && <SopCard />}
        </>
      )}
    </div>
  )
}

// ── SOP card (the real mc4 install-spec PDF) — placed after the media ────────
function SopCard() {
  return (
    <a
      href={REAL_SOP_URL}
      target="_blank"
      rel="noreferrer"
      className="panel group flex items-center gap-5 p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover"
    >
      <div className="relative h-28 w-[5.5rem] shrink-0 rounded-lg border border-ink-900/10 bg-white shadow-card-soft">
        <div className="absolute right-0 top-0 h-5 w-5 rounded-bl-lg border-b border-l border-ink-900/10 bg-paper-100" />
        <div className="space-y-1.5 p-3 pt-5">
          {[10, 8, 9, 6, 8, 5].map((w, i) => (
            <div key={i} className="h-1 rounded-full bg-ink-900/10" style={{ width: `${w * 9}%` }} />
          ))}
        </div>
        <span className="absolute bottom-2 left-2 rounded bg-[#ea4335] px-1.5 py-0.5 text-[8px] font-bold tracking-wide text-white">
          PDF
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-400">
          <FileText size={13} /> Document · SOP
        </div>
        <div className="mt-2 text-[15px] font-semibold text-ink-900">{REAL_SOP_NAME}</div>
        <div className="mt-0.5 text-[12.5px] text-ink-500">
          Auto-attached step-by-step install spec · 2 pages
        </div>
        <span className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-ink-900/[0.10] bg-white px-3.5 py-2 text-[12px] font-semibold text-ink-700 transition-colors group-hover:border-ink-900/25 group-hover:text-ink-900">
          Open document <ExternalLink size={13} />
        </span>
      </div>
    </a>
  )
}

// ── Hero count KPI (icon + big count + label) ───────────────────────────────
function CountCard({ icon: Icon, value, label }: { icon: LucideIcon; value: number; label: string }) {
  return (
    <div className="flex flex-col rounded-2xl border border-ink-900/[0.07] bg-white px-4 py-3.5 shadow-card-soft">
      <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-ink-900/[0.04] text-ink-500 ring-1 ring-inset ring-ink-900/[0.04]">
        <Icon size={15} />
      </span>
      <div className="mt-3 font-display text-[24px] font-bold leading-none tracking-tightest text-ink-900">{value}</div>
      <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-400">{label}</div>
    </div>
  )
}

// ── Source strip ────────────────────────────────────────────────────────────
function SourceStrip({ c }: { c: CaseView }) {
  return (
    <div className="panel flex flex-wrap items-center gap-x-6 gap-y-3 p-4">
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#25d366]/15 text-[#1aa251]">
          <MessageCircle size={16} />
        </div>
        <div>
          <div className="text-[13px] font-semibold text-ink-900">WhatsApp intake</div>
          <div className="font-mono text-[10.5px] text-ink-400">via Twilio · {c.case_id}</div>
        </div>
      </div>
      <span className="hidden h-8 w-px bg-ink-900/[0.08] sm:block" />
      {c.worker_name && <Meta icon={User} label={c.worker_name} />}
      {c.site_id && <Meta icon={MapPin} label={c.site_id} />}
      {c.opened_at && <Meta icon={Clock} label={`Opened ${c.opened_at}`} />}
    </div>
  )
}

function Meta({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[12.5px] text-ink-600">
      <Icon size={13.5} className="text-ink-400" />
      {label}
    </div>
  )
}

// ── The engineer's text report ──────────────────────────────────────────────
function TextReport({ msg, name }: { msg: ChatMessage; name: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="panel relative h-full overflow-hidden p-6"
    >
      <div className="pointer-events-none absolute -left-6 -top-8 font-serif text-[120px] leading-none text-ink-900/[0.04]">“</div>
      <div className="relative">
        <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-ink-400">
          <MessageSquareText size={13} /> Field report · text
        </div>
        <p className="mt-3 max-w-3xl text-[18px] font-medium leading-relaxed text-ink-900">{msg.text}</p>
        <div className="mt-4 flex items-center gap-2 text-[12px] text-ink-500">
          <User size={13} className="text-ink-400" />
          <span className="font-medium text-ink-700">{name}</span>
          <span className="text-ink-300">·</span>
          <span className="font-mono text-[11px]">{msg.ts}</span>
        </div>
      </div>
    </motion.div>
  )
}

// ── Skill-match card (only when c.skillHit exists) ──────────────────────────
function MatchCard({ id, source }: { id: string; source: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative flex h-full flex-col justify-between overflow-hidden rounded-2xl border border-brand-500/25 bg-gradient-to-br from-brand-50 via-white to-violet/[0.07] p-6 shadow-card-soft"
    >
      <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-brand-500/10 blur-3xl" />
      <div className="relative">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-500/12 text-brand-600 ring-1 ring-inset ring-brand-500/20">
            <Sparkles size={16} />
          </span>
          <div className="min-w-0">
            <div className="text-[14.5px] font-semibold tracking-tight text-brand-700">Seen this before.</div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-600">
              Matched <span className="font-mono text-[12px] text-ink-800">{id}</span> (candidate) from{' '}
              <span className="font-mono text-[12px] text-ink-800">{source}</span> — passed the hard gate.
            </p>
          </div>
        </div>
      </div>
      <button className="relative mt-5 inline-flex w-fit items-center gap-1.5 rounded-lg bg-brand-500 px-3.5 py-2 text-[12.5px] font-semibold text-white shadow-glow transition-transform hover:-translate-y-0.5">
        View match details <ExternalLink size={13} />
      </button>
    </motion.div>
  )
}

// ── Card header ─────────────────────────────────────────────────────────────
function CardHeader({ icon: Icon, title, right }: { icon: LucideIcon; title: string; right?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-ink-900/[0.07] px-4 py-3">
      <div className="flex items-center gap-2 text-[11.5px] font-semibold uppercase tracking-wide text-ink-500">
        <Icon size={14} /> {title}
      </div>
      {right && <span className="font-mono text-[10.5px] text-ink-400">{right}</span>}
    </div>
  )
}

// ── Tiny overlay icon-buttons (zoom / fullscreen / download) ─────────────────
function TileTools() {
  return (
    <span className="absolute bottom-3 right-3 flex items-center gap-1.5">
      {[ZoomIn, Maximize2, Download].map((Ic, i) => (
        <span
          key={i}
          className="flex h-7 w-7 items-center justify-center rounded-md bg-black/40 text-white/90 backdrop-blur transition-colors hover:bg-black/60"
        >
          <Ic size={13} />
        </span>
      ))}
    </span>
  )
}

// ── Video — the real field clip ─────────────────────────────────────────────
function VideoCard({ m }: { m: MediaItem }) {
  return (
    <div className="panel overflow-hidden">
      <CardHeader icon={Video} title="Video" right={m.meta ?? 'video/mp4'} />
      <div className="relative aspect-video w-full overflow-hidden bg-black">
        <video
          src={REAL_VIDEO_URL}
          controls
          preload="metadata"
          playsInline
          className="h-full w-full object-contain"
        />
      </div>
      {m.note && <div className="px-4 py-3 text-[12.5px] leading-relaxed text-ink-600">{m.note}</div>}
    </div>
  )
}

// ── Audio (the waveform) ────────────────────────────────────────────────────
function AudioCard({ m }: { m: MediaItem }) {
  const [playing, setPlaying] = useState(false)
  return (
    <div className="panel flex h-full flex-col">
      <CardHeader icon={AudioLines} title="Audio" right={m.meta ?? m.duration} />
      <div className="flex flex-1 flex-col justify-center px-5 py-6">
        <Waveform playing={playing} />
        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={() => setPlaying((p) => !p)}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-violet text-white shadow-glow transition-transform hover:scale-105"
          >
            {playing ? <Pause size={17} fill="currentColor" /> : <Play size={18} className="ml-0.5" fill="currentColor" />}
          </button>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[12.5px] font-semibold text-ink-900">{m.label}</div>
            <div className="font-mono text-[10.5px] text-ink-400">{playing ? '0:09' : '0:00'} / {m.duration ?? '—'}</div>
          </div>
        </div>
        {m.note && (
          <div className="mt-3 rounded-lg border border-ink-900/[0.06] bg-paper-50 px-3 py-2 text-[11.5px] italic leading-relaxed text-ink-500">
            “{m.note}”
          </div>
        )}
      </div>
    </div>
  )
}

// deterministic symmetric envelope (bell-shaped, dense) — recreates AudioWave.png
const BARS = Array.from({ length: 76 }, (_, i) => {
  const t = i / 75
  const env = Math.pow(Math.sin(Math.PI * t), 0.5)
  const noise = 0.4 + 0.6 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.73))
  return Math.max(0.14, env * noise)
})

function Waveform({ playing }: { playing: boolean }) {
  return (
    <div className="relative flex h-28 items-center justify-center gap-[2px]">
      {BARS.map((h, i) => {
        const t = i / (BARS.length - 1)
        const central = 1 - Math.abs(t - 0.5) * 2 // 1 at centre → 0 at edges
        const light = 64 + central * 8
        const sat = 58 + central * 18
        return (
          <span
            key={i}
            className={clsx('w-[3px] origin-center rounded-full', playing && 'animate-waveform')}
            style={{
              height: `${Math.round(h * 100)}%`,
              background: `hsl(258, ${sat}%, ${light}%)`,
              animationDelay: `${(i % 13) * 0.06}s`,
              animationDuration: `${1 + (i % 5) * 0.12}s`,
              transform: playing ? undefined : `scaleY(${0.7 + central * 0.3})`,
            }}
          />
        )
      })}
      {/* circular playhead + centre line — the reference motif */}
      <span className="pointer-events-none absolute left-1/2 top-1/2 h-[88px] w-[88px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-violet/40" />
      <span className="pointer-events-none absolute left-1/2 top-1/2 h-28 w-px -translate-x-1/2 -translate-y-1/2 bg-violet/50" />
    </div>
  )
}

// ── Image (annotated inspection photo) ──────────────────────────────────────
function ImageCard({ m }: { m: MediaItem }) {
  const thermal = /thermal/i.test(m.label)
  return (
    <div className="panel overflow-hidden">
      <CardHeader icon={ImageIcon} title={thermal ? 'Image · thermal' : 'Image'} right={m.meta} />
      <div className="relative aspect-[4/3] overflow-hidden">
        {thermal ? (
          <div
            className="absolute inset-0"
            style={{ background: 'radial-gradient(38% 40% at 54% 42%, #ff3b3b 0%, #ff8c00 26%, #ffe000 42%, #2ec27e 60%, #1d84d6 80%, #102a6b 100%)' }}
          />
        ) : (
          <>
            <div className="absolute inset-0" style={{ background: 'radial-gradient(62% 60% at 50% 46%, #6b3a1f 0%, #2a1810 58%, #120c0a 100%)' }} />
            <div className="absolute left-1/2 top-[46%] h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full bg-orange-500/40 blur-xl" />
            <div className="absolute left-1/2 top-[46%] h-8 w-8 -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-200/60 blur-sm" />
          </>
        )}
        {/* detection box */}
        <div className="absolute left-[27%] top-[28%] h-[42%] w-[46%] rounded-[3px] border-2 border-white/85 shadow-[0_0_0_9999px_rgba(0,0,0,0.18)]">
          <span className="absolute -top-[22px] left-0 whitespace-nowrap rounded bg-white px-1.5 py-0.5 text-[9px] font-semibold text-ink-900 shadow">
            {thermal ? '82°C hot-spot' : 'melted MC4 · charred + pin'}
          </span>
        </div>
        <span className="absolute left-3 top-3 rounded-md bg-black/45 px-2 py-1 font-mono text-[10px] font-medium text-white backdrop-blur">
          {m.label}
        </span>
        <TileTools />
      </div>
      {m.note && <div className="px-4 py-3 text-[12px] leading-relaxed text-ink-600">{m.note}</div>}
    </div>
  )
}

// ── Document ────────────────────────────────────────────────────────────────
function DocumentCard({ m }: { m: MediaItem }) {
  return (
    <div className="panel flex h-full flex-col">
      <CardHeader icon={FileText} title="Document" right={m.meta} />
      <div className="flex flex-1 items-center gap-4 px-5 py-5">
        {/* faux page */}
        <div className="relative h-28 w-[5.5rem] shrink-0 rounded-lg border border-ink-900/10 bg-white shadow-card-soft">
          <div className="absolute right-0 top-0 h-5 w-5 rounded-bl-lg border-b border-l border-ink-900/10 bg-paper-100" />
          <div className="space-y-1.5 p-3 pt-5">
            {[10, 8, 9, 6, 8, 5].map((w, i) => (
              <div key={i} className="h-1 rounded-full bg-ink-900/10" style={{ width: `${w * 9}%` }} />
            ))}
          </div>
          <span className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded bg-danger/90 px-1.5 py-0.5 text-[7.5px] font-bold tracking-wide text-white">
            PDF
          </span>
        </div>
        <div className="min-w-0">
          <div className="text-[13px] font-semibold text-ink-900">{m.label}</div>
          <div className="font-mono text-[10.5px] text-ink-400">{m.meta}</div>
          {m.note && <div className="mt-2 text-[12px] leading-relaxed text-ink-500">{m.note}</div>}
          <button className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-ink-900/[0.10] bg-white px-3 py-1.5 text-[11.5px] font-medium text-ink-700 transition-colors hover:bg-paper-50">
            <ExternalLink size={12} /> Open document
          </button>
        </div>
      </div>
    </div>
  )
}
