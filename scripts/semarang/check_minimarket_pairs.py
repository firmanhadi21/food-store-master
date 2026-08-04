#!/usr/bin/env python3
"""minimarket の 50m 以内ペアが「名寄せ漏れ」か「実在の向かい合わせ出店」かを判別する。

インドネシアでは Alfamart と Indomaret が意図的に至近距離へ出店するため、
50m 以内に同カテゴリ他店があること自体は異常ではない。
**同一チェーン同士**のペアだけが名寄せ漏れの疑い。
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
    else '(その他)' end as chain
  from {M} where cat='minimarket'""")
con.execute("create index m_ix on m using rtree(geom)")

print("=== 50m 以内の minimarket ペアの内訳 ===")
rows = con.execute("""
  select a.chain, b.chain, count(*) c,
         round(avg(111320*sqrt(power(b.lat-a.lat,2)
           + power((b.lng-a.lng)*cos(radians(a.lat)),2)))) avg_m
  from m a join m b on a.store_id < b.store_id
    and ST_DWithin(a.geom, b.geom, 0.00045)
  group by 1,2 order by c desc""").fetchall()
same = cross = 0
for a, b, c, d in rows:
    kind = "★同一チェーン＝名寄せ漏れの疑い" if a == b and a != '(その他)' else ""
    if a == b and a != '(その他)':
        same += c
    else:
        cross += c
    print(f"  {a:12s} × {b:12s} {c:>4,} 組  平均 {d:>3.0f}m  {kind}")

print(f"\n  同一チェーンのペア   {same:>4,} 組  ← 名寄せ漏れ")
print(f"  異チェーン/不明ペア {cross:>4,} 組  ← 実在の近接出店（正常）")

print("\n=== 同一チェーンで 50m 以内のもの（ソース別・重複の出どころ）===")
for r in con.execute("""
  select a.chain, a.src, b.src, count(*) c
  from m a join m b on a.store_id < b.store_id
    and ST_DWithin(a.geom, b.geom, 0.00045) and a.chain = b.chain
  where a.chain != '(その他)'
  group by 1,2,3 order by c desc""").fetchall():
    print(f"  {r[0]:12s} {r[1]:9s} × {r[2]:9s} {r[3]:>4,} 組")

print("\n=== 最終マスター サマリ ===")
for r in con.execute(f"""
  select cat, count(*) n, count(*) filter (where src='osm') osm,
         count(*) filter (where src='overture') ov
  from {M} group by 1 order by n desc""").fetchall():
    print(f"  {r[0]:16s} {r[1]:>5,}  (osm {r[2]:>4,} / overture {r[3]:>4,})")
n, = con.execute(f"select count(*) from {M}").fetchone()
print(f"  {'合計':16s} {n:>5,}")
