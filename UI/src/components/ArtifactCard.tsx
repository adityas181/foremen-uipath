import { motion } from 'framer-motion'
import {
  ClipboardList,
  ExternalLink,
  FileCheck2,
  GitBranch,
  ShieldCheck,
  Wrench,
} from 'lucide-react'
import type { Artifact, ArtifactType } from '../types'

const ICON: Record<ArtifactType, typeof Wrench> = {
  ticket: ClipboardList,
  work_order: Wrench,
  warranty_claim: ShieldCheck,
  fleet_case: GitBranch,
  noc: FileCheck2,
}

export function ArtifactCard({ a }: { a: Artifact }) {
  const Icon = ICON[a.type]
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="rounded-2xl border border-ink-900/[0.07] bg-white p-4 shadow-card-soft"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-ok/12 text-ok">
            <Icon size={17} />
          </div>
          <div>
            <div className="font-mono text-[13px] font-semibold text-ink-900">{a.id}</div>
            <div className="text-[11px] text-ink-500">{a.title}</div>
          </div>
        </div>
        {a.external && (
          <span className="chip chip-dark text-info" style={{ borderColor: '#1d84d655' }}>
            <ExternalLink size={10} /> real write
          </span>
        )}
      </div>

      {a.guard && (
        <div className="mt-3">
          <span className="chip chip-dark text-ok" style={{ borderColor: '#1aa25144' }}>
            <ShieldCheck size={10} /> guard · {a.guard}
          </span>
        </div>
      )}

      <dl className="mt-3 space-y-1.5">
        {Object.entries(a.fields).map(([k, v]) => (
          <div key={k} className="flex items-start justify-between gap-3 text-[11.5px]">
            <dt className="font-mono text-ink-400">{k}</dt>
            <dd className="text-right font-medium text-ink-700">{String(v)}</dd>
          </div>
        ))}
      </dl>
    </motion.div>
  )
}
