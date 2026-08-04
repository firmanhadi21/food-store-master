#!/usr/bin/env python3
"""
Build the Kota Semarang food store master (Semarang Phase 1).

Design changes from the Japan version (build_food_store_master.py), all evidence-driven
------------------------------------------------------------------------------------
1. **Take the union of sources.** The Japan version states "prefer a single best source per
   category; do not use unions." There, convenience stores reached 97.6% from Overture alone
   and a naive union inflated counts to 133%. Semarang inverts this. From
   diagnose_match_radius.py:
     - match counts plateau across the interpretable 50-200 m band (Alfamart 17 -> 18 -> 22)
     - median nearest-neighbour distance between same-brand stores is 524 m, so any match
       radius above ~200 m is picking up a *different* store, not the same one
     - 119 OSM-only minimarkets have **no Overture convenience store at all** within 100 m
   => the sources are genuinely complementary; the union is correct.

2. **OSM is the only usable source for pasar.** Measured: OSM 61 vs Overture 10. Traditional
   markets are the dominant fresh-food channel, so making Overture primary would understate
   fresh food access roughly sixfold.

3. **The drugstore category is dropped** — Indonesian apotek do not sell food, unlike the
   Japanese drugstores the MAFF definition includes.

4. **Name-driven classification, category as weak prior** (see semarang_food_rules.py).

Input:  data/semarang/overture_semarang_all.parquet
        data/semarang/osm_semarang_food.parquet
        data/semarang/semarang_boundary_poly.geojson
Output: data/semarang/semarang_food_master.parquet / .csv
"""
import os
import sys

import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semarang_food_rules import (  # noqa: E402
    CATEGORIES, classify_osm_sql, classify_overture_sql,
)

D = "data/semarang"
POLY = f"{D}/semarang_boundary_poly.geojson"
OUT_PARQUET = f"{D}/semarang_food_master.parquet"
OUT_CSV = f"{D}/semarang_food_master.csv"

# 100 m ~ 0.0009 degrees. Semarang sits at latitude -7 where cos ~ 0.993, so the grid is
# near-isotropic and degrees are an acceptable approximation.
DEDUP_DEG = 0.0009

# Confidence floor for Overture. Measured medians: grocery_store 0.489,
# convenience_store 0.699, supermarket 0.8. The Japan version needed no threshold;
# Semarang does, because 98% of records are Meta-derived and quality is lower.
MIN_CONF = 0.30


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main():
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")

    # ---- 1. Overture: clip to the city, then classify ----
    con.execute(f"""create table ov_raw as
      select name, category, confidence, brand_name, lon, lat, ST_Point(lon, lat) geom
      from read_parquet('{D}/overture_semarang_all.parquet')
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))
        and coalesce(confidence, 0) >= {MIN_CONF}""")
    con.execute(f"""create table ov as
      select {classify_overture_sql()} as cat, name, brand_name as brand,
             'overture' as src, confidence, lon, lat, geom
      from ov_raw""")
    con.execute("create table ov_hit as select * from ov where cat is not null")

    # ---- 2. OSM: clip, then classify ----
    con.execute(f"""create table osm_raw as
      select name, shop, amenity, brand, operator, lon, lat, ST_Point(lon, lat) geom
      from read_parquet('{D}/osm_semarang_food.parquet')
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    con.execute(f"""create table osm as
      select {classify_osm_sql()} as cat, name, coalesce(brand, operator) as brand,
             'osm' as src, null::double as confidence, lon, lat, geom
      from osm_raw""")
    con.execute("create table osm_hit as select * from osm where cat is not null")

    h("1. Classification result (within city limits, before deduplication)")
    nov_raw, = con.execute("select count(*) from ov_raw").fetchone()
    nosm_raw, = con.execute("select count(*) from osm_raw").fetchone()
    nov, = con.execute("select count(*) from ov_hit").fetchone()
    nosm, = con.execute("select count(*) from osm_hit").fetchone()
    print(f"  Overture: {nov_raw:,} in city (conf>={MIN_CONF}) -> {nov:,} food retail")
    print(f"  OSM:      {nosm_raw:,} in city              -> {nosm:,} food retail")
    print(f"\n  {'category':16s} {'Overture':>10s} {'OSM':>8s}")
    for cat in CATEGORIES:
        a, = con.execute(f"select count(*) from ov_hit where cat='{cat}'").fetchone()
        b, = con.execute(f"select count(*) from osm_hit where cat='{cat}'").fetchone()
        print(f"  {cat:16s} {a:>10,} {b:>8,}")

    # ---- 3. Union: prefer OSM, drop Overture records it already covers ----
    # OSM is preferred because its brand fill rate is 83.8% against Overture's 27.8% and its
    # tags are hand-placed. Overture still contributes the bulk of the volume.
    #
    # ** Matching on category and distance alone is WRONG here.** In Indonesia Alfamart and
    #   Indomaret deliberately open directly opposite one another, so a 100 m
    #   same-category merge collapses two genuinely different stores into one. A chain key
    #   is therefore part of the match condition.
    for tbl in ("ov_hit", "osm_hit"):
        con.execute(f"""create or replace table {tbl} as
          select *, case
            when name ilike '%alfamidi%'  then 'alfamidi'
            when name ilike '%alfamart%' or name ilike '%alfa mart%' then 'alfamart'
            when name ilike '%indomaret%' or name ilike '%indomart%' then 'indomaret'
            when name ilike '%superindo%' or name ilike '%super indo%' then 'superindo'
            when name ilike '%transmart%' then 'transmart'
            when name ilike '%hypermart%' then 'hypermart'
            when name ilike '%gelael%'    then 'gelael'
            when name ilike '%circle k%'  then 'circlek'
            else null end as chain from {tbl}""")

    con.execute("create index osm_ix on osm_hit using rtree(geom)")
    # Where a chain is identifiable, require the chains to agree; otherwise fall back to
    # category proximity alone.
    MATCH = ("o.cat = v.cat and (v.chain is null or o.chain is null "
             "or v.chain = o.chain)")
    con.execute(f"""create table ov_uniq as
      select * from ov_hit v
      where not exists (select 1 from osm_hit o
                        where {MATCH} and ST_DWithin(v.geom, o.geom, {DEDUP_DEG}))""")

    # Remove within-source duplicates too (Overture keeps one record per contributing
    # dataset for the same physical store).
    #
    # ** The first version bucketed by grid cell (floor(lat/deg)) plus exact name, which
    #   **cannot catch a 20 m pair straddling a cell boundary** — it removed exactly zero
    #   records (707 -> 707), and verification then reported "12.9% of minimarkets have
    #   another minimarket within 50 m". Replaced with true spatial neighbour search,
    #   keeping the first member of each cluster.
    con.execute("""create table ov_seq as
      select *, row_number() over (order by confidence desc nulls last, name) as seq
      from ov_uniq""")
    con.execute("create index ov_seq_ix on ov_seq using rtree(geom)")
    con.execute(f"""create table ov_dedup as
      select * exclude (seq) from ov_seq a
      where not exists (
        select 1 from ov_seq b
        where b.cat = a.cat and b.seq < a.seq
          and (a.chain is null or b.chain is null or a.chain = b.chain)
          and ST_DWithin(a.geom, b.geom, {DEDUP_DEG}))""")

    con.execute("""create table master_raw as
      select cat, name, brand, src, confidence, lon, lat, geom from osm_hit
      union all
      select cat, name, brand, src, confidence, lon, lat, geom from ov_dedup""")

    h("2. Effect of deduplication")
    n_ovu, = con.execute("select count(*) from ov_uniq").fetchone()
    n_ovd, = con.execute("select count(*) from ov_dedup").fetchone()
    print(f"  Overture {nov:,} -> minus OSM overlap {n_ovu:,} -> minus internal {n_ovd:,}")
    print(f"  OSM {nosm:,} (all kept)")
    print(f"  -> master candidates {n_ovd + nosm:,}")

    # ---- 4. Output ----
    con.execute("""create table master as
      select row_number() over (order by cat, name) as store_id,
             cat, name, brand, src, confidence, lat, lng, geom
      from (select cat, name, brand, src, confidence, lat, lon as lng, geom
            from master_raw)""")
    n, = con.execute("select count(*) from master").fetchone()

    h("3. Final master")
    print(f"  total {n:,}\n")
    print(f"  {'category':16s} {'total':>7s} {'overture':>9s} {'osm':>6s}  {'named':>8s}")
    for cat in CATEGORIES:
        r = con.execute(f"""select count(*),
            count(*) filter (where src='overture'), count(*) filter (where src='osm'),
            count(name) from master where cat='{cat}'""").fetchone()
        print(f"  {cat:16s} {r[0]:>7,} {r[1]:>9,} {r[2]:>6,}  {r[3]:>8,}")

    os.makedirs(D, exist_ok=True)
    con.execute(f"copy (select store_id,cat,name,brand,src,confidence,lat,lng,geom "
                f"from master) to '{OUT_PARQUET}' (FORMAT parquet)")
    con.execute(f"copy (select store_id,cat,name,brand,src,confidence,lat,lng "
                f"from master) to '{OUT_CSV}' (header, delimiter ',')")
    print(f"\nwrote: {OUT_PARQUET}")
    print(f"wrote: {OUT_CSV}")

    h("4. Chain counts (the only externally verifiable handle)")
    for kw in ["alfamart", "indomaret", "alfamidi", "superindo"]:
        r = con.execute(f"""select count(*), count(*) filter (where src='osm'),
            count(*) filter (where src='overture')
            from master where name ilike '%{kw}%'""").fetchone()
        print(f"  {kw:12s} {r[0]:>4,}  (osm {r[1]:>3,} / overture {r[2]:>3,})")
    print("\n  Note: '%superindo%' misses 'Super Indo' written with a space; see"
          "\n  estimate_chain_truth.py for the chain-key version used in analysis.")


if __name__ == "__main__":
    main()
