import { motion } from 'framer-motion'
import { Brain, Check, Cpu, Loader2, Quote } from 'lucide-react'
import type { AgentDef, AgentRun } from '../types'
import { clsx, pct } from '../lib/format'
import { HUE_HEX } from '../lib/hues'

export function AgentCard({ def, run, compact }: { def: AgentDef; run: AgentRun; compact?: boolean }) {
  const hex = HUE_HEX[def.hue]
  const active = run.status === 'running'
  const done = run.status === 'done'
  const idle = run.status === 'idle'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: idle ? 0.55 : 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={clsx(
        'relative overflow-hidden rounded-2xl border bg-white p-4 shadow-card-soft transition-colors',
        active ? 'border-ink-900/15' : 'border-ink-900/[0.07]',
      )}
      style={active ? { boxShadow: `0 0 0 1px ${hex}66, 0 10px 34px -12px ${hex}` } : undefined}
    >
      {/* hue wash */}
      <div
        className="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full opacity-25 blur-2xl"
        style={{ background: hex }}
      />
      {active && (
        <motion.div
          className="absolute inset-x-0 top-0 h-[2px]"
          style={{ background: `linear-gradient(90deg, transparent, ${hex}, transparent)` }}
          animate={{ x: ['-100%', '100%'] }}
          transition={{ repeat: Infinity, duration: 1.4, ease: 'linear' }}
        />
      )}

      <div className="relative flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-xl"
            style={{ background: `${hex}22`, color: shade(hex), border: `1px solid ${hex}55` }}
          >
            {def.id === 'vision' ? <Brain size={17} /> : <Cpu size={17} />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-ink-900">{def.name}</span>
              <span className="chip chip-dark !px-1.5 !py-0.5 !text-[9px] uppercase tracking-wider">
                {def.kind}
              </span>
            </div>
            <div className="text-[11px] font-mono text-ink-400">{def.reads}</div>
          </div>
        </div>
        <StatusPill status={run.status} hex={shade(hex)} />
      </div>

      {!compact && (
        <p className="relative mt-3 text-[12px] leading-relaxed text-ink-500">{def.role}</p>
      )}

      {done && run.headline && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative mt-3 rounded-xl border border-ink-900/[0.06] bg-paper-50 p-3"
        >
          <div className="flex items-start gap-2">
            <Check size={15} className="mt-0.5 shrink-0 text-ok" />
            <div>
              <div className="text-[13px] font-semibold text-ink-900">{run.headline}</div>
              {run.detail && (
                <div className="mt-1 text-[11.5px] leading-relaxed text-ink-600">{run.detail}</div>
              )}
            </div>
          </div>
          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            {typeof run.confidence === 'number' && (
              <span className="chip chip-dark" style={{ color: shade(hex), borderColor: `${hex}66` }}>
                conf {pct(run.confidence)}
              </span>
            )}
            {run.citations?.map((cit) => (
              <span key={cit} className="chip chip-dark">
                <Quote size={9} /> {cit}
              </span>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

function StatusPill({ status, hex }: { status: AgentRun['status']; hex: string }) {
  if (status === 'running') {
    return (
      <span className="chip chip-dark" style={{ color: hex, borderColor: `${hex}66` }}>
        <Loader2 size={11} className="animate-spin" /> Thinking…
      </span>
    )
  }
  if (status === 'done') {
    return (
      <span className="chip chip-dark text-ok" style={{ borderColor: '#1aa25144' }}>
        <Check size={11} /> Done
      </span>
    )
  }
  if (status === 'assembled') {
    return <span className="chip chip-dark">Assembled</span>
  }
  return <span className="chip chip-dark opacity-60">Idle</span>
}

// darken a pastel hex for legible text/icon on white
function shade(hex: string): string {
  const m = hex.replace('#', '')
  const r = Math.round(parseInt(m.slice(0, 2), 16) * 0.55)
  const g = Math.round(parseInt(m.slice(2, 4), 16) * 0.55)
  const b = Math.round(parseInt(m.slice(4, 6), 16) * 0.55)
  return `rgb(${r}, ${g}, ${b})`
}
