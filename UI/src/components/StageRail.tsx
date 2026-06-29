import { Check } from 'lucide-react'
import { STAGES, type StageId } from '../types'
import { clsx } from '../lib/format'

export function StageRail({ stage, status }: { stage: StageId; status: string }) {
  const currentIndex = STAGES.findIndex((s) => s.id === stage)
  return (
    <div className="flex items-stretch gap-0 overflow-x-auto">
      {STAGES.map((s, i) => {
        const done = i < currentIndex || status === 'closed'
        const active = i === currentIndex && status !== 'closed'
        return (
          <div key={s.id} className="flex min-w-[92px] flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              <div
                className={clsx(
                  'h-[2px] flex-1',
                  i === 0 ? 'opacity-0' : done || active ? 'bg-brand-400' : 'bg-ink-900/10',
                )}
              />
              <div
                className={clsx(
                  'relative flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold transition-all',
                  done && 'border-brand-300 bg-brand-50 text-brand-700',
                  active && 'border-brand-500 bg-brand-500 text-white shadow-glow animate-pulse-ring',
                  !done && !active && 'border-ink-900/12 bg-white text-ink-400',
                )}
              >
                {done ? <Check size={13} strokeWidth={3} /> : i + 1}
              </div>
              <div
                className={clsx(
                  'h-[2px] flex-1',
                  i === STAGES.length - 1 ? 'opacity-0' : done ? 'bg-brand-400' : 'bg-ink-900/10',
                )}
              />
            </div>
            <div className="mt-2 text-center">
              <div
                className={clsx(
                  'text-[12px] font-semibold leading-tight',
                  active ? 'text-ink-900' : done ? 'text-ink-700' : 'text-ink-400',
                )}
              >
                {s.label}
              </div>
              <div className="mt-0.5 hidden text-[10px] leading-tight text-ink-400 sm:block">
                {s.blurb}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
