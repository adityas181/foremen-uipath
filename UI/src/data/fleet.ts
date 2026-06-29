import type { FleetEdge, FleetNode } from '../types'

// Neo4j blast-radius layout — coordinates are in a 0..100 space, scaled in SVG.
// The non-marine failing batch (NG-BATCH-22) sits center; the healthy marine
// batch + dry inland site sit apart to show the graph "flags the bad batch only".
export const FLEET_NODES: FleetNode[] = [
  { id: 'NG-BATCH-22', label: 'NG-BATCH-22', type: 'batch', status: 'failing', x: 50, y: 48 },
  { id: 'NorthGrid', label: 'NorthGrid', type: 'vendor', x: 50, y: 12 },
  { id: 'WEST-COAST', label: 'WEST-COAST · coastal', type: 'cluster', x: 50, y: 86 },
  { id: 'DEL-0473', label: 'DEL-0473', type: 'site', status: 'corroded', x: 20, y: 34 },
  { id: 'MUM-0210', label: 'MUM-0210', type: 'site', status: 'corroded', x: 22, y: 64 },
  { id: 'GOA-0188', label: 'GOA-0188', type: 'site', status: 'at_risk', x: 76, y: 30 },
  { id: 'KOC-0231', label: 'KOC-0231', type: 'site', status: 'at_risk', x: 78, y: 64 },
  { id: 'NG-BATCH-30', label: 'NG-BATCH-30 · marine', type: 'batch', status: 'healthy', x: 90, y: 12 },
  { id: 'BLR-0337', label: 'BLR-0337 · dry', type: 'site', status: 'healthy', x: 92, y: 90 },
]

export const FLEET_EDGES: FleetEdge[] = [
  { from: 'NorthGrid', to: 'NG-BATCH-22', rel: 'SUPPLIED' },
  { from: 'NorthGrid', to: 'NG-BATCH-30', rel: 'SUPPLIED' },
  { from: 'DEL-0473', to: 'NG-BATCH-22', rel: 'USES' },
  { from: 'MUM-0210', to: 'NG-BATCH-22', rel: 'USES' },
  { from: 'GOA-0188', to: 'NG-BATCH-22', rel: 'USES' },
  { from: 'KOC-0231', to: 'NG-BATCH-22', rel: 'USES' },
  { from: 'DEL-0473', to: 'WEST-COAST', rel: 'IN' },
  { from: 'MUM-0210', to: 'WEST-COAST', rel: 'IN' },
  { from: 'BLR-0337', to: 'NG-BATCH-30', rel: 'USES' },
]

export const AFFECTED_SITES = ['DEL-0473', 'MUM-0210', 'GOA-0188', 'KOC-0231']
