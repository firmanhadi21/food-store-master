#!/usr/bin/env python3
"""
OSM と Dukcapil の学校レイヤを統合する。

なぜ統合するのか — 店舗マスターと同じ「真に相補的」の構図
----------------------------------------------------------
2ソースは**互いに独立**（OSM は現地マッパー、Dukcapil は Kemendikbud/Dapodik 由来）で、
かつ**補完し合う穴の形が違う**。実測（市域内）:

  OSM      2,017 件  … SD 507 / SMP 145 / SMA 152 / TK 1,110
  Dukcapil 1,781 件  … TK 1,378 / PT 270 / informal 40 / SLB 16 / SMA 1 / **SD・SMP は 0**

★ Dukcapil の致命的な穴（実測して確認した）:
  - Semarang bbox で tags='Elementary School' が **0 件**、'Junior High School' も **0 件**。
    全国では Elementary 54,159 / Junior High 93,714 件あるので、**地域的に不均一**な収録。
  - 'Senior High School' というタグは**全国どこにも存在しない**（count=0）。
    "High" の 95,457 件はすべて Junior High のマッチ。
  → **SD/SMP/SMA については Dukcapil は使えず、OSM が唯一のソース。**

★ 一方で Dukcapil が効く領域:
  - Dukcapil 1,781 件のうち OSM に 100m 以内の対応が無いもの **549 件**（30.8%）。
    大半が TK/PAUD で、PP 28/2024 の satuan pendidikan に幼稚園が含まれる解釈を採る場合に効く。

→ 結論: **和集合を採る。** SD/SMP/SMA は OSM 由来のみ、TK/PAUD は両ソースの和集合。
   店舗マスターで Overture∪OSM を採ったのと同じ判断（片方にしか無い実体が多数ある）。

重複排除の注意
--------------
店舗で Alfamart と Indomaret を潰しかけたのと同じ理由で、**段階（level）が違う施設を
近接だけで統合してはいけない**。同一敷地に TK と SD が併設されるのは普通なので、
level が一致する場合のみ重複とみなす。

出力: data/semarang/schools_semarang_combined.parquet
"""
import os

import duckdb

D = "data/semarang"
OSM = f"{D}/osm_schools_semarang.parquet"
DUK = f"{D}/dukcapil_schools_semarang.parquet"
OUT = f"{D}/schools_semarang_combined.parquet"

# ★ 学校は 150m。店舗（100m）より緩くする。
#
#   理由は**施設の性質**であって Dapodik に合わせたからではない: 店舗は間口が数mの点だが、
#   学校は敷地（校庭・複数棟）を持つため、ソースごとに代表点の取り方が違う
#   （門／校舎／敷地重心）。同一園でも 100〜200m ずれる。
#
#   実測（verify_school_completeness.py）: OSM×Dukcapil の TK で、100m では一致 0 件だが
#   150m で 128 件、200m で 239 件が一致する。100m のままだと同一園が二重計上され、
#   TK が 1,590 件＝Dapodik 公表 1,439 件の 110.5% に膨らんでいた。
#   150m にすると 1,462 件（101.6%）となり公表値とほぼ一致する。
#   ※ 公表値との一致は**裏付け**であって根拠ではない。根拠は上記の代表点のばらつき。
#
#   なお SD/SMP/SMA は Dukcapil が Semarang に1件も持たないため、この値を変えても
#   集合A には影響しない（影響するのは TK/PT/SLB のみ）。
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
print(f"OSM {n_osm:,} 件 / Dukcapil {n_duk:,} 件")

h("① 段階別の突き合わせ（どちらがどこを埋めるか）")
print(f"  {'level':10s} {'OSM':>7s} {'Dukcapil':>9s}")
for row in con.execute("""
    select coalesce(o.level, d.level) lv, coalesce(o.c,0) oc, coalesce(d.c,0) dc from
      (select level, count(*) c from osm group by 1) o
      full outer join (select level, count(*) c from duk group by 1) d
        on o.level = d.level
    order by oc + dc desc""").fetchall():
    print(f"  {str(row[0]):10s} {row[1]:>7,} {row[2]:>9,}")

# ---- 和集合。OSM を優先し、Dukcapil 側の「同 level・100m 以内」を重複として落とす ----
# OSM 優先の理由: SD/SMP/SMA を持つ唯一のソースであり、level 判定も校名から検証済み。
con.execute("create index osm_ix on osm using rtree(geom)")
DEG = DEDUP_M / 111320.0
con.execute(f"""create table duk_uniq as
  select * from duk d
  where not exists (
    select 1 from osm o
    where o.level = d.level
      and 111320*sqrt(power(o.lat-d.lat,2)
        + power((o.lon-d.lon)*cos(radians(d.lat)),2)) <= {DEDUP_M})""")
n_uniq, = con.execute("select count(*) from duk_uniq").fetchone()
print(f"\n  Dukcapil {n_duk:,} → OSM と同 level・{DEDUP_M}m 以内を除去 → 独自 {n_uniq:,} 件")

con.execute("""create table combined as
  select row_number() over () as school_id, name, level, src, lat, lon
  from (select name, level, src, lat, lon from osm
        union all
        select name, level, src, lat, lon from duk_uniq)""")
n, = con.execute("select count(*) from combined").fetchone()

h("② 統合後")
print(f"  合計 {n:,} 件\n")
print(f"  {'level':10s} {'計':>7s} {'osm':>7s} {'dukcapil':>9s}")
for row in con.execute("""
    select level, count(*) c, count(*) filter (where src='osm') o,
           count(*) filter (where src='dukcapil') d
    from combined group by 1 order by c desc""").fetchall():
    print(f"  {str(row[0]):10s} {row[1]:>7,} {row[2]:>7,} {row[3]:>9,}")

con.execute(f"copy combined to '{OUT}' (FORMAT parquet)")
print(f"\n出力: {OUT}")

h("③ PP 28/2024 の分析に使う集合")
a, = con.execute(
    "select count(*) from combined where level in ('SD','SMP','SMA')").fetchone()
c, = con.execute(
    "select count(*) from combined where level in ('SD','SMP','SMA','TK')").fetchone()
print(f"  A 小中高のみ            {a:,} 校  ← **OSM 由来のみ**（Dukcapil に SD/SMP が無い）")
print(f"  C 幼稚園含む            {c:,} 校  ← Dukcapil の寄与はここに出る")
print("\n  ※ Dukcapil は SD/SMP/SMA を Semarang で1件も持たないため、A の網羅性は")
print("     OSM 単独と変わらない。**A の網羅性検証は依然として未解決の課題**。")
