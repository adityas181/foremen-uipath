import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Boxes,
  Building2,
  Cpu,
  Factory,
  Globe,
  HardHat,
  Layers,
  MapPin,
  Package,
} from 'lucide-react'
import type { FleetEdge, FleetNode, FleetNodeType } from '../types'
import { clsx } from '../lib/format'

const STATUS_COLOR: Record<string, string> = {
  corroded: '#e23b3b',
  failing: '#e23b3b',
  at_risk: '#c77b08',
  healthy: '#1aa251',
}

function nodeColor(n?: FleetNode): string {
  if (n?.status && STATUS_COLOR[n.status]) return STATUS_COLOR[n.status]
  return '#5b6573'
}

const NODE_ICON: Record<FleetNodeType, typeof MapPin> = {
  site: MapPin,
  batch: Layers,
  vendor: Factory,
  cluster: Building2,
  crew: HardHat,
  part_lot: Package,
  asset: Cpu,
  region: Globe,
  equipment_class: Boxes,
}

const TYPE_LABEL: Record<FleetNodeType, string> = {
  site: 'site',
  batch: 'batch',
  vendor: 'vendor',
  cluster: 'cluster',
  crew: 'install crew',
  part_lot: 'part lot',
  asset: 'asset',
  region: 'region',
  equipment_class: 'equip class',
}

// ── Layout ───────────────────────────────────────────────────────────────────
// Fruchterman–Reingold force layout, seeded from each node's incoming x/y and
// relaxed so connected nodes never pile up. The live blast-radius payload often
// stacks the root asset and its hubs on nearly the same spot; this spreads them
// and keeps edges reading cleanly. A graph that is already well laid out (the
// baked Neo4j estate) is near equilibrium and barely moves. Deterministic (no
// randomness) → stable across renders; the caller memoises it.
function computeLayout(
  nodes: FleetNode[],
  edges: FleetEdge[],
): Record<string, { x: number; y: number }> {
  const n = nodes.length
  const out: Record<string, { x: number; y: number }> = {}
  if (n === 0) return out
  if (n === 1) {
    out[nodes[0].id] = { x: 50, y: 50 }
    return out
  }
  const ids = nodes.map((d) => d.id)
  const pos: Record<string, [number, number]> = {}
  nodes.forEach((d, i) => {
    // seed from incoming coords (0–100 → unit square), else spread on a circle
    const sx = Number.isFinite(d.x) ? d.x / 100 : 0.5 + 0.4 * Math.cos((2 * Math.PI * i) / n)
    const sy = Number.isFinite(d.y) ? d.y / 100 : 0.5 + 0.4 * Math.sin((2 * Math.PI * i) / n)
    pos[d.id] = [sx, sy]
  })
  const k = 1 / Math.sqrt(n) // ideal edge length in the unit square
  const eps = 1e-4
  const iters = 300
  for (let it = 0; it < iters; it++) {
    const disp: Record<string, [number, number]> = {}
    ids.forEach((id) => (disp[id] = [0, 0]))
    for (let a = 0; a < n; a++) {
      for (let b = a + 1; b < n; b++) {
        const A = ids[a]
        const B = ids[b]
        let dx = pos[A][0] - pos[B][0]
        let dy = pos[A][1] - pos[B][1]
        const dist = Math.hypot(dx, dy) || eps
        const f = (k * k) / dist // repulsion
        dx = (dx / dist) * f
        dy = (dy / dist) * f
        disp[A][0] += dx
        disp[A][1] += dy
        disp[B][0] -= dx
        disp[B][1] -= dy
      }
    }
    edges.forEach((e) => {
      if (!pos[e.from] || !pos[e.to]) return
      let dx = pos[e.from][0] - pos[e.to][0]
      let dy = pos[e.from][1] - pos[e.to][1]
      const dist = Math.hypot(dx, dy) || eps
      const f = (dist * dist) / k // attraction
      dx = (dx / dist) * f
      dy = (dy / dist) * f
      disp[e.from][0] -= dx
      disp[e.from][1] -= dy
      disp[e.to][0] += dx
      disp[e.to][1] += dy
    })
    const t = 0.1 * (1 - it / iters) // cool down
    ids.forEach((id) => {
      const [dx, dy] = disp[id]
      const len = Math.hypot(dx, dy) || 1e-9
      pos[id][0] += (dx / len) * Math.min(len, t)
      pos[id][1] += (dy / len) * Math.min(len, t)
    })
  }
  // normalise into a padded 0–100 box (extra room so labels don't clip the edge)
  const xs = ids.map((id) => pos[id][0])
  const ys = ids.map((id) => pos[id][1])
  const mnx = Math.min(...xs)
  const mxx = Math.max(...xs)
  const mny = Math.min(...ys)
  const myy = Math.max(...ys)
  const padX = 9
  const padY = 13
  ids.forEach((id) => {
    out[id] = {
      x: padX + ((pos[id][0] - mnx) / (mxx - mnx || 1)) * (100 - 2 * padX),
      y: padY + ((pos[id][1] - mny) / (myy - mny || 1)) * (100 - 2 * padY),
    }
  })
  return out
}

export function FleetGraph({
  nodes,
  edges,
  className,
  aspect = 'aspect-[4/3]',
}: {
  nodes: FleetNode[]
  edges: FleetEdge[]
  className?: string
  aspect?: string
}) {
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]))
  const [hover, setHover] = useState<string | null>(null)
  // Re-layout in the browser (seeded from incoming coords) so nodes never pile
  // up and the edges read cleanly. Memoised on a signature of the graph so it
  // only recomputes when the nodes/edges actually change.
  const sig =
    nodes.map((n) => `${n.id}:${Math.round(n.x)},${Math.round(n.y)}`).join('|') +
    '#' +
    edges.map((e) => `${e.from}>${e.to}`).join('|')
  const layout = useMemo(() => computeLayout(nodes, edges), [sig]) // eslint-disable-line react-hooks/exhaustive-deps
  const pos = (id: string) => layout[id] ?? { x: byId[id]?.x ?? 50, y: byId[id]?.y ?? 50 }
  // Big estate graphs (e.g. the full Neo4j snapshot): shrink nodes and only
  // label the roots + problem nodes (others reveal their label on hover).
  const dense = nodes.length > 18

  // which node ids are connected to the hovered one (for the trace highlight)
  const lit = new Set<string>()
  if (hover) {
    lit.add(hover)
    edges.forEach((e) => {
      if (e.from === hover) lit.add(e.to)
      if (e.to === hover) lit.add(e.from)
    })
  }
  const isLit = (id: string) => !hover || lit.has(id)
  const edgeLit = (e: FleetEdge) => !hover || e.from === hover || e.to === hover

  return (
    <div
      className={clsx(
        'relative w-full overflow-hidden rounded-2xl border border-ink-900/[0.06] bg-paper-50/60',
        aspect,
        className,
      )}
    >
      {/* canvas backdrop — faint grid + a soft glow under the hubs */}
      <div className="pointer-events-none absolute inset-0 bg-dots opacity-50" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-3/4 w-3/4 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-500/[0.045] blur-3xl" />

      {/* edges — drawn first, beneath the nodes */}
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
        {edges.map((e, i) => {
          const an = byId[e.from]
          const bn = byId[e.to]
          if (!an || !bn) return null
          const a = pos(e.from)
          const b = pos(e.to)
          const hot = !!e.hot
          // colour by the more-severe endpoint
          const accent = hot ? '#e23b3b' : '#9aa3ae'
          const on = edgeLit(e)
          return (
            <g key={i} opacity={on ? 1 : 0.07} style={{ transition: 'opacity 160ms' }}>
              {/* soft halo so the connection reads on the light canvas */}
              <line
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={accent}
                strokeOpacity={hot ? 0.12 : 0.06}
                strokeWidth={hot ? 3.4 : 2.2}
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
              />
              {/* base line */}
              <line
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={accent}
                strokeOpacity={hot ? 0.34 : 0.16}
                strokeWidth={hot ? 1.1 : 0.7}
                strokeLinecap="round"
                strokeDasharray={hot ? undefined : '1.4 1.6'}
                vectorEffect="non-scaling-stroke"
              />
              {/* flowing pulse along hot edges — "the blast spreading to the hub" */}
              {hot && (
                <line
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke="#e23b3b"
                  strokeOpacity={0.95}
                  strokeWidth={1.5}
                  strokeLinecap="round"
                  strokeDasharray="0.1 5"
                  vectorEffect="non-scaling-stroke"
                >
                  <animate attributeName="stroke-dashoffset" from="0" to="-30" dur="1.2s" repeatCount="indefinite" />
                </line>
              )}
            </g>
          )
        })}
      </svg>

      {/* nodes */}
      {nodes.map((n, i) => {
        const p = pos(n.id)
        const color = nodeColor(n)
        const Icon = NODE_ICON[n.type] ?? Boxes
        const hub = !!n.hub
        const critical = n.status === 'corroded' || n.status === 'failing'
        const atRisk = n.status === 'at_risk'
        const labelled = !dense || hub || critical || atRisk || hover === n.id
        const size = hub
          ? dense
            ? 'h-11 w-11'
            : 'h-14 w-14'
          : n.type === 'asset'
            ? dense
              ? 'h-7 w-7'
              : 'h-9 w-9'
            : dense
              ? 'h-8 w-8'
              : 'h-10 w-10'
        const on = isLit(n.id)
        return (
          // Static outer div does the centering (Tailwind -translate). The inner
          // motion.div only animates opacity/scale, so framer's transform never
          // clobbers the centering — the node sits dead-centre on its anchor and
          // edges meet the icon, not its corner.
          <div
            key={n.id}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${p.x}%`, top: `${p.y}%`, zIndex: hub ? 25 : critical ? 20 : hover === n.id ? 22 : 10 }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: on ? 1 : 0.12, scale: hover === n.id ? 1.14 : 1 }}
              transition={{ delay: i * 0.04, type: 'spring', stiffness: 220, damping: 18 }}
              onMouseEnter={() => setHover(n.id)}
              onMouseLeave={() => setHover(null)}
              title={`${n.label} · ${TYPE_LABEL[n.type]}`}
              className="relative flex cursor-pointer items-center justify-center"
            >
              <span className="relative flex items-center justify-center">
              {/* pulsing ring on the failing origin + the culprit hubs */}
              {(critical || hub) && (
                <>
                  <span
                    className="absolute h-full w-full animate-ping rounded-full opacity-50"
                    style={{ background: `${color}40` }}
                  />
                  <span className="absolute -inset-2 rounded-full" style={{ boxShadow: `0 0 0 1px ${color}33` }} />
                  {hub && (
                    <span className="absolute -inset-[7px] rounded-full" style={{ boxShadow: `0 0 0 1px ${color}22` }} />
                  )}
                </>
              )}
              <div
                className={clsx(
                  'relative flex items-center justify-center rounded-2xl border bg-white shadow-card-soft',
                  size,
                )}
                style={{
                  background: `linear-gradient(180deg, #ffffff, ${color}10)`,
                  borderColor: `${color}80`,
                  color,
                  boxShadow: hub
                    ? `0 0 26px -3px ${color}, 0 1px 2px rgba(20,23,28,0.06)`
                    : critical
                      ? `0 0 20px -5px ${color}, 0 1px 2px rgba(20,23,28,0.06)`
                      : undefined,
                }}
              >
                <Icon
                  size={hub ? (dense ? 18 : 24) : n.type === 'asset' ? (dense ? 13 : 16) : dense ? 14 : 18}
                  strokeWidth={2.2}
                />
              </div>
              {/* ROOT badge on the culprit hubs */}
              {hub && (
                <span
                  className="absolute -right-1 -top-2 rounded-full px-1.5 py-0.5 text-[7.5px] font-bold uppercase tracking-wide text-white"
                  style={{ background: color, boxShadow: `0 0 10px ${color}aa` }}
                >
                  root
                </span>
              )}
            </span>
              {labelled && (
                <div
                  className="absolute left-1/2 top-full mt-1.5 flex -translate-x-1/2 flex-col items-center whitespace-nowrap rounded-md border border-ink-900/[0.08] bg-white/95 px-1.5 py-0.5 shadow-sm backdrop-blur-sm"
                  style={{ color }}
                >
                  <span className="font-mono text-[10px] font-semibold leading-none">{n.label}</span>
                  <span className="text-[7.5px] uppercase leading-none tracking-wide text-ink-400">
                    {TYPE_LABEL[n.type]}
                  </span>
                </div>
              )}
            </motion.div>
          </div>
        )
      })}
    </div>
  )
}
