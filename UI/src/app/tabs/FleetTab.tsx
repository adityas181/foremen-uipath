import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Boxes,
  ChevronRight,
  Database,
  Download,
  GitBranch,
  GitFork,
  HardHat,
  Layers,
  Lightbulb,
  MapPin,
  Network,
  Package,
  Save,
  ShieldAlert,
  ShieldCheck,
  Workflow,
  Zap,
} from 'lucide-react'
import { useStore } from '../../store/store'
import { FleetGraph } from '../../components/FleetGraph'
import { Badge, Chip, Empty, PanelHeader } from '../../components/ui'
import { inrCompact } from '../../lib/format'
import { TONE_HEX, type Tone } from '../../lib/hues'
import { NEO4J_FLEET } from '../../data/neo4jFleet'
import type { CaseView, FleetFactor, FleetNode } from '../../types'

const STATUS_TONE: Record<string, Tone> = {
  corroded: 'danger',
  failing: 'danger',
  at_risk: 'warn',
  healthy: 'ok',
}
const STATUS_LABEL: Record<string, string> = {
  corroded: 'corroded',
  failing: 'failing',
  at_risk: 'at-risk',
  healthy: 'healthy',
}

// node-type → icon, used by the path-to-root chain (presentational)
const TYPE_NAME: Record<string, string> = {
  crew: 'install crew',
  part_lot: 'part lot',
  asset: 'asset',
  batch: 'batch',
  site: 'site',
  vendor: 'vendor',
  cluster: 'cluster',
  region: 'region',
  equipment_class: 'equip class',
}

export function FleetTab() {
  const c = useStore((s) => (s.activeCaseId ? s.cases[s.activeCaseId] : null))
  if (!c) return <Empty text="No active case — press play in the top bar." />

  // Live blast-radius if the Fleet agent emitted it; otherwise the hard-coded
  // snapshot of the real Neo4j estate graph (e1dfbbbd).
  const fleet = c.fleet ?? NEO4J_FLEET
  // Also render the FULL Neo4j estate as its own panel — but only when the case
  // emitted a blast-radius (otherwise `fleet` already IS the full estate).
  const hasCaseFleet = !!c.fleet
  const unit = fleet.unitNoun ?? 'site'
  const nodeById = Object.fromEntries(fleet.nodes.map((n) => [n.id, n])) as Record<string, FleetNode>

  // which hub(s) each affected asset propagates through (for the "via" column)
  const viaByAsset = new Map<string, string[]>()
  fleet.edges
    .filter((e) => e.hot)
    .forEach((e) => {
      const arr = viaByAsset.get(e.from) ?? []
      const hub = nodeById[e.to]
      if (hub) arr.push(hub.label)
      viaByAsset.set(e.from, arr)
    })

  const exposure = fleet.exposurePerHr ?? c.investigation?.exposure_per_hr

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      {/* ── Hero + KPI band ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
        <div className="lg:col-span-5">
          {fleet.systemic && (
            <div className="mb-4 inline-flex">
              <Badge tone="danger">
                <ShieldAlert size={11} /> systemic · {fleet.affected.length} {unit}s
              </Badge>
            </div>
          )}
          <div className="inline-flex items-center rounded-md border border-ink-900/[0.08] bg-paper-50 px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-ink-500">
            Knowledge Graph · Neo4j
          </div>
          <h1 className="mt-4 font-serif text-[31px] font-normal leading-[1.07] tracking-[-0.012em] text-ink-900 sm:text-[40px]">
            One fault, the whole estate
          </h1>
          <p className="mt-3.5 max-w-md text-[15px] leading-relaxed text-ink-500">
            The connection graph finds every {unit} at risk — and the shared root a flat query
            can&apos;t see.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 lg:col-span-7 xl:grid-cols-4">
          <KpiCard
            icon={<Database size={16} />}
            tone="info"
            eyebrow="Same-batch query"
            value={String(fleet.sqlVsGraph?.sqlFound ?? 0)}
            unitLabel={`real ${unit}s found`}
            caption={fleet.sqlVsGraph?.sqlNote ?? `WHERE batch = X → no real burns`}
          />
          <KpiCard
            icon={<GitFork size={16} />}
            tone="danger"
            eyebrow="At-risk strings"
            value={String(fleet.affected.length)}
            unitLabel={`${unit}s at risk`}
            captionStrong="Across 3 module batches"
            caption="MOD-LOT-A/B/C"
          />
          <KpiCard
            icon={<ShieldCheck size={16} />}
            tone="info"
            eyebrow="Graph summary"
            value={String(fleet.nodes.length)}
            unitLabel="nodes in graph"
            captionStrong={`${fleet.edges.length} total edges`}
            caption="connections ›"
          />
          {exposure != null && (
            <KpiCard
              icon={<Zap size={16} />}
              tone="warn"
              eyebrow="Exposure at risk"
              value={inrCompact(exposure) + '/hr'}
              unitLabel={(fleet.exposureLabel ?? 'generation revenue at risk').toLowerCase()}
              captionStrong="If unresolved"
              caption="exposure per hour"
            />
          )}
        </div>
      </div>

      {c.graphNote && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2.5 rounded-xl border border-ok/30 bg-ok/[0.07] px-4 py-3 text-[12.5px] text-ink-800"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ok/15 text-ok">
            <Network size={15} />
          </span>
          <span>
            <span className="font-semibold text-ink-900">Graph updated · learned</span> — {c.graphNote}
          </span>
        </motion.div>
      )}

      {/* ── Graph (left) + common-cause / criticality (right) ───────────────── */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <div className="panel p-5">
            <PanelHeader
              title="Multi-factor blast-radius"
              icon={<Network size={15} />}
              right={
                <Chip>
                  {fleet.nodes.length} nodes · {fleet.edges.length} edges
                </Chip>
              }
              className="!px-0 !py-0 pb-4"
            />
            <FleetGraph nodes={fleet.nodes} edges={fleet.edges} />
            <NodeLegend nodes={fleet.nodes} />
          </div>
        </div>

        <div className="space-y-5 lg:col-span-5">
          {fleet.rootCause && fleet.rootCause.length > 0 && <CommonCause factors={fleet.rootCause} />}
          {fleet.criticality && fleet.criticality.length > 0 && (
            <Criticality factors={fleet.criticality} />
          )}
          {!fleet.rootCause && !fleet.criticality && <AffectedList c={c} viaByAsset={viaByAsset} />}
        </div>
      </div>

      {/* ── Full Neo4j estate graph (the whole connected estate, not just this case) ── */}
      {hasCaseFleet && <FullEstateGraph />}

      {/* ── Bottom row: strings · path-to-root · insights · export ──────────── */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        {(fleet.rootCause || fleet.criticality) && (
          <div className="lg:col-span-3">
            <AffectedList c={c} viaByAsset={viaByAsset} compact />
          </div>
        )}
        <div className="lg:col-span-4">
          <PathToRoot fleet={fleet} nodeById={nodeById} />
        </div>
        <div className="lg:col-span-3">
          <GraphInsights fleet={fleet} />
        </div>
        <div className="lg:col-span-2">
          <ExportExplore />
        </div>
      </div>
    </motion.div>
  )
}

// ── Full Neo4j estate graph — every node, not just the case blast-radius ─────
function FullEstateGraph() {
  return (
    <div className="panel p-5">
      <PanelHeader
        title="Full estate graph"
        icon={<Boxes size={15} />}
        right={
          <div className="flex items-center gap-2.5">
            <Chip>Neo4j · e1dfbbbd</Chip>
            <Chip>
              {NEO4J_FLEET.nodes.length} nodes · {NEO4J_FLEET.edges.length} edges
            </Chip>
          </div>
        }
        className="!px-0 !py-0 pb-4"
      />
      <p className="-mt-1 mb-4 max-w-2xl text-[12.5px] leading-relaxed text-ink-500">
        The complete connected estate from the knowledge graph — every asset, batch, install
        crew, part lot, site, region and vendor. The case blast-radius above is one sub-graph
        of this whole.
      </p>
      <FleetGraph nodes={NEO4J_FLEET.nodes} edges={NEO4J_FLEET.edges} aspect="aspect-[16/9]" />
      <NodeLegend nodes={NEO4J_FLEET.nodes} />
    </div>
  )
}

// ── KPI card (icon tile + big value + unit label + tiny caption) ─────────────
function KpiCard({
  icon,
  tone,
  eyebrow,
  value,
  unitLabel,
  captionStrong,
  caption,
}: {
  icon: ReactNode
  tone: Tone
  eyebrow: string
  value: string
  unitLabel: string
  captionStrong?: string
  caption?: string
}) {
  const hex = TONE_HEX[tone]
  return (
    <div className="card-raised flex flex-col rounded-2xl border border-ink-900/[0.08] bg-white p-4 shadow-card-soft">
      <div className="flex items-start gap-3">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
          style={{ background: `${hex}14`, color: hex, border: `1px solid ${hex}2e` }}
        >
          {icon}
        </span>
        <div className="min-w-0">
          <div className="text-[9.5px] font-semibold uppercase tracking-[0.12em] text-ink-400">
            {eyebrow}
          </div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span
              className="font-display text-[24px] font-bold leading-none tracking-tightest"
              style={{ color: hex }}
            >
              {value}
            </span>
          </div>
          <div className="mt-1 text-[11px] leading-snug text-ink-500">{unitLabel}</div>
        </div>
      </div>
      <div className="mt-3 border-t border-ink-900/[0.06] pt-2.5">
        {captionStrong && (
          <div className="text-[10.5px] font-semibold" style={{ color: hex }}>
            {captionStrong}
          </div>
        )}
        {caption && (
          <div className="mt-0.5 truncate font-mono text-[10px] leading-snug text-ink-400">
            {caption}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Common-cause: the shared upstream root, ranked by failures explained ─────
function CommonCause({ factors }: { factors: FleetFactor[] }) {
  return (
    <div className="panel p-5">
      <PanelHeader
        title="Common-cause root(s)"
        icon={<Workflow size={15} />}
        right={<Chip>not a column SQL has</Chip>}
        className="!px-0 !py-0 pb-4"
      />
      <div className="space-y-2.5">
        {factors.map((f) => (
          <div key={f.factor} className="rounded-xl border border-danger/20 bg-danger/[0.04] p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[13px] font-semibold text-ink-900">{f.factor}</span>
                <Chip className="!text-[9.5px]">{f.factorType}</Chip>
              </div>
              <Badge tone="danger">explains {f.count}</Badge>
            </div>
            {f.note && (
              <div className="mt-1.5 text-[11.5px] leading-relaxed text-ink-500">{f.note}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Criticality: degree centrality — the single-points-of-failure to harden ──
function Criticality({ factors }: { factors: FleetFactor[] }) {
  const max = Math.max(...factors.map((f) => f.count), 1)
  return (
    <div className="panel p-5">
      <PanelHeader
        title="Criticality ranking"
        icon={<ShieldAlert size={15} />}
        right={<Chip>harden first</Chip>}
        className="!px-0 !py-0 pb-4"
      />
      <div className="space-y-3">
        {factors.map((f, i) => {
          const tone = i === 0 ? '#e23b3b' : i === 1 ? '#c77b08' : '#5b6573'
          return (
            <div key={f.factor}>
              <div className="flex items-center justify-between text-[12px]">
                <span className="font-mono font-semibold text-ink-800">{f.factor}</span>
                <span className="text-ink-500">
                  {f.count} <span className="text-ink-400">exposed</span>
                </span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-ink-900/[0.05]">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${(f.count / max) * 100}%`,
                    background: tone,
                    boxShadow: `0 0 10px ${tone}66`,
                  }}
                />
              </div>
              {f.note && <div className="mt-1 text-[10.5px] text-ink-400">{f.note}</div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Strings in the blast-radius (id + via + Failing/At-risk badge) ───────────
function AffectedList({
  c,
  viaByAsset,
  compact,
}: {
  c: CaseView
  viaByAsset: Map<string, string[]>
  compact?: boolean
}) {
  const fleet = c.fleet ?? NEO4J_FLEET
  const nodeById = Object.fromEntries(fleet.nodes.map((n) => [n.id, n])) as Record<string, FleetNode>
  const list = compact ? fleet.affected.slice(0, 3) : fleet.affected
  const atRisk = fleet.affected.length
  return (
    <div className="panel flex h-full flex-col p-5">
      <PanelHeader
        title={`${fleet.unitNoun ?? 'Unit'}s in the blast-radius`}
        icon={<MapPin size={15} />}
        right={<Chip>{atRisk} at-risk</Chip>}
        className="!px-0 !py-0 pb-4"
      />
      <div className="space-y-2">
        {list.map((id) => {
          const node = nodeById[id]
          const status = node?.status ?? 'at_risk'
          const via = viaByAsset.get(id)
          return (
            <div
              key={id}
              className="flex items-center justify-between gap-3 rounded-xl border border-ink-900/[0.07] bg-ink-900/[0.02] px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <MapPin size={13} className="shrink-0 text-ink-500" />
                  <span className="font-mono text-[12.5px] font-medium text-ink-900">
                    {node?.label ?? id}
                  </span>
                </div>
                {via && via.length > 0 && (
                  <div className="mt-0.5 truncate pl-[21px] text-[10.5px] text-ink-400">
                    via {via.join(' + ')}
                  </div>
                )}
              </div>
              <Badge tone={STATUS_TONE[status] ?? 'muted'}>{STATUS_LABEL[status] ?? status}</Badge>
            </div>
          )
        })}
      </div>
      {compact && fleet.affected.length > list.length && (
        <button
          type="button"
          className="mt-3 inline-flex items-center gap-1 self-start text-[11.5px] font-semibold text-brand-600 transition-colors hover:text-brand-500"
        >
          View all {fleet.affected.length} {fleet.unitNoun ?? 'unit'}s
          <ArrowRight size={13} />
        </button>
      )}
    </div>
  )
}

// ── Path to root: a representative left-to-right chain through the hub nodes ──
function PathToRoot({
  fleet,
  nodeById,
}: {
  fleet: NonNullable<CaseView['fleet']>
  nodeById: Record<string, FleetNode>
}) {
  // origin = first affected string; its hot edges lead to the hub(s); end on a batch
  const originId = fleet.affected[0]
  const origin = originId ? nodeById[originId] : undefined
  const hotFromOrigin = fleet.edges.filter((e) => e.hot && e.from === originId)
  const hubs = hotFromOrigin
    .map((e) => nodeById[e.to])
    .filter((n): n is FleetNode => !!n)
  // a representative module batch the origin sits in (the false signal)
  const batchEdge = fleet.edges.find((e) => !e.hot && e.from === originId)
  const batch = batchEdge ? nodeById[batchEdge.to] : undefined

  const chain: FleetNode[] = [
    ...(origin ? [origin] : []),
    ...hubs,
    ...(batch ? [batch] : []),
  ]
  if (chain.length < 2) return null

  return (
    <div className="panel flex h-full flex-col p-5">
      <PanelHeader
        title="Path to root (example)"
        icon={<GitBranch size={15} />}
        right={<Chip>Depth {chain.length - 1}</Chip>}
        className="!px-0 !py-0 pb-4"
      />
      <div className="flex flex-wrap items-start gap-y-3">
        {chain.map((n, i) => (
          <div key={n.id} className="flex items-start">
            <PathNode node={n} />
            {i < chain.length - 1 && (
              <ChevronRight size={16} className="mx-1.5 mt-3 shrink-0 text-ink-300" />
            )}
          </div>
        ))}
      </div>
      <div className="mt-auto flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-ink-900/[0.06] pt-3 text-[10.5px] text-ink-400">
        <span className="font-semibold text-ink-500">Depth {chain.length - 1}:</span>
        {chain.map((n, i) => (
          <span key={n.id} className="flex items-center gap-2">
            <span className="font-mono">{TYPE_NAME[n.type] ?? n.type}</span>
            {i < chain.length - 1 && <ArrowRight size={11} className="text-ink-300" />}
          </span>
        ))}
      </div>
    </div>
  )
}

const PATH_ICON: Record<string, typeof MapPin> = {
  crew: HardHat,
  part_lot: Package,
  batch: Layers,
  asset: Boxes,
}

function PathNode({ node }: { node: FleetNode }) {
  const tone = STATUS_TONE[node.status ?? 'at_risk'] ?? 'muted'
  const hex = TONE_HEX[tone]
  const Icon = PATH_ICON[node.type] ?? Boxes
  return (
    <div className="flex w-[64px] flex-col items-center text-center">
      <span
        className="flex h-10 w-10 items-center justify-center rounded-2xl"
        style={{ background: `${hex}14`, color: hex, border: `1px solid ${hex}40` }}
      >
        <Icon size={17} strokeWidth={2.1} />
      </span>
      <span className="mt-1.5 max-w-full truncate font-mono text-[10px] font-semibold text-ink-800">
        {node.label}
      </span>
      <span className="text-[8px] uppercase tracking-wide text-ink-400">
        {TYPE_NAME[node.type] ?? node.type}
      </span>
    </div>
  )
}

// ── Graph insights: 2-3 bullets derived from the live data ───────────────────
function GraphInsights({ fleet }: { fleet: NonNullable<CaseView['fleet']> }) {
  const roots = fleet.rootCause?.length ?? 0
  const atRisk = fleet.affected.length
  const healthyAssets = fleet.nodes.filter(
    (n) => n.type === 'asset' && n.status === 'healthy',
  )
  const insights: { strong: string; rest: string }[] = []
  if (roots > 0) {
    insights.push({
      strong: `${roots} root cause node${roots === 1 ? '' : 's'}`,
      rest: ` driving ${atRisk} at-risk strings`,
    })
  }
  insights.push({
    strong: `${atRisk} assets`,
    rest: ' impacted across 3 module batches',
  })
  if (healthyAssets.length > 0) {
    insights.push({
      strong: `1 healthy string in MOD-LOT-A`,
      rest: ' proves the issue is not batch-wide',
    })
  }
  return (
    <div className="panel flex h-full flex-col p-5">
      <PanelHeader
        title="Graph insights"
        icon={<Lightbulb size={15} />}
        className="!px-0 !py-0 pb-4"
      />
      <div className="space-y-3.5">
        {insights.map((ins, i) => (
          <div key={i} className="flex items-start gap-2.5">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-brand-500/10 font-display text-[11px] font-bold text-brand-600">
              {i + 1}
            </span>
            <p className="text-[12px] leading-relaxed text-ink-500">
              <span className="font-semibold text-ink-900">{ins.strong}</span>
              {ins.rest}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Export & explore (presentational action rows) ───────────────────────────
function ExportExplore() {
  const rows = [
    { icon: <Download size={15} />, label: 'Export graph (CSV)' },
    { icon: <Network size={15} />, label: 'Open in Neo4j Browser' },
    { icon: <Save size={15} />, label: 'Save view' },
  ]
  return (
    <div className="panel flex h-full flex-col p-5">
      <PanelHeader
        title="Export & explore"
        icon={<Boxes size={15} />}
        className="!px-0 !py-0 pb-4"
      />
      <div className="flex flex-col gap-1.5">
        {rows.map((r) => (
          <button
            key={r.label}
            type="button"
            className="group flex items-center gap-2.5 rounded-lg px-2 py-2 text-left text-[12px] font-medium text-ink-600 transition-colors hover:bg-ink-900/[0.03] hover:text-ink-900"
          >
            <span className="text-ink-400 transition-colors group-hover:text-brand-600">
              {r.icon}
            </span>
            {r.label}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Node legend under the graph ──────────────────────────────────────────────
function NodeLegend({ nodes }: { nodes: FleetNode[] }) {
  const types = Array.from(new Set(nodes.map((n) => n.type)))
  return (
    <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-ink-900/[0.07] pt-4">
      <LegendDot color="#e23b3b" label="failing" />
      <LegendDot color="#c77b08" label="at-risk" />
      <LegendDot color="#1aa251" label="healthy" />
      <span className="text-ink-300">·</span>
      <span className="text-[11px] text-ink-400">
        nodes: {types.map((t) => TYPE_NAME[t] ?? t).join(' · ')}
      </span>
      <span className="ml-auto text-[10.5px] text-ink-300">hover a node to trace its links</span>
    </div>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2 text-[11.5px] text-ink-500">
      <span
        className="h-2 w-2 rounded-full"
        style={{ background: color, boxShadow: `0 0 8px ${color}` }}
      />
      {label}
    </div>
  )
}
