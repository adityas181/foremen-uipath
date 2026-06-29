import { clsx } from '../lib/format'
import logoUrl from '../assets/agentic-foreman-logo.png'

export function Logo({
  className,
  subtitle,
  size = 34,
}: {
  className?: string
  subtitle?: string
  size?: number
}) {
  return (
    <div className={clsx('flex items-center gap-3', className)}>
      <img
        src={logoUrl}
        alt="Agentic Foreman"
        style={{ height: size }}
        className="w-auto select-none"
        draggable={false}
      />
      {subtitle && (
        <span className="hidden rounded-md border border-ink-900/[0.10] bg-white px-2.5 py-1 font-mono text-[9.5px] font-medium uppercase tracking-[0.18em] text-ink-500 sm:inline-block">
          {subtitle}
        </span>
      )}
    </div>
  )
}
