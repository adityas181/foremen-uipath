import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Activity,
  ChevronsUpDown,
  GitBranch,
  Images,
  LayoutGrid,
  Phone,
  Sparkles,
  Users,
  FileText,
} from 'lucide-react'
import { Logo } from '../components/Logo'
import { Donut, Dot } from '../components/ui'
import { useStore } from '../store/store'
import { SKILL_LIBRARY } from '../data/skillLibrary'
import { clsx } from '../lib/format'
import isoCube from '../assets/graphics/iso-cube-tall.jpeg'
import knowledgeCube from '../assets/graphics/knowledge-cube.jpeg'

export const TABS = [
  { to: 'cases', label: 'Cases', icon: LayoutGrid },
  { to: 'console', label: 'Console', icon: Activity },
  { to: 'media', label: 'MediaBoard', icon: Images },
  { to: 'crew', label: 'Crew', icon: Users },
  { to: 'calls', label: 'Calls', icon: Phone },
  { to: 'skills', label: 'Skills', icon: Sparkles },
  { to: 'fleet', label: 'Knowledge Graph', icon: GitBranch },
  { to: 'audit', label: 'Audit', icon: FileText },
]

export function Sidebar() {
  const { pathname } = useLocation()
  const routeKey = pathname.split('/').filter(Boolean).pop() ?? 'cases'

  return (
    <aside className="sticky top-0 z-40 hidden h-screen w-[248px] shrink-0 flex-col border-r border-ink-900/[0.06] bg-white lg:flex">
      {/* Brand */}
      <div className="flex h-[68px] items-center px-5">
        <Logo size={28} />
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-0.5 px-3 pt-2">
        {TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            className={({ isActive }) => clsx('nav-link', isActive && 'nav-link-active')}
          >
            <t.icon size={17} strokeWidth={2} />
            {t.label}
          </NavLink>
        ))}
      </nav>

      <div className="flex-1" />

      {/* Contextual widget */}
      <div className="px-3 pb-2">
        <SidebarWidget routeKey={routeKey} />
      </div>

      {/* User */}
      <UserCard />
    </aside>
  )
}

function SidebarWidget({ routeKey }: { routeKey: string }) {
  const skills = useStore((s) => Object.values(s.skills))

  switch (routeKey) {
    case 'calls':
      return (
        <PerfWidget
          title="Call Performance"
          value={98.7}
          color="#3ba7f0"
          centerLabel="Authorised by Voice"
          rows={[
            ['Avg. Authorisation Time', '12m 34s', 'down', '18%'],
            ['First Call Resolution', '91.2%', 'up', '7%'],
            ['Escalation Accuracy', '96.1%', 'down', '9%'],
          ]}
        />
      )
    case 'crew':
      return (
        <PerfWidget
          title="Crew Performance"
          value={98.7}
          color="#2f6dff"
          centerLabel="On-time Resolution"
          rows={[
            ['Avg. Response Time', '12m 34s', 'down', '18%'],
            ['First Time Fix Rate', '91.2%', 'up', '7%'],
            ['Utilization', '78%', 'down', '6%'],
          ]}
        />
      )
    case 'fleet':
      return (
        <PerfWidget
          title="Graph health"
          value={93}
          color="#34c759"
          status="Healthy"
          centerLabel="Healthy"
          legend={[
            ['Healthy', '84%', '#34c759'],
            ['At-risk', '11%', '#f5a623'],
            ['Failing', '5%', '#ff4d4f'],
          ]}
        />
      )
    case 'audit':
      return (
        <PerfWidget
          title="Audit quality"
          value={96}
          color="#34c759"
          status="Excellent"
          centerLabel="Overall quality"
          legend={[
            ['Evidence captured', '98%', '#34c759'],
            ['Skill coverage', '94%', '#3ba7f0'],
            ['Human feedback', '91%', '#f5a623'],
          ]}
        />
      )
    case 'skills': {
      const learned = skills.length
      const trusted = skills.filter((s) => s.status === 'trusted').length || 8
      const domains = new Set(SKILL_LIBRARY.map((s) => s.domain)).size
      return (
        <div className="overflow-hidden rounded-2xl border border-ink-900/[0.07] bg-paper-50 p-3.5 shadow-card-soft">
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.14em] text-ink-400">
            Skills at a glance
          </div>
          <div className="mt-3 space-y-2.5">
            <GlanceRow icon="✦" value={learned || 1} label="Learned this session" hex="#c77b08" />
            <GlanceRow icon="◆" value={trusted} label="Trusted skills" hex="#34c759" />
            <GlanceRow icon="▣" value={domains} label="Asset domains" hex="#7c5cdb" />
          </div>
          <div className="relative mt-3 h-20 overflow-hidden rounded-xl bg-white">
            <img src={knowledgeCube} alt="" className="absolute inset-0 h-full w-full object-cover" />
          </div>
        </div>
      )
    }
    default:
      // cases / console / media — system status with iso graphic
      return (
        <div className="overflow-hidden rounded-2xl border border-ink-900/[0.07] bg-paper-50 shadow-card-soft">
          <div className="px-3.5 pt-3.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-ink-700">System Status</span>
              <Dot tone="ok" pulse size={7} />
            </div>
            <div className="mt-1 text-[13px] font-semibold text-ok">Operational</div>
            <div className="text-[10.5px] text-ink-400">All systems healthy</div>
          </div>
          <div className="relative mt-1.5 h-[120px] overflow-hidden">
            <img src={isoCube} alt="" className="absolute inset-0 h-full w-full scale-110 object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-paper-50 via-transparent to-transparent" />
          </div>
        </div>
      )
  }
}

function GlanceRow({ icon, value, label, hex }: { icon: string; value: ReactNode; label: string; hex: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[12px]"
        style={{ background: `${hex}16`, color: hex }}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <div className="text-[13px] font-bold leading-none text-ink-900">{value}</div>
        <div className="truncate text-[10px] text-ink-400">{label}</div>
      </div>
    </div>
  )
}

function PerfWidget({
  title,
  value,
  color,
  centerLabel,
  status,
  rows,
  legend,
}: {
  title: string
  value: number
  color: string
  centerLabel: string
  status?: string
  rows?: [string, string, 'up' | 'down', string][]
  legend?: [string, string, string][]
}) {
  return (
    <div className="rounded-2xl border border-ink-900/[0.07] bg-paper-50 p-3.5 shadow-card-soft">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-ink-700">{title}</span>
        <span className="inline-flex items-center gap-1 text-[10px] font-medium text-ok">
          <Dot tone="ok" pulse size={6} />
          {status ?? 'Live'}
        </span>
      </div>
      <div className="mt-2 flex justify-center">
        <Donut
          value={value}
          size={104}
          stroke={9}
          color={color}
          center={
            <>
              <div className="font-display text-[19px] font-bold leading-none text-ink-900">{value}%</div>
              <div className="mt-1 max-w-[68px] text-[8.5px] leading-tight text-ink-400">{centerLabel}</div>
            </>
          }
        />
      </div>
      {rows && (
        <div className="mt-2 space-y-2 border-t border-ink-900/[0.06] pt-2.5">
          {rows.map(([label, val, dir, delta]) => (
            <div key={label}>
              <div className="flex items-center justify-between text-[10.5px] text-ink-400">
                <span className="truncate">{label}</span>
                <span className={dir === 'up' ? 'text-ok' : 'text-ink-400'}>
                  {dir === 'up' ? '↑' : '↓'} {delta}
                </span>
              </div>
              <div className="text-[12px] font-semibold text-ink-900">{val}</div>
            </div>
          ))}
        </div>
      )}
      {legend && (
        <div className="mt-2.5 space-y-1.5 border-t border-ink-900/[0.06] pt-2.5">
          {legend.map(([label, val, hex]) => (
            <div key={label} className="flex items-center gap-2 text-[11px]">
              <span className="h-2 w-2 rounded-full" style={{ background: hex }} />
              <span className="text-ink-500">{label}</span>
              <span className="ml-auto font-medium text-ink-700">{val}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function UserCard() {
  return (
    <button className="m-3 mt-1 flex items-center gap-2.5 rounded-xl border border-ink-900/[0.06] bg-paper-50 px-3 py-2.5 text-left transition-colors hover:bg-paper-100">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-violet text-[12px] font-semibold text-white">
        AR
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[12.5px] font-semibold text-ink-900">Arjun Rao</div>
        <div className="truncate text-[11px] text-ink-400">Operations Lead</div>
      </div>
      <ChevronsUpDown size={14} className="text-ink-400" />
    </button>
  )
}
