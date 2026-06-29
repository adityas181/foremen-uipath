"""Diagnostics for the FOREMAN graph - reads the REAL current Neo4j state, bypassing Bloom's cache.

    uv run python kg_check.py

Use this to settle "is it a sync problem or just Bloom showing a stale scene?".
"""
import os

for _l in open(".env", encoding="utf-8"):
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        _k, _, _v = _l.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

import kg


def run(ses, q, **kw):
    return ses.run(q, **kw).data()


with kg.driver() as d, d.session(database=kg.database()) as ses:
    print("== node counts by label (the DB truth) ==")
    for r in run(ses, "MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS n ORDER BY label"):
        print(f"  {r['label']:16} {r['n']}")

    print("\n== relationship counts by type ==")
    for r in run(ses, "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n ORDER BY t"):
        print(f"  {r['t']:16} {r['n']}")

    print("\n== every asset and its vendor / region (the connectors) ==")
    for r in run(ses, """
        MATCH (a:Asset)
        OPTIONAL MATCH (a)-[:SUPPLIED_BY]->(v:Vendor)
        OPTIONAL MATCH (a)-[:LOCATED_AT]->(:Site)-[:IN_REGION]->(rg:Region)
        RETURN a.asset_id AS asset, coalesce(v.name,'(none)') AS vendor,
               coalesce(rg.name,'(none)') AS region
        ORDER BY asset"""):
        print(f"  {r['asset']:22} vendor={r['vendor']:12} region={r['region']}")

    print("\n== is the fleet ONE connected graph? path between a SOLAR and an RF asset ==")
    rows = run(ses, """
        MATCH p = shortestPath(
          (a:Asset {asset_id:'AST-SCB-DEL-0788'})-[*..10]-(b:Asset {asset_id:'AST-RF-MUM-0210'}))
        RETURN length(p) AS hops,
               [n IN nodes(p) | coalesce(n.asset_id, n.name, n.batch_id, n.site_id,
                                         n.lot_id, n.crew_id)] AS via""")
    if rows:
        print(f"  CONNECTED in {rows[0]['hops']} hops:")
        print("    " + "  ->  ".join(str(x) for x in rows[0]["via"]))
        print("  => one fleet. If Bloom still shows 2 blobs, it's a stale scene (refresh it).")
    else:
        print("  NOT connected - they are in separate components. Tell me and we'll fix the sync.")