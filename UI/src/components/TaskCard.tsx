import { motion } from 'framer-motion'
import { CheckCircle2, UserCheck } from 'lucide-react'
import type { HumanTask } from '../types'
import { clsx } from '../lib/format'

export function TaskCard({ task }: { task: HumanTask }) {
  const pending = task.status === 'pending'
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'rounded-2xl border p-4 shadow-card-soft',
        pending ? 'border-warn/40 bg-warn/[0.07]' : 'border-ok/30 bg-ok/[0.06]',
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={clsx('flex h-7 w-7 items-center justify-center rounded-lg', pending ? 'bg-warn/15 text-warn' : 'bg-ok/15 text-ok')}>
            <UserCheck size={15} />
          </span>
          <div>
            <div className="text-[12px] font-semibold text-ink-900">
              Action Center · {task.kind === 'confirm' ? 'Confirm' : 'Approve call'}
            </div>
            <div className="font-mono text-[10px] text-ink-400">{task.id}</div>
          </div>
        </div>
        {pending ? (
          <span className="chip chip-dark text-warn" style={{ borderColor: '#c77b0855' }}>
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-warn" /> parked
          </span>
        ) : (
          <span className="chip chip-dark text-ok" style={{ borderColor: '#1aa25155' }}>
            <CheckCircle2 size={11} /> answered
          </span>
        )}
      </div>

      <p className="mt-3 text-[12.5px] leading-relaxed text-ink-700">{task.prompt}</p>

      {task.options && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {task.options.map((o) => (
            <span
              key={o}
              className={clsx(
                'rounded-md border px-2.5 py-1 font-mono text-[11px]',
                !pending && task.answer === o
                  ? 'border-ok/50 bg-ok/15 text-ok'
                  : 'border-ink-900/10 bg-white text-ink-500',
              )}
            >
              {o}
            </span>
          ))}
        </div>
      )}

      {!pending && (
        <div className="mt-3 flex items-center gap-2 border-t border-ok/15 pt-2.5 text-[11.5px]">
          <CheckCircle2 size={13} className="text-ok" />
          <span className="text-ink-700">
            <span className="font-semibold text-ok">{task.answer}</span>
            {task.answeredBy && <span className="text-ink-400"> · {task.answeredBy}</span>}
          </span>
        </div>
      )}
    </motion.div>
  )
}
