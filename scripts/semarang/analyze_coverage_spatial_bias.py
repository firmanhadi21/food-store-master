#!/usr/bin/env python3
"""
Test whether the master's ~50% chain shortfall is **spatially random or structured**.

Why this is decisive
--------------------
estimate_chain_truth.py put the master's chain coverage at 0.42 (Alfamart) and 0.41
(Indomaret). The school-buffer analysis reports absolute counts that are roughly half of
reality — but its *proportions* survive **only if the misses are spatially random**.

  - misses random          -> proportions usable; only the counts need correcting
  - misses concentrated    -> **the proportions are biased too**, and section 3 of the
                              analysis cannot be reported as-is

There is a reason to expect structure: Overture here is 98.1% Meta-derived, so coverage
should inherit Facebook-page density, which is lower where commercial formality is lower.
That is a testable hypothesis, so test it.

Method
------
1. Cut the city into a 2 km grid, count Google and master records per cell, take the ratio.
2. Check whether the ratio correlates with distance from the centre or with store density.
3. Aggregate by kecamatan (OSM admin_level=6) for an interpretable view.

Output: docs/semarang/verify_coverage-spatial-bias.csv
"""
import json
import os
import time
import urllib.parse
import urllib.request

import duckdb

D = "data/semarang"
G = f"read_parquet('{D}/google_chains_semarang.parquet')"
M = f"read_parquet('{D}/semarang_food_master.parquet')"
POLY = f"{D}/semarang_boundary_poly.geojson"
KEC = f"{D}/semarang_kecamatan.geojson"
OUT = "docs/semarang/verify_coverage-spatial-bias.csv"

CELL_KM = 2.0
# Simpang Lima, the city centre — the reference point for "peripherality"
CX, CY = 110.4229, -6.9932

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def fetch_kecamatan():
    """Fetch kecamatan polygons (admin_level=6) for Kota Semarang from OSM."""
    if os.path.exists(KEC):
        return
    q = """
    [out:json][timeout:180];
    area["name"="Kota Semarang"]["admin_level"="5"]->.a;
    relation(area.a)["boundary"="administrative"]["admin_level"="6"];
    out geom;
    """
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": q}).encode(),
        headers={"User-Agent": "japan-food-store-master/semarang"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    feats = []
    for el in data["elements"]:
        ways = [[(p["lon"], p["lat"]) for p in m["geometry"]]
                for m in el.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
        if not ways:
            continue
        # Same ring-stitching as compare_sources_semarang.py
        rings, pending = [], list(ways)
        cur = pending.pop(0)
        while True:
            if cur[0] == cur[-1] and len(cur) > 3:
                rings.append(cur)
                if not pending:
                    break
                cur = pending.pop(0)
                continue
            for i, w in enumerate(pending):
                if w[0] == cur[-1]:
                    cur += w[1:]; pending.pop(i); break
                if w[-1] == cur[-1]:
                    cur += w[::-1][1:]; pending.pop(i); break
                if w[-1] == cur[0]:
                    cur = w[:-1] + cur; pending.pop(i); break
                if w[0] == cur[0]:
                    cur = w[::-1][:-1] + cur; pending.pop(i); break
            else:
                rings.append(cur)
                if not pending:
                    break
                cur = pending.pop(0)
        rings = [r for r in rings if len(r) > 3]
        if not rings:
            continue
        main = max(rings, key=len)
        if main[0] != main[-1]:
            main.append(main[0])
        feats.append({"type": "Feature",
                      "properties": {"name": el.get("tags", {}).get("name")},
                      "geometry": {"type": "Polygon", "coordinates": [main]}})
    with open(KEC, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)
    print(f"{len(feats)} kecamatan -> {KEC}")
    time.sleep(1)


# ---- 1. Coverage per grid cell ----
con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
b = con.execute("""select ST_XMin(geom), ST_XMax(geom), ST_YMin(geom), ST_YMax(geom)
                   from kota""").fetchone()
dlat = CELL_KM / 111.320
dlon = CELL_KM / (111.320 * 0.99255)

con.execute(f"""create table g as select chain, lat, lon,
    floor((lon - {b[0]})/{dlon})::int cx, floor((lat - {b[2]})/{dlat})::int cy from {G}""")
con.execute(f"""create table m as select name, lat, lng as lon,
    floor((lng - {b[0]})/{dlon})::int cx, floor((lat - {b[2]})/{dlat})::int cy
    from {M} where cat='minimarket'
      and (name ilike '%alfamart%' or name ilike '%indomaret%')""")

con.execute("""create table cell as
  select coalesce(g.cx, m.cx) cx, coalesce(g.cy, m.cy) cy,
         coalesce(g.n, 0) g_n, coalesce(m.n, 0) m_n
  from (select cx, cy, count(*) n from g group by 1,2) g
  full outer join (select cx, cy, count(*) n from m group by 1,2) m
    using (cx, cy)""")
con.execute(f"""create or replace table cell as
  select *, {b[0]} + (cx + 0.5)*{dlon} as lon, {b[2]} + (cy + 0.5)*{dlat} as lat,
         111.320*sqrt(power({b[2]} + (cy+0.5)*{dlat} - {CY}, 2)
           + power(({b[0]} + (cx+0.5)*{dlon} - {CX})*0.99255, 2)) as dist_km,
         case when g_n > 0 then m_n::double / g_n else null end as ratio
  from cell""")

n_cell, = con.execute("select count(*) from cell where g_n > 0").fetchone()
h(f"1. Coverage per {CELL_KM} km cell ({n_cell} cells with at least one Google record)")
r = con.execute("""select round(min(ratio),2), round(quantile_cont(ratio,0.25),2),
    round(median(ratio),2), round(quantile_cont(ratio,0.75),2), round(max(ratio),2)
    from cell where g_n > 0""").fetchone()
print(f"  ratio (master/Google)  min={r[0]}  p25={r[1]}  median={r[2]}  p75={r[3]}  max={r[4]}")

h("2. Coverage by distance from the centre — **this is the bias test**")
print(f"  {'band':12s} {'cells':>5s} {'Google':>7s} {'master':>8s} {'coverage':>9s}")
for lo, hi in [(0, 2), (2, 4), (4, 6), (6, 8), (8, 12), (12, 99)]:
    row = con.execute(f"""select count(*), sum(g_n), sum(m_n) from cell
        where g_n > 0 and dist_km >= {lo} and dist_km < {hi}""").fetchone()
    if row[0]:
        rate = row[2] / row[1] if row[1] else 0
        bar = "#" * int(rate * 40)
        print(f"  {f'{lo}-{hi}km':12s} {row[0]:>5,} {row[1]:>7,} {row[2]:>8,} "
              f"{rate:>8.2f} {bar}")

h("3. Correlations (negative => coverage falls toward the periphery)")
c = con.execute("""select corr(dist_km, ratio), corr(g_n, ratio), count(*)
    from cell where g_n > 0""").fetchone()
print(f"  corr(distance from centre, coverage) = {c[0]:+.3f}")
print(f"  corr(stores per cell, coverage)      = {c[1]:+.3f}   (n={c[2]})")
print("\n  Reading:")
print("   |r| < ~0.2 suggests effectively random -> proportions usable, correct counts only")
print("   strongly negative -> peripheral areas under-covered -> **proportions biased too**")
print("\n  ** But a weak correlation here does not settle it. See section 4: distance is")
print("     simply the wrong covariate, and stratifying by administrative unit reveals")
print("     variation the correlation misses entirely.")

# ---- 4. By kecamatan ----
try:
    fetch_kecamatan()
    con.execute(f"""create table kec as
      select name, geom::GEOMETRY geom from ST_Read('{KEC}')""")
    nk, = con.execute("select count(*) from kec").fetchone()
    h(f"4. Coverage by kecamatan ({nk} districts)")
    con.execute("""create table kecstat as
      select k.name,
        (select count(*) from g where ST_Contains(k.geom, ST_Point(g.lon, g.lat))) g_n,
        (select count(*) from m where ST_Contains(k.geom, ST_Point(m.lon, m.lat))) m_n
      from kec k""")
    print(f"  {'kecamatan':22s} {'Google':>7s} {'master':>8s} {'coverage':>9s}")
    for row in con.execute("""select name, g_n, m_n,
        case when g_n > 0 then m_n::double/g_n end r
        from kecstat order by r nulls last""").fetchall():
        bar = "#" * int((row[3] or 0) * 30)
        print(f"  {str(row[0])[:20]:22s} {row[1]:>7,} {row[2]:>8,} "
              f"{(row[3] or 0):>8.2f} {bar}")
    con.execute(f"copy (select name as kecamatan, g_n as google_n, m_n as master_n, "
                f"case when g_n>0 then round(m_n::double/g_n,3) end as coverage_ratio "
                f"from kecstat order by coverage_ratio) to '{OUT}' (header, delimiter ',')")
    print(f"\nwrote: {OUT}")
except Exception as e:  # noqa: BLE001
    print(f"\nkecamatan fetch failed (the cell-level conclusion still stands): {e}")
