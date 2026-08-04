#!/usr/bin/env python3
"""
Decide whether minimarket pairs within 50 m are missed deduplication or genuine
opposite-side-of-the-street openings.

In Indonesia Alfamart and Indomaret deliberately open very close to one another, so having
another minimarket within 50 m is not by itself anomalous. **Only same-chain pairs are
suspect.**
"""
import duckdb

M = "read_parquet('data/semarang/semarang_food_master.parquet')"
con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute(f"""create table m as select *, ST_Point(lng, lat) geom,
  case
    when name ilike '%alfamidi%'  then 'alfamidi'
    when name ilike '%alfamart%'  then 'alfamart'
    when name ilike '%indomaret%' then 'indomaret'
    else '(other)' end as chain
  from {M} where cat='minimarket'""")
con.execute("create index m_ix on m using rtree(geom)")

print("=== minimarket pairs within 50 m ===")
rows = con.execute("""
  select a.chain, b.chain, count(*) c,
         round(avg(111320*sqrt(power(b.lat-a.lat,2)
           + power((b.lng-a.lng)*cos(radians(a.lat)),2)))) avg_m
  from m a join m b on a.store_id < b.store_id
    and ST_DWithin(a.geom, b.geom, 0.00045)
  group by 1,2 order by c desc""").fetchall()
same = cross = 0
for a, b, c, d in rows:
    is_same = a == b and a != '(other)'
    flag = "** same chain — suspect deduplication miss" if is_same else ""
    if is_same:
        same += c
    else:
        cross += c
    print(f"  {a:12s} x {b:12s} {c:>4,} pairs  mean {d:>3.0f} m  {flag}")

print(f"\n  same-chain pairs  {same:>4,}  <- deduplication misses")
print(f"  cross/unknown     {cross:>4,}  <- genuine nearby openings")

print("\n=== same-chain pairs within 50 m, by source ===")
for r in con.execute("""
  select a.chain, a.src, b.src, count(*) c
  from m a join m b on a.store_id < b.store_id
    and ST_DWithin(a.geom, b.geom, 0.00045) and a.chain = b.chain
  where a.chain != '(other)'
  group by 1,2,3 order by c desc""").fetchall():
    print(f"  {r[0]:12s} {r[1]:9s} x {r[2]:9s} {r[3]:>4,} pairs")

print("\n=== final master summary ===")
for r in con.execute(f"""
  select cat, count(*) n, count(*) filter (where src='osm') osm,
         count(*) filter (where src='overture') ov
  from {M} group by 1 order by n desc""").fetchall():
    print(f"  {r[0]:16s} {r[1]:>5,}  (osm {r[2]:>4,} / overture {r[3]:>4,})")
n, = con.execute(f"select count(*) from {M}").fetchone()
print(f"  {'total':16s} {n:>5,}")
