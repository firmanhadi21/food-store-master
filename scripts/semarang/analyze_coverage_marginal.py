#!/usr/bin/env python3
"""
Estimate — before doing it — whether completing the warung / toko kelontong layer is worth it.

The reasoning (borrowed directly from the Japan version's verify_master_quality.py)
-----------------------------------------------------------------------------------
An access measure is binary: is the nearest outlet within the threshold or not. Therefore:
  - **surplus is harmless.** Adding an outlet somewhere already inside the threshold changes
    nothing.
  - **a missing outlet only matters where it was the only one in range.**

So the marginal contribution of each nested category bounds what completing warung could
possibly change.

Population is not yet joined, so this is **area-based**. Kota Semarang contains sparsely
populated hills in the south (Gunungpati, Mijen) and port/tambak land in the north, so the
area-based uncovered share overstates the population-based one. Population weighting is the
next step (Podes / WorldPop).

Output: docs/semarang/verify_coverage-marginal-contribution.csv
"""
import os

import duckdb

D = "data/semarang"
M = f"read_parquet('{D}/semarang_food_master.parquet')"
POLY = f"{D}/semarang_boundary_poly.geojson"
OUT = "docs/semarang/verify_coverage-marginal-contribution.csv"

GRID_M = 250       # assessment grid, half the 500 m threshold
THRESHOLDS = [300, 500, 1000]

# Nested sets, in the spirit of the Japan version's NESTED list. Ordered so that "can fresh
# food be bought here" comes first and packaged-only formats are added afterwards.
NESTED = [
    ("F1 pasar only", "['pasar']"),
    ("F2 +supermarket", "['pasar','supermarket']"),
    ("F3 +fresh_food", "['pasar','supermarket','fresh_food']"),
    ("F4 +minimarket", "['pasar','supermarket','fresh_food','minimarket']"),
    ("F5 +toko_kelontong (all)",
     "['pasar','supermarket','fresh_food','minimarket','toko_kelontong']"),
]

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


# ---- 1. A 250 m grid covering the city ----
# Equirectangular; at latitude -7 the longitude correction is cos(7 deg) ~ 0.993
con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
b = con.execute("""select ST_XMin(geom), ST_XMax(geom), ST_YMin(geom), ST_YMax(geom)
                   from kota""").fetchone()
dlat = GRID_M / 111320.0
dlon = GRID_M / (111320.0 * 0.99255)
nx = int((b[1] - b[0]) / dlon) + 1
ny = int((b[3] - b[2]) / dlat) + 1
print(f"grid {nx} x {ny} = {nx*ny:,} cells ({GRID_M} m)")

con.execute(f"""create table cell as
  select {b[0]} + (i + 0.5) * {dlon} as lng,
         {b[2]} + (j + 0.5) * {dlat} as lat
  from range(0, {nx}) t(i), range(0, {ny}) u(j)""")
con.execute("""create table grid as
  select row_number() over () id, lng, lat, ST_Point(lng, lat) geom
  from cell c where exists (select 1 from kota k where ST_Contains(k.geom, c_pt))
  """.replace("c_pt", "ST_Point(c.lng, c.lat)"))
ncell, = con.execute("select count(*) from grid").fetchone()
print(f"cells inside the city: {ncell:,} = {ncell * (GRID_M/1000)**2:,.1f} km2")

# ---- 2. Project stores and cells to a metre plane and bucket them ----
con.execute(f"""create table st as
  select cat, lng*111320*0.99255 x, lat*111320 y from {M}""")
con.execute("""create table gp as
  select id, lng*111320*0.99255 x, lat*111320 y from grid""")

h("1. Coverage as categories are added (area-based)")
rows = []
for thr in THRESHOLDS:
    print(f"\n  --- threshold {thr} m ---")
    print(f"  {'store set':32s} {'cells in':>9s} {'coverage':>9s} {'marginal':>10s}")
    prev = None
    for label, cats in NESTED:
        # Bucket first to narrow candidates, then apply the true (approximated) distance
        n_in, = con.execute(f"""
          select count(distinct g.id) from gp g join st s
            on floor(s.x/{thr})::bigint between floor(g.x/{thr})::bigint - 1
                                            and floor(g.x/{thr})::bigint + 1
           and floor(s.y/{thr})::bigint between floor(g.y/{thr})::bigint - 1
                                            and floor(g.y/{thr})::bigint + 1
          where s.cat in (select unnest({cats}))
            and sqrt(power(g.x-s.x,2) + power(g.y-s.y,2)) <= {thr}""").fetchone()
        rate = n_in / ncell
        delta = (n_in - prev) if prev is not None else None
        d = f"{delta:>+10,}" if delta is not None else f"{'—':>10s}"
        print(f"  {label:32s} {n_in:>9,} {rate*100:>8.1f}% {d}")
        rows.append((thr, label, n_in, ncell, round(rate, 4),
                     delta if delta is not None else 0))
        prev = n_in

h("2. Isolated-store rate — outlets that are the sole reason a place is covered")
print("  (the Japan version's 'impact of a gap = shortfall x isolated-store rate')")
print(f"  {'category':18s} {'stores':>7s} {'no other store within 500 m':>30s}")
for cat in ["pasar", "supermarket", "fresh_food", "minimarket", "toko_kelontong"]:
    r = con.execute(f"""
      with a as (select * from st where cat='{cat}'),
           b as (select * from st)
      select count(*) from a where not exists (
        select 1 from b where (b.x,b.y) != (a.x,a.y)
          and sqrt(power(a.x-b.x,2)+power(a.y-b.y,2)) <= 500)""").fetchone()
    tot, = con.execute(f"select count(*) from st where cat='{cat}'").fetchone()
    print(f"  {cat:18s} {tot:>7,} {r[0]:>25,} ({r[0]/tot*100:.1f}%)")

h("3. Where the uncovered cells are — southern hills, or holes in the built-up area?")
# Semarang runs from coastal city in the north to hills in the south, so the latitude
# profile separates the two explanations.
con.execute(f"""create table outside as
  select g.* from gp g where not exists (
    select 1 from st s
    where floor(s.x/500)::bigint between floor(g.x/500)::bigint - 1
                                     and floor(g.x/500)::bigint + 1
      and floor(s.y/500)::bigint between floor(g.y/500)::bigint - 1
                                     and floor(g.y/500)::bigint + 1
      and sqrt(power(g.x-s.x,2)+power(g.y-s.y,2)) <= 500)""")
n_out, = con.execute("select count(*) from outside").fetchone()
print(f"  cells beyond 500 m of any category: {n_out:,} / {ncell:,} = {n_out/ncell*100:.1f}%")
print("\n  by latitude band (north = coastal city -> south = hills):")
# `out` is a reserved word in DuckDB and cannot be used as an alias
for r in con.execute("""
    select round(lat, 2) band, count(*) tot,
           count(*) filter (where id in (select id from outside)) n_out
    from grid group by 1 order by band desc""").fetchall():
    bar = "#" * int(r[2] / max(r[1], 1) * 40)
    print(f"    lat {r[0]:>7.2f}  uncovered {r[2]:>4,}/{r[1]:<4,} "
          f"({r[2]/r[1]*100:>5.1f}%) {bar}")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(threshold_m int, store_set varchar, cells_in bigint, "
            "cells_total bigint, coverage double, marginal_cells bigint)")
con.executemany("insert into res values (?,?,?,?,?,?)", rows)
con.execute(f"copy res to '{OUT}' (header, delimiter ',')")
print(f"\nwrote: {OUT}")
