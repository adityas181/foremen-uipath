import type { ReactNode } from 'react'
import { ArrowDownRight, ArrowUpRight } from 'lucide-react'
import { clsx } from '../lib/format'
import { TONE_HEX, type Tone } from '../lib/hues'

// ── Pill chip (icon + label) ────────────────────────────────────────────────
export function Chip({
  children,
  icon,
  className,
  variant = 'dark',
}: {
  children: ReactNode
  icon?: ReactNode
  className?: string
  variant?: 'dark' | 'light'
}) {
  return (
    <span className={clsx('chip', variant === 'light' ? 'chip-light' : 'chip-dark', className)}>
      {icon && <span className="-ml-0.5 opacity-80">{icon}</span>}
      {children}
    </span>
  )
}

// ── Small uppercase mono section label ──────────────────────────────────────
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={clsx(
        'font-mono text-[11px] font-medium uppercase tracking-[0.22em] text-ink-400',
        className,
      )}
    >
      {children}
    </div>
  )
}

// ── Elegant page/tab header — the home-page recipe (brand eyebrow + big title) ─
export function TabHeader({
  eyebrow,
  title,
  sub,
  right,
  className,
}: {
  eyebrow: string
  title: ReactNode
  sub?: string
  right?: ReactNode
  className?: string
}) {
  return (
    <div className={clsx('flex flex-wrap items-end justify-between gap-x-6 gap-y-4', className)}>
      <div className="max-w-2xl">
        <div className="inline-flex items-center rounded-md border border-ink-900/[0.08] bg-paper-50 px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-ink-500">
          {eyebrow}
        </div>
        <h1 className="mt-4 font-serif text-[31px] font-normal leading-[1.07] tracking-[-0.012em] text-ink-900 sm:text-[42px]">
          {title}
        </h1>
        {sub && <p className="mt-3.5 max-w-xl text-[15px] leading-relaxed text-ink-500">{sub}</p>}
      </div>
      {right && <div className="flex flex-wrap items-center gap-2">{right}</div>}
    </div>
  )
}

// ── Status dot (with optional pulse) ────────────────────────────────────────
export function Dot({ tone = 'muted', pulse, size = 8 }: { tone?: Tone; pulse?: boolean; size?: number }) {
  return (
    <span className="relative inline-flex" style={{ width: size, height: size }}>
      {pulse && (
        <span
          className="absolute inset-0 animate-ping rounded-full opacity-60"
          style={{ background: TONE_HEX[tone] }}
        />
      )}
      <span
        className="relative inline-block rounded-full"
        style={{ width: size, height: size, background: TONE_HEX[tone] }}
      />
    </span>
  )
}

// ── Badge ───────────────────────────────────────────────────────────────────
export function Badge({
  children,
  tone = 'muted',
  className,
}: {
  children: ReactNode
  tone?: Tone
  className?: string
}) {
  const hex = TONE_HEX[tone]
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold',
        className,
      )}
      style={{ background: `${hex}16`, color: hex, border: `1px solid ${hex}33` }}
    >
      {children}
    </span>
  )
}

// ── Metric / stat block ─────────────────────────────────────────────────────
export function Stat({
  value,
  label,
  sub,
  tone,
  className,
}: {
  value: ReactNode
  label: string
  sub?: string
  tone?: Tone
  className?: string
}) {
  return (
    <div className={clsx('flex flex-col', className)}>
      <div
        className="font-display text-2xl font-bold tracking-tightest text-ink-900"
        style={tone ? { color: TONE_HEX[tone] } : undefined}
      >
        {value}
      </div>
      <div className="mt-0.5 text-xs font-medium text-ink-500">{label}</div>
      {sub && <div className="text-[11px] text-ink-400">{sub}</div>}
    </div>
  )
}

// ── Enterprise KPI card (icon chip + big metric + label) ────────────────────
export function Kpi({
  icon,
  value,
  label,
  tone = 'muted',
  className,
}: {
  icon?: ReactNode
  value: ReactNode
  label: string
  tone?: Tone
  className?: string
}) {
  const hex = TONE_HEX[tone]
  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-2xl border border-ink-900/[0.08] bg-white p-4 shadow-card-soft',
        className,
      )}
    >
      {icon && (
        <span
          className="flex h-9 w-9 items-center justify-center rounded-xl"
          style={{ background: `${hex}14`, color: hex, border: `1px solid ${hex}2e` }}
        >
          {icon}
        </span>
      )}
      <div
        className="mt-3 font-display text-[26px] font-bold leading-none tracking-tightest"
        style={{ color: hex }}
      >
        {value}
      </div>
      <div className="mt-1.5 text-[12px] font-medium text-ink-500">{label}</div>
    </div>
  )
}

// ── Panel header ────────────────────────────────────────────────────────────
export function PanelHeader({
  title,
  icon,
  right,
  className,
}: {
  title: ReactNode
  icon?: ReactNode
  right?: ReactNode
  className?: string
}) {
  return (
    <div className={clsx('flex items-center justify-between gap-3 px-5 py-3.5', className)}>
      <div className="flex items-center gap-2.5">
        {icon && (
          <span className="flex h-7 w-7 items-center justify-center rounded-[9px] bg-ink-900/[0.045] text-ink-500 ring-1 ring-inset ring-ink-900/[0.04]">
            {icon}
          </span>
        )}
        <h3 className="text-[14.5px] font-semibold tracking-tight text-ink-900">{title}</h3>
      </div>
      {right}
    </div>
  )
}

// ── Empty state ─────────────────────────────────────────────────────────────
export function Empty({ icon, text }: { icon?: ReactNode; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      {icon && <div className="text-ink-300">{icon}</div>}
      <div className="text-sm text-ink-400">{text}</div>
    </div>
  )
}

// ── Segmented control (ElevenLabs-style: solid-ink active, quiet inactive) ────
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  size = 'md',
  className,
}: {
  options: { value: T; label: ReactNode }[]
  value: T
  onChange: (v: T) => void
  size?: 'sm' | 'md'
  className?: string
}) {
  return (
    <div
      className={clsx(
        'inline-flex items-center gap-0.5 rounded-lg border border-ink-900/[0.08] bg-paper-100/80 p-0.5',
        className,
      )}
    >
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={clsx(
              'rounded-md font-semibold tracking-tight transition-all duration-150',
              size === 'sm' ? 'px-2.5 py-1 text-[11px]' : 'px-3.5 py-1.5 text-[12px]',
              active
                ? 'bg-ink-900 text-white shadow-[0_1px_2px_rgba(20,23,28,0.25)]'
                : 'text-ink-500 hover:bg-ink-900/[0.05] hover:text-ink-900',
            )}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

// ── Trend delta (▲/▼ + caption) ─────────────────────────────────────────────
export function Trend({
  dir,
  children,
  tone,
  className,
}: {
  dir: 'up' | 'down'
  children: ReactNode
  tone?: Tone
  className?: string
}) {
  const Icon = dir === 'up' ? ArrowUpRight : ArrowDownRight
  const color = tone ? TONE_HEX[tone] : dir === 'up' ? TONE_HEX.ok : TONE_HEX.muted
  return (
    <span className={clsx('inline-flex items-center gap-1 text-[11px] font-medium text-ink-400', className)}>
      <Icon size={12} style={{ color }} strokeWidth={2.4} />
      <span>{children}</span>
    </span>
  )
}

// ── Radial donut meter (sidebar perf widgets, call/crew/graph/audit health) ──
export function Donut({
  value,
  size = 96,
  stroke = 9,
  color = TONE_HEX.info,
  track = 'rgba(20,23,28,0.07)',
  center,
  className,
}: {
  value: number // 0..100
  size?: number
  stroke?: number
  color?: string
  track?: string
  center?: ReactNode
  className?: string
}) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const off = c * (1 - Math.max(0, Math.min(100, value)) / 100)
  return (
    <div className={clsx('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
          style={{ transition: 'stroke-dashoffset 900ms cubic-bezier(0.4,0,0.2,1)' }}
        />
      </svg>
      {center && <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{center}</div>}
    </div>
  )
}

// ── Inline sparkline (tiny trend chart for KPI cards) ────────────────────────
export function Sparkline({
  data,
  color = TONE_HEX.info,
  width = 96,
  height = 30,
  fill = true,
  className,
}: {
  data: number[]
  color?: string
  width?: number
  height?: number
  fill?: boolean
  className?: string
}) {
  if (data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const span = max - min || 1
  const pad = 2
  const stepX = (width - pad * 2) / (data.length - 1)
  const pts = data.map((d, i) => {
    const x = pad + i * stepX
    const y = pad + (1 - (d - min) / span) * (height - pad * 2)
    return [x, y] as const
  })
  const line = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const area = `${line} L${pts[pts.length - 1][0].toFixed(1)},${height} L${pts[0][0].toFixed(1)},${height} Z`
  const gid = `spark-${color.replace(/[^a-z0-9]/gi, '')}`
  return (
    <svg width={width} height={height} className={className} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.22} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${gid})`} />}
      <path d={line} fill="none" stroke={color} strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// ── Metric card (icon chip + label + big value + trend) — dashboard KPIs ──────
export function MetricCard({
  icon,
  label,
  value,
  trend,
  tone = 'info',
  className,
}: {
  icon?: ReactNode
  label: string
  value: ReactNode
  trend?: ReactNode
  tone?: Tone
  className?: string
}) {
  const hex = TONE_HEX[tone]
  return (
    <div
      className={clsx(
        'group flex items-center gap-4 rounded-2xl border border-ink-900/[0.07] bg-white p-4 shadow-card-soft transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover sm:p-5',
        className,
      )}
    >
      {icon && (
        <span
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl transition-transform duration-200 group-hover:scale-105"
          style={{ background: `${hex}12`, color: hex, border: `1px solid ${hex}24` }}
        >
          {icon}
        </span>
      )}
      <div className="min-w-0">
        <div className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-ink-400">{label}</div>
        <div className="mt-1 font-display text-[26px] font-bold leading-none tracking-tightest text-ink-900">
          {value}
        </div>
        {trend && <div className="mt-1.5">{trend}</div>}
      </div>
    </div>
  )
}

// ── Pill button (ElevenLabs outline pill — for standalone actions) ───────────
export function PillButton({
  children,
  onClick,
  icon,
  active,
  className,
}: {
  children: ReactNode
  onClick?: () => void
  icon?: ReactNode
  active?: boolean
  className?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-[12px] font-semibold tracking-tight transition-all duration-150',
        active
          ? 'bg-ink-900 text-white shadow-[0_1px_2px_rgba(20,23,28,0.25)] hover:bg-ink-800'
          : 'border border-ink-900/[0.12] bg-white text-ink-700 hover:border-ink-900/25 hover:text-ink-900',
        className,
      )}
    >
      {icon && <span className="-ml-0.5 opacity-80">{icon}</span>}
      {children}
    </button>
  )
}
