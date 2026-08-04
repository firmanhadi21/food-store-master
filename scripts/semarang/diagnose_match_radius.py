#!/usr/bin/env python3
"""
Overture と OSM が同じチェーン店をどれだけ共有しているかを、突合半径を変えて測る。

なぜ必要か
----------
compare_sources_semarang.py で「100m 以内で一致するのは Alfamart 84 件中 18 件だけ」
という結果が出た。解釈は2通りあり、どちらかで設計判断が正反対になる:

  仮説1: 両ソースは**別々の実在店舗**を捉えている（真に相補的）
         → 和集合が正しい。日本と逆に「OSM ∪ Overture」を採るべき。
  仮説2: 同一店舗だが**座標がズレていて突合に失敗**している
         → 和集合は水増し。日本と同じく単一ソース優先にすべき。

判別法: 突合半径を広げて一致数の伸びを見る。
  - 早期に飽和 → 仮説1（半径を広げても一致しない＝別の店）
  - 伸び続ける → 仮説2（座標ズレ）

あわせて ST_Area_Spheroid が nan を返す件（CLAUDE.md 既知）を等距円筒近似で回避し、
市域ポリゴンの組み立てが正しいかを面積で検算する。
"""
import duckdb

D = "data/semarang"
POLY = f"{D}/semarang_boundary_poly.geojson"

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("⓪ 市域ポリゴンの検算（ST_Area_Spheroid は この環境で nan を返す）")
# 等距円筒近似: 緯度 -7 度付近なので経度1度 ≒ 111,320*cos(7°) m
a_deg, = con.execute("select ST_Area(geom) from kota").fetchone()
km2 = a_deg * 111.320 * 111.320 * 0.99255  # cos(7°)
print(f"  ST_Area(度^2) = {a_deg:.6f}")
print(f"  等距円筒近似   = {km2:,.1f} km2   （Kota Semarang 公称 373.8 km2）")
print(f"  → 比 {km2 / 373.8:.3f}   1.0 付近ならリング組み立ては正しい")

con.execute(f"""create table ov as
  select name, category, brand_name, lon, lat, ST_Point(lon, lat) geom
  from read_parquet('{D}/overture_semarang_all.parquet')
  where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
con.execute(f"""create table osm as
  select name, shop, amenity, brand, lon, lat, ST_Point(lon, lat) geom
  from read_parquet('{D}/osm_semarang_food.parquet')
  where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")

h("① 突合半径を変えたときの一致数（仮説1 vs 仮説2 の判別）")
# 緯度1度 ≒ 111,320m。経度側は cos(7°)≒0.9926 なのでほぼ等方、度で近似してよい
RADII = [(50, 0.00045), (100, 0.0009), (200, 0.0018), (300, 0.0027),
         (500, 0.0045), (1000, 0.0090)]
for kw in ["alfamart", "indomaret"]:
    nov, = con.execute(f"select count(*) from ov where name ilike '%{kw}%'").fetchone()
    nosm, = con.execute(f"select count(*) from osm where name ilike '%{kw}%'").fetchone()
    print(f"\n  {kw}  (Overture {nov} / OSM {nosm})")
    print(f"    {'半径':>8s} {'一致':>6s} {'OSM側の一致率':>14s} {'和集合':>8s}")
    for m, deg in RADII:
        k, = con.execute(f"""
          select count(*) from osm o where o.name ilike '%{kw}%'
            and exists (select 1 from ov v where v.name ilike '%{kw}%'
                        and ST_DWithin(o.geom, v.geom, {deg}))""").fetchone()
        print(f"    {m:>6d}m {k:>6,} {k / nosm * 100:>13.1f}% {nov + nosm - k:>8,}")

h("② 対照: 同一ソース内で最近隣の同ブランド店までの距離（店舗の実際の粗密）")
# 隣の Alfamart までの距離が 200m しかない密集地なら、突合半径 200m は使えない
for src, tbl, f in [("Overture", "ov", "name ilike '%alfamart%'"),
                    ("OSM", "osm", "name ilike '%alfamart%'")]:
    row = con.execute(f"""
      with p as (select lon, lat from {tbl} where {f}),
      d as (select a.lon, a.lat,
                   min(111320*sqrt(power(b.lat-a.lat,2)
                     + power((b.lon-a.lon)*cos(radians(a.lat)),2))) m
            from p a join p b on (a.lon,a.lat) != (b.lon,b.lat) group by 1,2)
      select round(min(m)), round(quantile_cont(m,0.1)), round(median(m)),
             round(quantile_cont(m,0.9)) from d""").fetchone()
    print(f"  {src:9s} 最近隣Alfamart間距離  min={row[0]:>5.0f}m p10={row[1]:>5.0f}m "
          f"median={row[2]:>5.0f}m p90={row[3]:>5.0f}m")

h("③ OSM 独自の Alfamart/Indomaret は本当に「別の店」か（近傍に何があるか）")
for row in con.execute("""
    select o.name,
           (select count(*) from ov v
            where ST_DWithin(o.geom, v.geom, 0.0009)) as ov_any_poi,
           (select count(*) from ov v where v.category='convenience_store'
            and ST_DWithin(o.geom, v.geom, 0.0009)) as ov_cvs
    from osm o
    where (o.name ilike '%alfamart%' or o.name ilike '%indomaret%')
      and not exists (select 1 from ov v
                      where (v.name ilike '%alfamart%' or v.name ilike '%indomaret%')
                        and ST_DWithin(o.geom, v.geom, 0.0009))
    order by ov_any_poi limit 15""").fetchall():
    print(f"  {str(row[0])[:34]:36s} 100m以内の Overture POI={row[1]:>3,} "
          f"うち convenience={row[2]}")
n_iso, = con.execute("""
    select count(*) from osm o
    where (o.name ilike '%alfamart%' or o.name ilike '%indomaret%')
      and not exists (select 1 from ov v
                      where (v.name ilike '%alfamart%' or v.name ilike '%indomaret%')
                        and ST_DWithin(o.geom, v.geom, 0.0009))
      and not exists (select 1 from ov v where v.category='convenience_store'
                      and ST_DWithin(o.geom, v.geom, 0.0009))""").fetchone()
print(f"\n  OSM独自ミニマーケットのうち、100m以内に Overture の convenience が"
      f"**1件も無い**もの = {n_iso} 件")
print("  （これが多いほど「Overture が丸ごと取りこぼした実在店舗」＝仮説1 の裏付け）")
