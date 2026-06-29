import { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import type { LogEntry } from '../types'
import { Dot } from './ui'
import type { Tone } from '../lib/hues'
import { rewriteLogText } from '../lib/livePresentation'

export function ActivityLog({ entries }: { entries: LogEntry[] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [entries.length])

  return (
    <div ref={ref} className="h-full overflow-y-auto px-4 py-3">
      <div className="space-y-2">
        <AnimatePresence initial={false}>
          {entries.map((e) => (
            <motion.div
              key={e.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              className="flex items-start gap-2.5"
            >
              <div className="mt-1.5">
                <Dot tone={(e.tone as Tone) ?? 'muted'} size={7} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-[10px] text-ink-400">{e.ts}</span>
                  <span className="truncate font-mono text-[10px] font-medium text-ink-500">
                    {e.source}
                  </span>
                </div>
                <div className="text-[12px] leading-snug text-ink-700">{rewriteLogText(e.source, e.text)}</div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {entries.length === 0 && (
          <div className="py-6 text-center text-xs text-ink-400">No activity yet — press play.</div>
        )}
      </div>
    </div>
  )
}
