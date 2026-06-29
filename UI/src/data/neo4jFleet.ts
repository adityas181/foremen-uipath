// AUTO-GENERATED from the live Neo4j Aura instance (e1dfbbbd) via
//   MATCH (n)-[r]->(m) RETURN n, r, m
// 40 nodes, 63 edges. Types: {'batch': 5, 'vendor': 3, 'site': 10, 'region': 3, 'asset': 10, 'equipment_class': 5, 'crew': 2, 'part_lot': 2}.
// Hard-coded snapshot used by the Knowledge Graph tab when the live fleet
// payload hasn't streamed in. Regenerate with scripts/transform_neo4j.py.
import type { FleetView } from '../types'

export const NEO4J_FLEET: FleetView = {
  "systemic": true,
  "affected": [
    "AST-INV-DEL-0623",
    "AST-PDU-DEL-0512",
    "AST-PDU-DEL-0556",
    "AST-SCB-DEL-0788",
    "AST-SCB-DEL-0791",
    "AST-SCB-DEL-0802"
  ],
  "unitNoun": "asset",
  "nodes": [
    {
      "id": "VE-BATCH-07",
      "label": "VE-BATCH-07",
      "type": "batch",
      "x": 88.0,
      "y": 50.9,
      "status": "at_risk",
      "hub": true
    },
    {
      "id": "VoltEdge",
      "label": "VoltEdge",
      "type": "vendor",
      "x": 89.7,
      "y": 49.2
    },
    {
      "id": "NG-BATCH-22",
      "label": "NG-BATCH-22",
      "type": "batch",
      "x": 48.5,
      "y": 12.7,
      "status": "failing"
    },
    {
      "id": "NorthGrid",
      "label": "NorthGrid",
      "type": "vendor",
      "x": 48.8,
      "y": 9.8
    },
    {
      "id": "HV-BATCH-19",
      "label": "HV-BATCH-19",
      "type": "batch",
      "x": 35.0,
      "y": 63.5,
      "status": "healthy"
    },
    {
      "id": "HelioVolt",
      "label": "HelioVolt",
      "type": "vendor",
      "x": 29.2,
      "y": 63.1
    },
    {
      "id": "HV-BATCH-21",
      "label": "HV-BATCH-21",
      "type": "batch",
      "x": 22.8,
      "y": 58.3,
      "status": "healthy"
    },
    {
      "id": "DEL-0512",
      "label": "DEL-0512",
      "type": "site",
      "x": 73.6,
      "y": 44.6
    },
    {
      "id": "DEL",
      "label": "DEL",
      "type": "region",
      "x": 62.1,
      "y": 48.5
    },
    {
      "id": "DEL-0473",
      "label": "DEL-0473",
      "type": "site",
      "x": 58.6,
      "y": 32.5
    },
    {
      "id": "MUM-0210",
      "label": "MUM-0210",
      "type": "site",
      "x": 33.6,
      "y": 15.1
    },
    {
      "id": "MUM",
      "label": "MUM",
      "type": "region",
      "x": 27.1,
      "y": 24.6
    },
    {
      "id": "DEL-0788",
      "label": "DEL-0788",
      "type": "site",
      "x": 50.8,
      "y": 52.1
    },
    {
      "id": "DEL-0791",
      "label": "DEL-0791",
      "type": "site",
      "x": 50.6,
      "y": 55.3
    },
    {
      "id": "DEL-0802",
      "label": "DEL-0802",
      "type": "site",
      "x": 53.1,
      "y": 57.0
    },
    {
      "id": "DEL-0623",
      "label": "DEL-0623",
      "type": "site",
      "x": 74.2,
      "y": 53.8
    },
    {
      "id": "MUM-0345",
      "label": "MUM-0345",
      "type": "site",
      "x": 24.0,
      "y": 36.9
    },
    {
      "id": "DEL-0556",
      "label": "DEL-0556",
      "type": "site",
      "x": 73.5,
      "y": 48.4
    },
    {
      "id": "BLR-0119",
      "label": "BLR-0119",
      "type": "site",
      "x": 12.3,
      "y": 84.3
    },
    {
      "id": "BLR",
      "label": "BLR",
      "type": "region",
      "x": 7.0,
      "y": 91.0
    },
    {
      "id": "AST-PDU-DEL-0512",
      "label": "PDU-DEL-0512",
      "type": "asset",
      "x": 84.6,
      "y": 44.6
    },
    {
      "id": "power_distribution_unit",
      "label": "power_distribution_unit",
      "type": "equipment_class",
      "x": 89.8,
      "y": 42.3
    },
    {
      "id": "AST-RF-DEL-0473",
      "label": "RF-DEL-0473",
      "type": "asset",
      "x": 53.6,
      "y": 17.9
    },
    {
      "id": "rf_jumper_cable",
      "label": "rf_jumper_cable",
      "type": "equipment_class",
      "x": 51.4,
      "y": 9.0
    },
    {
      "id": "AST-SCB-DEL-0788",
      "label": "SCB-DEL-0788",
      "type": "asset",
      "x": 39.4,
      "y": 58.8
    },
    {
      "id": "solar_connector",
      "label": "solar_connector",
      "type": "equipment_class",
      "x": 33.3,
      "y": 56.5
    },
    {
      "id": "CREW-PV-W",
      "label": "CREW-PV-W",
      "type": "crew",
      "x": 43.1,
      "y": 64.8
    },
    {
      "id": "MC4-LOT-X",
      "label": "MC4-LOT-X",
      "type": "part_lot",
      "x": 39.6,
      "y": 66.5,
      "status": "failing",
      "hub": true
    },
    {
      "id": "AST-SCB-DEL-0791",
      "label": "SCB-DEL-0791",
      "type": "asset",
      "x": 38.7,
      "y": 61.1
    },
    {
      "id": "AST-SCB-DEL-0802",
      "label": "SCB-DEL-0802",
      "type": "asset",
      "x": 40.6,
      "y": 61.4
    },
    {
      "id": "AST-INV-DEL-0623",
      "label": "INV-DEL-0623",
      "type": "asset",
      "x": 85.8,
      "y": 56.0
    },
    {
      "id": "string_inverter",
      "label": "string_inverter",
      "type": "equipment_class",
      "x": 93.0,
      "y": 61.3
    },
    {
      "id": "AST-SCB-MUM-0345",
      "label": "SCB-MUM-0345",
      "type": "asset",
      "x": 23.7,
      "y": 51.1
    },
    {
      "id": "CREW-PV-S",
      "label": "CREW-PV-S",
      "type": "crew",
      "x": 15.1,
      "y": 51.0
    },
    {
      "id": "MC4-LOT-Z",
      "label": "MC4-LOT-Z",
      "type": "part_lot",
      "x": 16.7,
      "y": 46.2,
      "status": "healthy"
    },
    {
      "id": "AST-PDU-DEL-0556",
      "label": "PDU-DEL-0556",
      "type": "asset",
      "x": 84.1,
      "y": 47.6
    },
    {
      "id": "AST-CMB-BLR-0119",
      "label": "CMB-BLR-0119",
      "type": "asset",
      "x": 19.1,
      "y": 74.5
    },
    {
      "id": "combiner_box",
      "label": "combiner_box",
      "type": "equipment_class",
      "x": 12.3,
      "y": 78.3
    },
    {
      "id": "HV-BATCH-23",
      "label": "HV-BATCH-23",
      "type": "batch",
      "x": 23.1,
      "y": 70.3
    },
    {
      "id": "AST-RF-MUM-0210",
      "label": "RF-MUM-0210",
      "type": "asset",
      "x": 43.1,
      "y": 10.0
    }
  ],
  "edges": [
    {
      "from": "VE-BATCH-07",
      "to": "VoltEdge",
      "rel": "SUPPLIED_BY",
      "hot": true
    },
    {
      "from": "NG-BATCH-22",
      "to": "NorthGrid",
      "rel": "SUPPLIED_BY",
      "hot": true
    },
    {
      "from": "HV-BATCH-19",
      "to": "HelioVolt",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "HV-BATCH-21",
      "to": "HelioVolt",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "DEL-0512",
      "to": "DEL",
      "rel": "IN_REGION"
    },
    {
      "from": "DEL-0473",
      "to": "DEL",
      "rel": "IN_REGION"
    },
    {
      "from": "MUM-0210",
      "to": "MUM",
      "rel": "IN_REGION"
    },
    {
      "from": "DEL-0788",
      "to": "DEL",
      "rel": "IN_REGION"
    },
    {
      "from": "DEL-0791",
      "to": "DEL",
      "rel": "IN_REGION"
    },
    {
      "from": "DEL-0802",
      "to": "DEL",
      "rel": "IN_REGION"
    },
    {
      "from": "DEL-0623",
      "to": "DEL",
      "rel": "IN_REGION"
    },
    {
      "from": "MUM-0345",
      "to": "MUM",
      "rel": "IN_REGION"
    },
    {
      "from": "DEL-0556",
      "to": "DEL",
      "rel": "IN_REGION"
    },
    {
      "from": "BLR-0119",
      "to": "BLR",
      "rel": "IN_REGION"
    },
    {
      "from": "AST-PDU-DEL-0512",
      "to": "power_distribution_unit",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-PDU-DEL-0512",
      "to": "VE-BATCH-07",
      "rel": "FROM_BATCH",
      "hot": true
    },
    {
      "from": "AST-PDU-DEL-0512",
      "to": "DEL-0512",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-PDU-DEL-0512",
      "to": "VoltEdge",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-RF-DEL-0473",
      "to": "rf_jumper_cable",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-RF-DEL-0473",
      "to": "NG-BATCH-22",
      "rel": "FROM_BATCH",
      "hot": true
    },
    {
      "from": "AST-RF-DEL-0473",
      "to": "DEL-0473",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-RF-DEL-0473",
      "to": "NorthGrid",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-SCB-DEL-0788",
      "to": "solar_connector",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-SCB-DEL-0788",
      "to": "HV-BATCH-19",
      "rel": "FROM_BATCH"
    },
    {
      "from": "AST-SCB-DEL-0788",
      "to": "DEL-0788",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-SCB-DEL-0788",
      "to": "HelioVolt",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-SCB-DEL-0788",
      "to": "CREW-PV-W",
      "rel": "INSTALLED_BY"
    },
    {
      "from": "AST-SCB-DEL-0788",
      "to": "MC4-LOT-X",
      "rel": "USES_PART_LOT",
      "hot": true
    },
    {
      "from": "AST-SCB-DEL-0791",
      "to": "solar_connector",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-SCB-DEL-0791",
      "to": "HV-BATCH-19",
      "rel": "FROM_BATCH"
    },
    {
      "from": "AST-SCB-DEL-0791",
      "to": "DEL-0791",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-SCB-DEL-0791",
      "to": "HelioVolt",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-SCB-DEL-0791",
      "to": "CREW-PV-W",
      "rel": "INSTALLED_BY"
    },
    {
      "from": "AST-SCB-DEL-0791",
      "to": "MC4-LOT-X",
      "rel": "USES_PART_LOT",
      "hot": true
    },
    {
      "from": "AST-SCB-DEL-0802",
      "to": "solar_connector",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-SCB-DEL-0802",
      "to": "HV-BATCH-19",
      "rel": "FROM_BATCH"
    },
    {
      "from": "AST-SCB-DEL-0802",
      "to": "DEL-0802",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-SCB-DEL-0802",
      "to": "HelioVolt",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-SCB-DEL-0802",
      "to": "CREW-PV-W",
      "rel": "INSTALLED_BY"
    },
    {
      "from": "AST-SCB-DEL-0802",
      "to": "MC4-LOT-X",
      "rel": "USES_PART_LOT",
      "hot": true
    },
    {
      "from": "AST-INV-DEL-0623",
      "to": "string_inverter",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-INV-DEL-0623",
      "to": "VE-BATCH-07",
      "rel": "FROM_BATCH",
      "hot": true
    },
    {
      "from": "AST-INV-DEL-0623",
      "to": "DEL-0623",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-INV-DEL-0623",
      "to": "VoltEdge",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-SCB-MUM-0345",
      "to": "solar_connector",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-SCB-MUM-0345",
      "to": "HV-BATCH-21",
      "rel": "FROM_BATCH"
    },
    {
      "from": "AST-SCB-MUM-0345",
      "to": "MUM-0345",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-SCB-MUM-0345",
      "to": "HelioVolt",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-SCB-MUM-0345",
      "to": "CREW-PV-S",
      "rel": "INSTALLED_BY"
    },
    {
      "from": "AST-SCB-MUM-0345",
      "to": "MC4-LOT-Z",
      "rel": "USES_PART_LOT"
    },
    {
      "from": "AST-PDU-DEL-0556",
      "to": "power_distribution_unit",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-PDU-DEL-0556",
      "to": "VE-BATCH-07",
      "rel": "FROM_BATCH",
      "hot": true
    },
    {
      "from": "AST-PDU-DEL-0556",
      "to": "DEL-0556",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-PDU-DEL-0556",
      "to": "VoltEdge",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-CMB-BLR-0119",
      "to": "combiner_box",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-CMB-BLR-0119",
      "to": "HV-BATCH-23",
      "rel": "FROM_BATCH"
    },
    {
      "from": "AST-CMB-BLR-0119",
      "to": "BLR-0119",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-CMB-BLR-0119",
      "to": "HelioVolt",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "AST-RF-MUM-0210",
      "to": "rf_jumper_cable",
      "rel": "OF_CLASS"
    },
    {
      "from": "AST-RF-MUM-0210",
      "to": "NG-BATCH-22",
      "rel": "FROM_BATCH",
      "hot": true
    },
    {
      "from": "AST-RF-MUM-0210",
      "to": "MUM-0210",
      "rel": "LOCATED_AT"
    },
    {
      "from": "AST-RF-MUM-0210",
      "to": "NorthGrid",
      "rel": "SUPPLIED_BY"
    },
    {
      "from": "HV-BATCH-23",
      "to": "HelioVolt",
      "rel": "SUPPLIED_BY"
    }
  ],
  "rootCause": [
    {
      "factor": "MC4-LOT-X",
      "factorType": "Part lot",
      "count": 3,
      "note": "mixed-brand / cross-mated connector lot shared across assets"
    },
    {
      "factor": "VE-BATCH-07",
      "factorType": "Batch",
      "count": 3,
      "note": "suspect batch supplied to multiple assets"
    }
  ],
  "criticality": [
    {
      "factor": "HelioVolt",
      "factorType": "Vendor",
      "count": 8,
      "note": "8 connections in the knowledge graph"
    },
    {
      "factor": "DEL",
      "factorType": "Region",
      "count": 7,
      "note": "7 connections in the knowledge graph"
    },
    {
      "factor": "AST-SCB-DEL-0788",
      "factorType": "Asset",
      "count": 6,
      "note": "6 connections in the knowledge graph"
    }
  ],
  "sqlVsGraph": {
    "sqlFound": 2,
    "sqlNote": "A flat status='failing' query sees only the assets already failing.",
    "graphFound": 6,
    "graphNote": "The graph reveals every asset sharing the cross-mated lot or suspect batch."
  },
  "queryTitle": "Estate graph \u00b7 Cypher",
  "query": "MATCH (n)-[r]->(m)\nRETURN n, r, m",
  "exposurePerHr": 9200,
  "exposureLabel": "estate revenue at risk"
}
