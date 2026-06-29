import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Radio } from 'lucide-react'
import { Logo } from '../components/Logo'
import { Sidebar, TABS } from './Sidebar'
import { useLiveFeed } from '../store/liveFeed'
import { useStore } from '../store/store'
import { clsx } from '../lib/format'

const STATUS_STYLE: Record<string, string> = {
  open: 'text-info bg-info/10',
  parked: 'text-warn bg-warn/10',
  resolved: 'text-ok bg-ok/10',
  closed: 'text-ok bg-ok/10',
}

export function Dashboard() {
  useLiveFeed() // streams real CaseEvents over WebSocket from the view-backend
  const { pathname } = useLocation()
  const routeKey = pathname.split('/').filter(Boolean).pop() ?? 'cases'
  const isCases = routeKey === 'cases'
  const isCalls = routeKey === 'calls' // hide the top bar on the Calls page for a clean call view
  const activeCase = useStore((s) => (s.activeCaseId ? s.cases[s.activeCaseId] : null))

  return (
    <div className="flex min-h-screen bg-page text-ink-700 [overflow-x:clip]">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header — hidden on the Calls page for a clean call view */}
        <header
          className={clsx(
            'sticky top-0 z-30 border-b border-ink-900/[0.06] bg-white/80 backdrop-blur-xl',
            isCalls && 'hidden',
          )}
        >
          <div className="flex h-[68px] items-center gap-3 px-4 sm:px-6">
            {/* Mobile brand */}
            <div className="lg:hidden">
              <Logo size={26} />
            </div>

            {/* Left cluster */}
            <div className="hidden items-center gap-3 lg:flex">
              <span className="inline-flex items-center rounded-lg border border-ink-900/[0.08] bg-paper-50 px-3 py-1.5 font-mono text-[10.5px] font-semibold uppercase tracking-[0.14em] text-ink-600">
                Control Room
              </span>
              {!isCases && activeCase && (
                <div className="flex items-center gap-2 rounded-lg border border-ink-900/[0.08] bg-white px-3 py-1.5 shadow-card-soft">
                  <Radio size={13} className="text-brand-500" />
                  <span className="font-mono text-[11px] text-ink-700">{activeCase.case_id}</span>
                  <span className="text-ink-300">·</span>
                  <span className="font-mono text-[11px] text-ink-500">{activeCase.site_id}</span>
                  <span
                    className={clsx(
                      'ml-1 rounded px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wide',
                      STATUS_STYLE[activeCase.status] ?? 'text-ink-500 bg-ink-900/5',
                    )}
                  >
                    {activeCase.status}
                  </span>
                </div>
              )}
            </div>

            {/* Right cluster — live indicator */}
            <div className="ml-auto flex items-center gap-2.5">
              <LiveBadge />
            </div>
          </div>
        </header>

        {/* Section sub-tabs — mobile-only nav (the sidebar is the desktop nav) */}
        <div className="border-b border-ink-900/[0.06] bg-white/60 backdrop-blur lg:hidden">
          <nav className="no-scrollbar flex gap-1 overflow-x-auto px-4 sm:px-6">
            {TABS.map((t) => (
              <NavLink key={t.to} to={t.to} className={({ isActive }) => clsx('subtab', isActive && 'subtab-active')}>
                {({ isActive }) => (
                  <>
                    <t.icon size={14} strokeWidth={2} />
                    {t.label}
                    <span
                      className={clsx(
                        'absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-brand-sheen transition-opacity',
                        isActive ? 'opacity-100' : 'opacity-0',
                      )}
                    />
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Content */}
        <main className="mx-auto w-full max-w-[1320px] flex-1 px-4 py-6 sm:px-6 sm:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function LiveBadge() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="inline-flex items-center gap-2 rounded-lg border border-ok/30 bg-ok/[0.07] px-3 py-1.5 text-[12px] font-semibold text-ok">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ok opacity-70" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-ok" />
        </span>
        LIVE
      </span>
      <span className="hidden font-mono text-[11px] text-ink-400 sm:inline">streaming · UiPath Maestro</span>
    </div>
  )
}
