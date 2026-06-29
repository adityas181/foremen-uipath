import type { FleetView } from '../types'

// ─────────────────────────────────────────────────────────────────────────────
// MC4 solar cross-mating blast-radius (the graph that beats SQL).
//
// The burned connectors span THREE different module batches (MOD-LOT-A/B/C) but
// share ONE install crew (CREW-PV-3) and ONE connector lot (MC4-LOT-X). So a
// "same batch" query points at the wrong thing; the graph converges on crew+lot.
// Positions are laid out by hand (0–100 canvas) so the two culprit hubs sit
// centre-stage and the scattered batches fan out to the rim.
// ─────────────────────────────────────────────────────────────────────────────

export const fleetMC4: FleetView = {
  systemic: true,
  unitNoun: 'string',
  affected: [
    'AST-PV-RJ-S12',
    'AST-PV-RJ-S07',
    'AST-PV-GJ-S03',
    'AST-PV-GJ-S22',
    'AST-PV-RJ-S15',
    'AST-PV-GJ-S19',
  ],

  nodes: [
    // ── the two culprit hubs (centre) ──
    { id: 'CREW-PV-3', label: 'CREW-PV-3', type: 'crew', status: 'failing', hub: true, x: 39, y: 47 },
    { id: 'MC4-LOT-X', label: 'MC4-LOT-X', type: 'part_lot', status: 'failing', hub: true, x: 64, y: 43 },

    // ── burned strings (the live case + two priors) ──
    { id: 'AST-PV-RJ-S12', label: 'RJ-S12', type: 'asset', status: 'failing', x: 50, y: 71 },
    { id: 'AST-PV-RJ-S07', label: 'RJ-S07', type: 'asset', status: 'failing', x: 23, y: 69 },
    { id: 'AST-PV-GJ-S03', label: 'GJ-S03', type: 'asset', status: 'failing', x: 77, y: 68 },

    // ── at-risk strings (same crew and/or lot, not yet failed) ──
    { id: 'AST-PV-GJ-S22', label: 'GJ-S22', type: 'asset', status: 'at_risk', x: 85, y: 54 },
    { id: 'AST-PV-RJ-S15', label: 'RJ-S15', type: 'asset', status: 'at_risk', x: 15, y: 55 },
    { id: 'AST-PV-GJ-S19', label: 'GJ-S19', type: 'asset', status: 'at_risk', x: 38, y: 25 },

    // ── module batches: scattered on the rim (the false signal) ──
    { id: 'MOD-LOT-A', label: 'MOD-LOT-A', type: 'batch', status: 'healthy', x: 52, y: 11 },
    { id: 'MOD-LOT-B', label: 'MOD-LOT-B', type: 'batch', status: 'healthy', x: 16, y: 22 },
    { id: 'MOD-LOT-C', label: 'MOD-LOT-C', type: 'batch', status: 'healthy', x: 86, y: 24 },

    // ── the healthy control: shares MOD-LOT-A but a good crew + genuine lot ──
    { id: 'AST-PV-MH-S05', label: 'MH-S05', type: 'asset', status: 'healthy', x: 88, y: 86 },
    { id: 'CREW-PV-1', label: 'CREW-PV-1', type: 'crew', status: 'healthy', x: 72, y: 90 },
  ],

  edges: [
    // INSTALLED_BY → the crew hub (hot: the real propagation path)
    { from: 'AST-PV-RJ-S12', to: 'CREW-PV-3', rel: 'INSTALLED_BY', hot: true },
    { from: 'AST-PV-RJ-S07', to: 'CREW-PV-3', rel: 'INSTALLED_BY', hot: true },
    { from: 'AST-PV-GJ-S03', to: 'CREW-PV-3', rel: 'INSTALLED_BY', hot: true },
    { from: 'AST-PV-GJ-S22', to: 'CREW-PV-3', rel: 'INSTALLED_BY', hot: true },
    { from: 'AST-PV-RJ-S15', to: 'CREW-PV-3', rel: 'INSTALLED_BY', hot: true },
    { from: 'AST-PV-GJ-S19', to: 'CREW-PV-3', rel: 'INSTALLED_BY', hot: true },
    // USES_PART_LOT → the connector-lot hub (hot)
    { from: 'AST-PV-RJ-S12', to: 'MC4-LOT-X', rel: 'USES_PART_LOT', hot: true },
    { from: 'AST-PV-RJ-S07', to: 'MC4-LOT-X', rel: 'USES_PART_LOT', hot: true },
    { from: 'AST-PV-GJ-S03', to: 'MC4-LOT-X', rel: 'USES_PART_LOT', hot: true },
    { from: 'AST-PV-GJ-S22', to: 'MC4-LOT-X', rel: 'USES_PART_LOT', hot: true },
    // FROM_BATCH → scattered module batches (cool: the signal SQL keys on, but it
    // splits the failures across three lots, so it never clusters them)
    { from: 'AST-PV-RJ-S12', to: 'MOD-LOT-A', rel: 'FROM_BATCH' },
    { from: 'AST-PV-GJ-S19', to: 'MOD-LOT-A', rel: 'FROM_BATCH' },
    { from: 'AST-PV-RJ-S07', to: 'MOD-LOT-B', rel: 'FROM_BATCH' },
    { from: 'AST-PV-RJ-S15', to: 'MOD-LOT-B', rel: 'FROM_BATCH' },
    { from: 'AST-PV-GJ-S03', to: 'MOD-LOT-C', rel: 'FROM_BATCH' },
    { from: 'AST-PV-GJ-S22', to: 'MOD-LOT-C', rel: 'FROM_BATCH' },
    // the healthy control: shares MOD-LOT-A (so SQL grabs it) but a good crew
    { from: 'AST-PV-MH-S05', to: 'MOD-LOT-A', rel: 'FROM_BATCH' },
    { from: 'AST-PV-MH-S05', to: 'CREW-PV-1', rel: 'INSTALLED_BY' },
  ],

  // common-cause: the shared upstream node that explains the burns (count =
  // failures explained). The module batch never appears — it can't.
  rootCause: [
    { factor: 'CREW-PV-3', factorType: 'Crew', via: 'INSTALLED_BY', count: 3, note: 'cross-mated connectors across 3 module batches' },
    { factor: 'MC4-LOT-X', factorType: 'Part lot', via: 'USES_PART_LOT', count: 3, note: 'mixed-brand connector lot (Stäubli ↔ generic)' },
  ],

  // criticality: degree centrality — biggest single-points-of-failure to harden
  criticality: [
    { factor: 'CREW-PV-3', factorType: 'Crew', count: 6, note: 'every string this crew installed is exposed' },
    { factor: 'MC4-LOT-X', factorType: 'Part lot', count: 4, note: 'connectors drawn from the mixed lot' },
    { factor: 'MOD-LOT-A', factorType: 'Batch', count: 3, note: 'incl. a HEALTHY string — proof it is not the cause' },
  ],

  sqlVsGraph: {
    sqlFound: 0,
    sqlNote: 'WHERE batch = MOD-LOT-A → 2 same-batch strings, both healthy, 0 real burns',
    graphFound: 6,
    graphNote: 'traverse crew + connector lot → 6 at-risk strings across MOD-LOT-A/B/C',
  },

  queryTitle: 'Multi-factor blast-radius · Cypher',
  query: `MATCH (a:Asset {asset_id:'AST-PV-RJ-S12'})-[r]->(f)<-[r2]-(o:Asset)
WHERE type(r) IN ['INSTALLED_BY','USES_PART_LOT'] AND type(r)=type(r2)
RETURN o.asset_id, type(r) AS via, f
// => 6 strings via CREW-PV-3 + MC4-LOT-X — across MOD-LOT-A/B/C
//    a WHERE batch=X query returns 2 healthy strings and misses every burn`,

  exposurePerHr: 9200,
  exposureLabel: 'Generation revenue at risk',
}
