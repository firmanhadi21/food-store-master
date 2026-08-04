#!/usr/bin/env python3
"""
Combine the OSM and Dukcapil school layers.

Why combine — the same "genuinely complementary" situation as the store master
-----------------------------------------------------------------------------
The two sources are **independent** (OSM is local mappers; Dukcapil republishes
Kemendikbud/Dapodik) and the holes in each have different shapes. Measured, within the city:

  OSM      2,017  — SD 507 / SMP 145 / SMA 152 / TK 1,110
  Dukcapil 1,781  — TK 1,378 / PT 270 / informal 40 / SLB 16 / SMA 1 / **no SD or SMP**

** Dukcapil's critical gap, confirmed by direct query:
  - within the Semarang bbox, tags='Elementary School' returns **0** and
    'Junior High School' returns **0**, while nationally these hold 54,159 and 93,714 —
    so its coverage is **regionally uneven**
  - 'Senior High School' **does not exist as a tag anywhere nationally** (count 0)
  => **For SD/SMP/SMA, Dukcapil is unusable and OSM is the only source.**

** Where Dukcapil does help:
  - 879 of its records have no OSM counterpart within the match radius, overwhelmingly
    TK/PAUD — which matters because PP 28/2024's definition of satuan pendidikan
    includes PAUD.

=> Take the union. Same call as Overture union OSM in the store master: each source holds
   many entities the other lacks.

Deduplication caveat
--------------------
For the same reason Alfamart and Indomaret must not be merged in the store master,
**facilities at different levels must not be merged on proximity alone** — a TK and an SD
sharing a site is entirely normal. Only same-level pairs are treated as duplicates.

Output: data/semarang/schools_semarang_combined.parquet
"""
import os

import duckdb

D = "data/semarang"
OSM = f"{D}/osm_schools_semarang.parquet"
DUK = f"{D}/dukcapil_schools_semarang.parquet"
OUT = f"{D}/schools_semarang_combined.parquet"

# ** 150 m for schools, against 100 m for stores.
#
#   The reason is the nature of the facility, not fitting a target: a shop is a few metres
#   of frontage, but a school is a compound, so sources pick different reference points
#   (gate / building / site centroid) and the same institution lands 100-200 m apart.
#
#   Measured (verify_school_completeness.py): OSM x Dukcapil TK pairs matching at 100 m = 0,
#   at 150 m = 128, at 200 m = 239. At 100 m the same kindergarten was double-counted and TK
#   reached 1,590, or 110.5% of Dapodik's published 1,439. At 150 m it is 1,462 (101.6%).
#   The published figure **corroborates** the change; the justification is the spread above.
#
#   Note this cannot affect SD/SMP/SMA, since Dukcapil holds none of those in Semarang.
DEDUP_M = 150

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 68}\n{t}\n{'=' * 68}")


con.execute(f"""create table osm as
  select name, level, 'osm' as src, lon, lat, ST_Point(lon, lat) geom
  from read_parquet('{OSM}')""")
con.execute(f"""create table duk as
  select poi_name as name, level, 'dukcapil' as src, lon, lat, ST_Point(lon, lat) geom
  from read_parquet('{DUK}')""")

n_osm, = con.execute("select count(*) from osm").fetchone()
n_duk, = con.execute("select count(*) from duk").fetchone()
print(f"OSM {n_osm:,} / Dukcapil {n_duk:,}")

h("1. By level — which source fills which gap")
print(f"  {'level':10s} {'OSM':>7s} {'Dukcapil':>9s}")
for row in con.execute("""
    select coalesce(o.level, d.level) lv, coalesce(o.c,0) oc, coalesce(d.c,0) dc from
      (select level, count(*) c from osm group by 1) o
      full outer join (select level, count(*) c from duk group by 1) d
        on o.level = d.level
    order by oc + dc desc""").fetchall():
    print(f"  {str(row[0]):10s} {row[1]:>7,} {row[2]:>9,}")

# ---- Union: OSM leads; drop Dukcapil records at the same level within DEDUP_M ----
# OSM leads because it is the only source holding SD/SMP/SMA, and its levels were checked
# against school-name tokens.
con.execute("create index osm_ix on osm using rtree(geom)")
con.execute(f"""create table duk_uniq as
  select * from duk d
  where not exists (
    select 1 from osm o
    where o.level = d.level
      and 111320*sqrt(power(o.lat-d.lat,2)
        + power((o.lon-d.lon)*cos(radians(d.lat)),2)) <= {DEDUP_M})""")
n_uniq, = con.execute("select count(*) from duk_uniq").fetchone()
print(f"\n  Dukcapil {n_duk:,} -> minus same-level matches within {DEDUP_M} m "
      f"-> {n_uniq:,} unique")

con.execute("""create table combined as
  select row_number() over () as school_id, name, level, src, lat, lon
  from (select name, level, src, lat, lon from osm
        union all
        select name, level, src, lat, lon from duk_uniq)""")
n, = con.execute("select count(*) from combined").fetchone()

h("2. Combined")
print(f"  total {n:,}\n")
print(f"  {'level':10s} {'total':>7s} {'osm':>7s} {'dukcapil':>9s}")
for row in con.execute("""
    select level, count(*) c, count(*) filter (where src='osm') o,
           count(*) filter (where src='dukcapil') d
    from combined group by 1 order by c desc""").fetchall():
    print(f"  {str(row[0]):10s} {row[1]:>7,} {row[2]:>7,} {row[3]:>9,}")

os.makedirs(D, exist_ok=True)
con.execute(f"copy combined to '{OUT}' (FORMAT parquet)")
print(f"\nwrote: {OUT}")

h("3. Sets used in the PP 28/2024 analysis")
legal, = con.execute(
    "select count(*) from combined where level in ('TK','SD','SMP','SMA','SLB','PT')"
).fetchone()
a, = con.execute(
    "select count(*) from combined where level in ('SD','SMP','SMA')").fetchone()
print(f"  statutory satuan pendidikan  {legal:,}  (PAUD, madrasah, pesantren, higher ed)")
print(f"  SD/SMP/SMA only              {a:,}  <- **OSM-derived only**")
print("\n  Since Dukcapil holds no SD/SMP/SMA in Semarang, the completeness of that subset")
print("  is exactly OSM's. It is measured against Dapodik in verify_school_completeness.py")
print("  (76.4%).")
