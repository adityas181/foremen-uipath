import { useState, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  ArrowUpRight,
  Award,
  BadgeCheck,
  FileCheck2,
  Fingerprint,
  GitBranch,
  Layers,
  Quote,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { useStore } from '../../store/store'
import { Badge, Chip, Empty, Sparkline } from '../../components/ui'
import { SkillFileModal, skillFileExists } from '../../components/SkillFileModal'
import { clsx } from '../../lib/format'
import { TONE_HEX, type Tone } from '../../lib/hues'
import { SKILL_LIBRARY, type LibrarySkill } from '../../data/skillLibrary'
import type { Skill, SkillStatus } from '../../types'
import skillsMd from '../../assets/graphics/skills-md.jpeg'

const STATUS_TONE: Record<SkillStatus, Tone> = {
  candidate: 'warn',
  trusted: 'ok',
  retired: 'muted',
  none: 'muted',
}

export function SkillsTab() {
  const skills = useStore((s) => s.skills)
  const list = Object.values(skills)
  const hasTrusted = list.some((s) => s.status === 'trusted')
  const [openId, setOpenId] = useState<string | null>(null)

  return (
    <div className="space-y-9">
      <SkillsHero
        learned={list.length}
        trusted={list.filter((s) => s.status === 'trusted').length}
        domains={new Set(SKILL_LIBRARY.map((s) => s.domain)).size}
      />

      <LifecycleStrip hasTrusted={hasTrusted} />

      {/* Learned this session */}
      {list.length === 0 ? (
        <div className="panel">
          <Empty
            icon={<Sparkles size={22} />}
            text="Nothing learned this session — run a case to its thumbs-up to write a candidate skill."
          />
        </div>
      ) : (
        <div>
          <SectionLabel>Learned this session</SectionLabel>
          <div className="grid grid-cols-1 gap-5">
            {list.map((skill, i) => (
              <SkillCard key={skill.id} skill={skill} index={i} onView={setOpenId} />
            ))}
          </div>
        </div>
      )}

      <FleetLibrary learnedIds={new Set(list.map((s) => s.id))} onView={setOpenId} />

      <SkillFileModal id={openId} onClose={() => setOpenId(null)} />
    </div>
  )
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div className="mb-4 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-ink-400">
      {children}
    </div>
  )
}

// ── Hero — the semantic-layer banner (skills-md neon graphic) ────────────────
function SkillsHero({ learned, trusted, domains }: { learned: number; trusted: number; domains: number }) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-ink-900/[0.08] bg-[#0a0a12] shadow-card-light">
      <div className="relative grid grid-cols-1 items-stretch lg:grid-cols-[1fr_460px]">
        <div className="p-7 sm:p-9">
          <div className="inline-flex items-center gap-1.5 rounded-md border border-violet/30 bg-violet/[0.12] px-2.5 py-1 font-mono text-[10.5px] font-medium uppercase tracking-[0.18em] text-[#b9a6f0]">
            <Sparkles size={12} /> Semantic layer · governed learning
          </div>
          <h1 className="mt-4 font-display text-[40px] font-bold leading-[1.02] tracking-tight text-white sm:text-[52px]">
            Agent <span className="text-[#9d83ee]">Skills</span>
          </h1>
          <p className="mt-3.5 max-w-lg text-[14px] leading-relaxed text-white/60">
            Every thumbs-up distills a reusable, hard-gated, cited recipe — a{' '}
            <span className="font-mono text-white/85">SKILL.md</span> card. Three approvals promote it to
            trusted.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <HeroStat icon={<Sparkles size={15} />} n={learned} l="Learned this session" />
            <HeroStat icon={<BadgeCheck size={15} />} n={trusted} l="Trusted skills" violet />
            <HeroStat icon={<Layers size={15} />} n={domains} l="Asset domains" />
          </div>
        </div>
        <div className="relative hidden lg:block">
          <img src={skillsMd} alt="Agent Skills — skills.md" className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0a0a12] via-[#0a0a12]/35 to-transparent" />
        </div>
      </div>
    </div>
  )
}

function HeroStat({ icon, n, l, violet }: { icon: ReactNode; n: number; l: string; violet?: boolean }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5">
      <span
        className={clsx(
          'flex h-8 w-8 items-center justify-center rounded-lg',
          violet ? 'bg-violet/20 text-[#b9a6f0]' : 'bg-white/[0.06] text-white/70',
        )}
      >
        {icon}
      </span>
      <div>
        <div className="font-display text-lg font-bold leading-none text-white">{n}</div>
        <div className="mt-0.5 text-[10.5px] text-white/45">{l}</div>
      </div>
    </div>
  )
}

// ── Lifecycle strip — Born → Reused → Promoted → Retired ────────────────────
function LifecycleStrip({ hasTrusted }: { hasTrusted: boolean }) {
  const stages = [
    { label: 'Born', sub: 'candidate', lit: true, icon: <Sparkles size={14} />, hex: '#c77b08' },
    { label: 'Reused', sub: 'matched + approved', lit: true, icon: <GitBranch size={14} />, hex: '#1d84d6' },
    { label: 'Promoted', sub: 'trusted', lit: hasTrusted, icon: <Award size={14} />, hex: '#1aa251' },
    { label: 'Retired', sub: 'superseded', lit: false, icon: <ArrowRight size={14} />, hex: '#697079' },
  ]
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <SectionLabel>
          <Layers size={13} className="text-ink-300" /> Skill lifecycle
        </SectionLabel>
        <span className="mb-4 font-mono text-[11px] text-ink-400">
          Always on · <span className="text-brand-600">Every case</span>
        </span>
      </div>
      <div className="panel -mt-3 flex flex-wrap items-center gap-2.5 p-4">
        {stages.map((s, i) => (
          <div key={s.label} className="flex items-center gap-2.5">
            <div
              className={clsx(
                'flex items-center gap-2.5 rounded-xl border px-3 py-2 transition-all',
                s.lit ? 'border-ink-900/[0.10] bg-white' : 'border-ink-900/[0.06] opacity-40',
              )}
            >
              <span
                className="flex h-7 w-7 items-center justify-center rounded-lg"
                style={{ background: `${s.hex}16`, color: s.hex }}
              >
                {s.icon}
              </span>
              <div className="flex flex-col">
                <span className="text-[12.5px] font-semibold text-ink-900">{s.label}</span>
                <span className="text-[10.5px] text-ink-400">{s.sub}</span>
              </div>
            </div>
            {i < stages.length - 1 && <ArrowRight size={14} className="shrink-0 text-ink-300" />}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Skill card (live learned) — candidate badge, approval bar, 3-col body ────
function SkillCard({ skill, index, onView }: { skill: Skill; index: number; onView: (id: string) => void }) {
  const tone = STATUS_TONE[skill.status]
  const hex = TONE_HEX[tone]
  const hard: [string, string][] = (
    [
      ['equipment_class', skill.match_key.equipment_class],
      ['component', skill.match_key.component],
      ['failure_mode', skill.match_key.failure_mode],
      ['environment', skill.match_key.environment],
      ['spec', skill.match_key.spec],
      ['capacity_band', skill.match_key.capacity_band],
    ] as [string, string | undefined][]
  ).filter((kv): kv is [string, string] => Boolean(kv[1]))

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="relative overflow-hidden rounded-2xl border border-ink-900/[0.07] bg-white p-6 pl-7 shadow-card-flat"
    >
      <span className="absolute inset-y-0 left-0 w-1" style={{ background: hex }} />

      {/* Header: status badge + mono id */}
      <div className="flex items-center gap-2.5">
        <Badge tone={tone} className="!uppercase !tracking-wide">
          {skill.status}
        </Badge>
        <span className="font-mono text-[14px] font-semibold text-ink-900">{skill.id}</span>
      </div>

      {/* Diagnosis + approval progress */}
      <div className="mt-4 grid grid-cols-1 gap-x-8 gap-y-4 lg:grid-cols-[1fr_300px]">
        <div className="text-[14px] leading-relaxed text-ink-700">{skill.diagnosis}</div>
        <div className="lg:pt-1">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-ink-500">Approval progress</span>
            <span className="font-mono text-[12px] font-semibold text-ink-700">
              {skill.approve_count} / 3
            </span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-ink-900/[0.07]">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${(Math.min(skill.approve_count, 3) / 3) * 100}%`,
                background: hex,
              }}
            />
          </div>
        </div>
      </div>

      {/* Three-column lower area: RECIPE | FINGERPRINT | FROM */}
      <div className="mt-5 grid grid-cols-1 gap-5 border-t border-ink-900/[0.06] pt-5 lg:grid-cols-3">
        {/* RECIPE */}
        <div>
          <div className="text-[10.5px] uppercase tracking-wide text-ink-400">Recipe</div>
          <ol className="mt-2.5 space-y-1.5">
            {skill.recipe.map((step, i) => (
              <li
                key={i}
                className="flex gap-2.5 rounded-lg border border-ink-900/[0.06] bg-paper-50 px-2.5 py-1.5"
              >
                <span className="font-mono text-[11px] font-semibold text-ink-400">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="font-mono text-[11.5px] leading-relaxed text-ink-700">{step}</span>
              </li>
            ))}
          </ol>
        </div>

        {/* FINGERPRINT */}
        <div>
          <div className="flex items-center gap-1.5 text-[10.5px] uppercase tracking-wide text-ink-400">
            <Fingerprint size={12} /> Fingerprint
            <span className="ml-auto rounded-sm bg-ink-900/[0.06] px-1.5 py-0.5 text-[8.5px] font-semibold uppercase tracking-wide text-ink-500">
              hard
            </span>
          </div>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {hard.map(([k, v]) => (
              <Chip key={k} className="!gap-1">
                <span className="text-ink-400">{k}</span>
                <span className="font-mono text-ink-700">{v}</span>
              </Chip>
            ))}
          </div>
        </div>

        {/* FROM */}
        <div>
          <div className="text-[10.5px] uppercase tracking-wide text-ink-400">From</div>
          <div className="mt-2.5 space-y-2">
            {skill.source_cases.map((sc, i) => (
              <div key={sc} className="space-y-1">
                <Chip className="font-mono">{sc}</Chip>
                {skill.citations[i] && (
                  <div className="flex items-center gap-1.5 font-mono text-[10.5px] text-ink-500">
                    <Quote size={11} className="shrink-0 text-ink-400" />
                    {skill.citations[i]}
                  </div>
                )}
              </div>
            ))}
            {skill.citations.slice(skill.source_cases.length).map((cite) => (
              <div key={cite} className="flex items-center gap-1.5 font-mono text-[10.5px] text-ink-500">
                <Quote size={11} className="shrink-0 text-ink-400" />
                {cite}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer: Review skill button + last-seen caption */}
      <div className="mt-5 flex items-center justify-between border-t border-ink-900/[0.06] pt-4">
        {skillFileExists(skill.id) ? (
          <button
            onClick={() => onView(skill.id)}
            className="group inline-flex items-center gap-1.5 rounded-lg border border-brand-500/40 bg-white px-3.5 py-1.5 text-[12px] font-semibold text-brand-600 transition-all hover:border-brand-500 hover:bg-brand-500/[0.04]"
          >
            Review skill
            <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
          </button>
        ) : (
          <span />
        )}
        <span className="font-mono text-[11px] text-ink-400">Last seen 11:04 AM</span>
      </div>
    </motion.div>
  )
}

// ── Fleet skill library — grid + search/filters + governance rail ───────────
const LIB_STATUS_TONE: Record<LibrarySkill['status'], Tone> = {
  candidate: 'warn',
  trusted: 'ok',
  retired: 'muted',
}

const DOMAIN_FILTERS = ['All', 'Solar', 'Telecom', 'HVAC', 'Rail', 'Power', 'Data Center']

function FleetLibrary({ learnedIds, onView }: { learnedIds: Set<string>; onView: (id: string) => void }) {
  const items = SKILL_LIBRARY.filter((s) => !learnedIds.has(s.id))
  if (items.length === 0) return null
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <SectionLabel>Fleet skill library</SectionLabel>
          <p className="-mt-2 max-w-2xl text-[13.5px] leading-relaxed text-ink-500">
            One learning loop, every asset class. The same hard-gated recipe format spans solar, telecom,
            rotating plant, HVAC, rail, power and water.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-ink-900/[0.10] bg-white px-3 py-1.5 text-[12px] text-ink-400">
            <Search size={13} />
            <span>Search skills…</span>
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg border border-ink-900/[0.10] bg-white px-3 py-1.5 text-[12px] font-medium text-ink-600 transition-colors hover:border-ink-900/25"
          >
            <SlidersHorizontal size={13} /> Filters
          </button>
        </div>
      </div>

      {/* Domain filter chips (presentational) */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        {DOMAIN_FILTERS.map((d, i) => (
          <span
            key={d}
            className={clsx(
              'cursor-default rounded-full px-3 py-1 text-[11.5px] font-medium transition-colors',
              i === 0
                ? 'bg-ink-900 text-white'
                : 'border border-ink-900/[0.10] bg-white text-ink-500 hover:text-ink-900',
            )}
          >
            {d}
          </span>
        ))}
        <span className="inline-flex cursor-default items-center gap-1 rounded-full border border-ink-900/[0.10] bg-white px-3 py-1 text-[11.5px] font-medium text-ink-500">
          Domain
          <ArrowRight size={11} className="rotate-90 text-ink-400" />
        </span>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_300px]">
        {/* Library grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {items.map((s, i) => (
            <motion.button
              key={s.id}
              type="button"
              onClick={() => onView(s.id)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="group flex flex-col rounded-2xl border border-ink-900/[0.07] bg-white p-5 text-left shadow-card-flat transition-all hover:-translate-y-0.5 hover:border-ink-900/[0.14] hover:shadow-card-light"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12px] font-medium text-ink-500">{s.domain}</span>
                <Badge tone={LIB_STATUS_TONE[s.status]}>{s.status}</Badge>
              </div>
              <div className="mt-2.5 font-mono text-[12.5px] font-semibold text-ink-900">{s.id}</div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Chip className="!gap-1">
                  <span className="text-ink-400">class</span>
                  <span className="font-mono text-ink-700">{s.equipment_class}</span>
                </Chip>
                <Chip className="!gap-1">
                  <span className="text-ink-400">mode</span>
                  <span className="font-mono text-ink-700">{s.failure_mode}</span>
                </Chip>
              </div>
              <div className="mt-2.5 flex-1 text-[12.5px] leading-relaxed text-ink-500">{s.diagnosis}</div>
              <div className="mt-4 flex items-center gap-1.5 border-t border-ink-900/[0.06] pt-3 text-[11px] text-ink-400">
                <span className="font-medium text-ink-600 transition-colors group-hover:text-brand-600">
                  View file
                </span>
                <ArrowRight
                  size={12}
                  className="text-ink-400 transition-transform group-hover:translate-x-0.5"
                />
              </div>
            </motion.button>
          ))}
        </div>

        {/* Right rail: governance explainer + trust trend */}
        <div className="space-y-5">
          <GovernanceCard />
          <TrustTrendCard />
        </div>
      </div>
    </div>
  )
}

// ── Governed. Cited. Trusted. — four-point explainer ────────────────────────
function GovernanceCard() {
  const points = [
    { icon: <ShieldCheck size={15} />, t: 'Hard-gated', d: 'Quality before trust' },
    { icon: <Quote size={15} />, t: 'Cited', d: 'Every fact is sourced' },
    { icon: <GitBranch size={15} />, t: 'Versioned', d: 'Change with traceability' },
    { icon: <BadgeCheck size={15} />, t: 'Trusted by design', d: '3-approval promotion' },
  ]
  return (
    <div className="section-card p-5">
      <div className="flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-ink-900/[0.08] bg-paper-50 text-brand-600">
          <ShieldCheck size={16} />
        </span>
        <h3 className="text-[14px] font-semibold tracking-tight text-ink-900">Governed. Cited. Trusted.</h3>
      </div>
      <p className="mt-3 text-[12px] leading-relaxed text-ink-500">
        Every skill is hard-gated, versioned and backed by evidence. That's how we keep the brain reliable —
        at scale.
      </p>
      <div className="mt-4 space-y-3">
        {points.map((p) => (
          <div key={p.t} className="flex items-start gap-2.5">
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-paper-50 text-ink-500 ring-1 ring-inset ring-ink-900/[0.05]">
              {p.icon}
            </span>
            <div>
              <div className="text-[12.5px] font-semibold text-ink-900">{p.t}</div>
              <div className="text-[11px] text-ink-400">{p.d}</div>
            </div>
          </div>
        ))}
      </div>
      <a
        href="#"
        className="group mt-4 inline-flex items-center gap-1.5 border-t border-ink-900/[0.06] pt-3 text-[12px] font-medium text-brand-600"
      >
        Learn about our skills framework
        <ArrowUpRight size={13} className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
      </a>
    </div>
  )
}

// ── Trust score trend — big number + sparkline ──────────────────────────────
const TRUST_TREND = [78, 80, 79, 83, 86, 84, 89, 91, 90, 94, 96]

function TrustTrendCard() {
  return (
    <div className="section-card p-5">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-400">
          <FileCheck2 size={13} /> Trust score trend
        </span>
        <span className="font-mono text-[10.5px] text-ink-400">This session</span>
      </div>
      <div className="mt-3 flex items-baseline gap-2.5">
        <span className="font-display text-[40px] font-bold leading-none tracking-tightest text-ink-900">
          96%
        </span>
        <span className="inline-flex items-center gap-0.5 text-[12px] font-semibold text-ok">
          <TrendingUp size={13} /> 8%
        </span>
      </div>
      <div className="mt-4">
        <Sparkline data={TRUST_TREND} color={TONE_HEX.info} width={258} height={70} />
      </div>
    </div>
  )
}
