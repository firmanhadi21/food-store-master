#!/usr/bin/env python3
"""
Kota Semarang 食料品店マスター構築（Semarang Phase1）

日本版 build_food_store_master.py からの設計変更（すべて実測に基づく）
--------------------------------------------------------------------
1. **和集合を採る**（日本版は「単一ソース優先・∪は原則使わない」）
   日本のコンビニは Overture 単独で実数の 97.6% を取れ、素朴な和集合は 133% に膨張した。
   Semarang は逆で、diagnose_match_radius.py の実測により:
     - OSM 独自のミニマーケット 119 件は、100m 以内に Overture の convenience が**1件も無い**
     - 突合率は 50m→100m でほぼ横ばい（Alfamart 17→18）＝座標ズレではなく**別の実在店舗**
   → 両ソースは真に相補的。和集合が正しい。

2. **OSM を pasar の唯一ソースにする**
   実測 OSM 61 件 vs Overture 10 件。伝統市場は生鮮アクセスの主役なので、
   ここで Overture を主にすると生鮮アクセスを 6 倍過小評価する。

3. **drugstore カテゴリを廃止**（インドネシアの apotek は食料品を扱わない）

4. **name 主・category 従の分類**（semarang_food_rules.py 参照）

入力:
  data/semarang/overture_semarang_all.parquet
  data/semarang/osm_semarang_food.parquet
  data/semarang/semarang_boundary_poly.geojson
出力:
  data/semarang/semarang_food_master.parquet / .csv
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

# 100m ≒ 0.0009 度。Semarang は緯度 -7 度で cos≒0.993 なのでほぼ等方、度で近似してよい。
DEDUP_DEG = 0.0009

# Overture の低 confidence を切る閾値。実測の median は grocery_store 0.489 /
# convenience_store 0.699 / supermarket 0.8。日本版に閾値は無かったが、
# Semarang は meta 由来 98% で品質が低いため足切りする。
MIN_CONF = 0.30


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main():
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")

    # ---- 1. Overture: 市域クリップ → 分類 ----
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

    # ---- 2. OSM: 市域クリップ → 分類 ----
    con.execute(f"""create table osm_raw as
      select name, shop, amenity, brand, operator, lon, lat, ST_Point(lon, lat) geom
      from read_parquet('{D}/osm_semarang_food.parquet')
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    con.execute(f"""create table osm as
      select {classify_osm_sql()} as cat, name, coalesce(brand, operator) as brand,
             'osm' as src, null::double as confidence, lon, lat, geom
      from osm_raw""")
    con.execute("create table osm_hit as select * from osm where cat is not null")

    h("① 分類結果（市域内・重複排除前）")
    nov_raw, = con.execute("select count(*) from ov_raw").fetchone()
    nosm_raw, = con.execute("select count(*) from osm_raw").fetchone()
    nov, = con.execute("select count(*) from ov_hit").fetchone()
    nosm, = con.execute("select count(*) from osm_hit").fetchone()
    print(f"  Overture: 市域内 {nov_raw:,} 件（conf>={MIN_CONF}） → 食料品店 {nov:,} 件")
    print(f"  OSM:      市域内 {nosm_raw:,} 件              → 食料品店 {nosm:,} 件")
    print(f"\n  {'カテゴリ':16s} {'Overture':>10s} {'OSM':>8s}")
    for cat in CATEGORIES:
        a, = con.execute(f"select count(*) from ov_hit where cat='{cat}'").fetchone()
        b, = con.execute(f"select count(*) from osm_hit where cat='{cat}'").fetchone()
        print(f"  {cat:16s} {a:>10,} {b:>8,}")

    # ---- 3. 和集合（OSM を優先し、Overture 側の重複を落とす）----
    # OSM 優先の理由: ブランド付与率 83.8% vs 27.8%、タグが人手で信頼できる。
    # ただし件数は Overture の方が多いので、OSM に無いものは Overture から拾う。
    #
    # ★ 重複判定は「同カテゴリ・近接」だけでは**誤り**。インドネシアでは
    #   Alfamart と Indomaret が**意図的に向かい合わせに出店する**ため、
    #   カテゴリだけで 100m 名寄せすると別チェーンの実在2店が1店に潰れる。
    #   → チェーンキー（判別できる場合）を一致条件に加える。
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
    # チェーンが判別できるものは chain 一致を要求、できないものはカテゴリ近接のみで判定
    MATCH = ("o.cat = v.cat and (v.chain is null or o.chain is null "
             "or v.chain = o.chain)")
    con.execute(f"""create table ov_uniq as
      select * from ov_hit v
      where not exists (select 1 from osm_hit o
                        where {MATCH} and ST_DWithin(v.geom, o.geom, {DEDUP_DEG}))""")

    # ソース内の重複も落とす（Overture は同一店が提供元ごとに別レコードで残る）。
    #
    # ★ 第1版はグリッドセル（floor(lat/deg)）+ 完全一致名でバケット化していたが、
    #   これでは **セル境界をまたぐ 20m 差のペアが落ちない**（実際 707→707 で1件も
    #   除去されず、検証で「minimarket の 12.9% が 50m 以内に同カテゴリ他店あり」と出た）。
    #   → 真の空間近傍で「クラスタの先頭だけ残す」方式に変更する。
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

    h("② 重複排除の効果")
    n_ovu, = con.execute("select count(*) from ov_uniq").fetchone()
    n_ovd, = con.execute("select count(*) from ov_dedup").fetchone()
    print(f"  Overture {nov:,} → OSM と重複除去 {n_ovu:,} → ソース内重複除去 {n_ovd:,}")
    print(f"  OSM {nosm:,}（全採用）")
    print(f"  → マスター候補 {n_ovd + nosm:,} 件")

    # ---- 4. 出力 ----
    con.execute("""create table master as
      select row_number() over (order by cat, name) as store_id,
             cat, name, brand, src, confidence, lat, lng, geom
      from (select cat, name, brand, src, confidence, lat, lon as lng, geom
            from master_raw)""")
    n, = con.execute("select count(*) from master").fetchone()

    h("③ 最終マスター")
    print(f"  合計 {n:,} 件\n")
    print(f"  {'カテゴリ':16s} {'計':>7s} {'overture':>9s} {'osm':>6s}  {'名称あり':>8s}")
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
    print(f"\n出力: {OUT_PARQUET}")
    print(f"出力: {OUT_CSV}")

    h("④ チェーン実数チェック（外部検証できる唯一の足がかり）")
    for kw in ["alfamart", "indomaret", "alfamidi", "superindo"]:
        r = con.execute(f"""select count(*), count(*) filter (where src='osm'),
            count(*) filter (where src='overture')
            from master where name ilike '%{kw}%'""").fetchone()
        print(f"  {kw:12s} 計 {r[0]:>4,}  (osm {r[1]:>3,} / overture {r[2]:>3,})")


if __name__ == "__main__":
    main()
