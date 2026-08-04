#!/usr/bin/env python3
"""
マスターのチェーン店取りこぼし（約5割）が**空間的にランダムか、偏っているか**を検定する。

なぜ決定的か
------------
fetch_chains_google_places.py で、マスターのチェーン網羅率が Alfamart 0.55 /
Indomaret 0.48 と判明した。学校バッファ分析（analyze_tobacco_school_buffers.py）の
**絶対数は約半分**になるが、**割合（例: minimarket の 46.7% が学校 200m 圏内）は
「欠落が空間的にランダムなら」保たれる**。

  - 欠落がランダム → 割合は使える。絶対数だけ補正すればよい。
  - 欠落が周縁部に偏る → **割合そのものが偏る**。§3 の結論は使えない。

Overture は Semarang で meta 由来 98.1%＝Facebook ページの有無に依存するため、
商業的な formality が低い周縁部で取りこぼしが増える**理由がある**。仮説として妥当なので
実際に測る。

方法
----
1. 市域を 2km 格子に切り、セルごとに Google 件数とマスター件数を数えて比を出す。
2. 比が「都心からの距離」「店舗密度」と相関するかを見る。
   相関が無ければランダム、あれば偏り。
3. kecamatan（OSM admin_level=6）別にも集計して解釈しやすくする。

出力: docs/semarang/verify_coverage-spatial-bias.csv
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
# Simpang Lima（市の中心）。周縁度の基準点
CX, CY = 110.4229, -6.9932

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def fetch_kecamatan():
    """OSM から Kota Semarang の kecamatan（admin_level=6）ポリゴンを取得。"""
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
        # 環に組み立て（build 側と同じ手順）
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
    print(f"kecamatan {len(feats)} 件 -> {KEC}")
    time.sleep(1)


# ---- 1. セル単位の網羅率 ----
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

con.execute(f"""create table cell as
  select coalesce(g.cx, m.cx) cx, coalesce(g.cy, m.cy) cy,
         coalesce(g.n, 0) g_n, coalesce(m.n, 0) m_n
  from (select cx, cy, count(*) n from g group by 1,2) g
  full outer join (select cx, cy, count(*) n from m group by 1,2) m
    using (cx, cy)""")
# セル中心の座標と都心からの距離
con.execute(f"""create or replace table cell as
  select *, {b[0]} + (cx + 0.5)*{dlon} as lon, {b[2]} + (cy + 0.5)*{dlat} as lat,
         111.320*sqrt(power({b[2]} + (cy+0.5)*{dlat} - {CY}, 2)
           + power(({b[0]} + (cx+0.5)*{dlon} - {CX})*0.99255, 2)) as dist_km,
         case when g_n > 0 then m_n::double / g_n else null end as ratio
  from cell""")

n_cell, = con.execute("select count(*) from cell where g_n > 0").fetchone()
h(f"① セル単位の網羅率（{CELL_KM}km 格子・Google に1件以上あるセル {n_cell} 個）")
r = con.execute("""select round(min(ratio),2), round(quantile_cont(ratio,0.25),2),
    round(median(ratio),2), round(quantile_cont(ratio,0.75),2), round(max(ratio),2)
    from cell where g_n > 0""").fetchone()
print(f"  ratio(マスター/Google)  min={r[0]}  p25={r[1]}  median={r[2]}  p75={r[3]}  max={r[4]}")

h("② 都心からの距離帯別の網羅率 ← **これが偏りの検定**")
print(f"  {'距離帯':12s} {'セル':>5s} {'Google':>7s} {'マスター':>8s} {'網羅率':>7s}")
for lo, hi in [(0, 2), (2, 4), (4, 6), (6, 8), (8, 12), (12, 99)]:
    row = con.execute(f"""select count(*), sum(g_n), sum(m_n) from cell
        where g_n > 0 and dist_km >= {lo} and dist_km < {hi}""").fetchone()
    if row[0]:
        rate = row[2] / row[1] if row[1] else 0
        bar = "#" * int(rate * 40)
        print(f"  {f'{lo}-{hi}km':12s} {row[0]:>5,} {row[1]:>7,} {row[2]:>8,} "
              f"{rate:>6.2f} {bar}")

h("③ 相関（負なら周縁ほど網羅率が低い＝偏りあり）")
c = con.execute("""select corr(dist_km, ratio), corr(g_n, ratio), count(*)
    from cell where g_n > 0""").fetchone()
print(f"  corr(都心からの距離, 網羅率) = {c[0]:+.3f}")
print(f"  corr(セル内Google店舗数, 網羅率) = {c[1]:+.3f}   (n={c[2]})")
print("\n  解釈:")
print("   |r| < 0.2 程度なら実質ランダム → 割合は使える（絶対数だけ補正）")
print("   負に大きいなら周縁で取りこぼしが多い → **割合そのものが偏る**")

# ---- 2. kecamatan 別 ----
try:
    fetch_kecamatan()
    con.execute(f"""create table kec as
      select name, geom::GEOMETRY geom from ST_Read('{KEC}')""")
    nk, = con.execute("select count(*) from kec").fetchone()
    h(f"④ kecamatan 別の網羅率（{nk} 区）")
    con.execute("""create table kecstat as
      select k.name,
        (select count(*) from g where ST_Contains(k.geom, ST_Point(g.lon, g.lat))) g_n,
        (select count(*) from m where ST_Contains(k.geom, ST_Point(m.lon, m.lat))) m_n
      from kec k""")
    print(f"  {'kecamatan':22s} {'Google':>7s} {'マスター':>8s} {'網羅率':>7s}")
    for row in con.execute("""select name, g_n, m_n,
        case when g_n > 0 then m_n::double/g_n end r
        from kecstat order by r nulls last""").fetchall():
        bar = "#" * int((row[3] or 0) * 30)
        print(f"  {str(row[0])[:20]:22s} {row[1]:>7,} {row[2]:>8,} "
              f"{(row[3] or 0):>6.2f} {bar}")
    con.execute(f"copy (select name as kecamatan, g_n as google_n, m_n as master_n, "
                f"case when g_n>0 then round(m_n::double/g_n,3) end as coverage_ratio "
                f"from kecstat order by coverage_ratio) to '{OUT}' (header, delimiter ',')")
    print(f"\n出力: {OUT}")
except Exception as e:  # noqa: BLE001
    print(f"\nkecamatan 取得に失敗（セル単位の結論は有効）: {e}")
