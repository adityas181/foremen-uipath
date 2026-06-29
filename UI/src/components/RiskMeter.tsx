import { clsx } from '../lib/format'

// ── Semicircular risk gauge (Console) — 0..1 with the 0.70 call threshold ────
function polar(cx: number, cy: number, r: number, frac: number) {
  const theta = Math.PI * (1 - Math.max(0, Math.min(1, frac)))
  return [cx + r * Math.cos(theta), cy - r * Math.sin(theta)] as const
}
function arc(cx: number, cy: number, r: number, f0: number, f1: number) {
  const [x0, y0] = polar(cx, cy, r, f0)
  const [x1, y1] = polar(cx, cy, r, f1)
  return `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${r} ${r} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`
}

export function RiskGauge({ value, className }: { value: number | null; className?: string }) {
  const v = value ?? 0
  const high = v >= 0.7
  const color = value === null ? '#969ca5' : high ? '#e23b3b' : v >= 0.45 ? '#c77b08' : '#1aa251'
  const label = value === null ? '—' : high ? 'High Risk' : v >= 0.45 ? 'Elevated' : 'Low Risk'
  const W = 240
  const cx = 120
  const cy = 128
  const r = 96
  const [nx, ny] = polar(cx, cy, r - 14, v)
  const [tx, ty] = polar(cx, cy, r, 0.7)

  return (
    <div className={clsx('flex flex-col items-center', className)}>
      <svg viewBox={`0 0 ${W} 150`} className="w-full max-w-[260px]">
        {/* zone arcs */}
        <path d={arc(cx, cy, r, 0, 0.45)} fill="none" stroke="#1aa251" strokeWidth={13} strokeLinecap="round" />
        <path d={arc(cx, cy, r, 0.46, 0.7)} fill="none" stroke="#e6ab3e" strokeWidth={13} strokeLinecap="round" />
        <path d={arc(cx, cy, r, 0.71, 1)} fill="none" stroke="#e23b3b" strokeWidth={13} strokeLinecap="round" />
        {/* 0.70 call threshold tick */}
        <line x1={tx} y1={ty} x2={polar(cx, cy, r - 20, 0.7)[0]} y2={polar(cx, cy, r - 20, 0.7)[1]} stroke="#14171c" strokeOpacity={0.4} strokeWidth={2} />
        {/* needle */}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={color} strokeWidth={3.5} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={6} fill={color} />
        <circle cx={cx} cy={cy} r={11} fill="none" stroke={color} strokeOpacity={0.25} strokeWidth={2} />
      </svg>
      <div className="-mt-6 text-center">
        <div className="font-display text-[30px] font-bold leading-none tracking-tightest" style={{ color }}>
          {value === null ? '—' : v.toFixed(2)}
        </div>
        <div className="mt-1 text-[11px] font-semibold uppercase tracking-wide" style={{ color }}>
          {label}
        </div>
      </div>
      <div className="mt-2 flex w-full max-w-[240px] items-center justify-between px-2 text-[10px] font-mono text-ink-400">
        <span>0</span>
        <span className="text-ink-500">0.70 · call</span>
        <span>1.00</span>
      </div>
    </div>
  )
}

// Horizontal risk bar 0..1 with the 0.7 call-threshold marked.
export function RiskMeter({ value, className }: { value: number | null; className?: string }) {
  const v = value ?? 0
  const pctV = Math.round(v * 100)
  const high = v >= 0.7
  const color = value === null ? '#969ca5' : high ? '#e23b3b' : v >= 0.45 ? '#c77b08' : '#1aa251'

  return (
    <div className={clsx('w-full', className)}>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-xs font-medium text-ink-500">Risk score</span>
        <span className="font-display text-lg font-bold tracking-tightest" style={{ color }}>
          {value === null ? '—' : v.toFixed(2)}
        </span>
      </div>
      <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-ink-900/[0.07]">
        <div
          className="h-full rounded-full transition-[width] duration-700 ease-out"
          style={{ width: `${pctV}%`, background: `linear-gradient(90deg, ${color}cc, ${color})` }}
        />
        {/* 0.7 threshold marker */}
        <div className="absolute inset-y-0" style={{ left: '70%' }}>
          <div className="h-full w-[2px] bg-ink-900/35" />
        </div>
      </div>
      <div className="relative mt-1 h-3 text-[10px] text-ink-400">
        <span className="absolute" style={{ left: '70%', transform: 'translateX(-50%)' }}>
          0.70 · call
        </span>
      </div>
    </div>
  )
}
