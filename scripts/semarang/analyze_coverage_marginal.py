#!/usr/bin/env python3
"""
「warung / toko kelontong を補完する価値があるか」を、補完する前に見積もる。

考え方（日本版 verify_master_quality.py の枠組みをそのまま使う）
----------------------------------------------------------------
アクセス指標は「最近隣店舗までの距離が閾値を超えるか」という二値。したがって:
  - 過剰（既に圏内の場所に店を足す）→ **判定は1ミリも変わらない**
  - 欠落が効くのは「その店がその地点で唯一の店だった」ときだけ

→ カテゴリを入れ子に足していったときの**限界寄与**を測れば、
   「kelontong を補完したら何が変わるか」の上限が分かる。

ここでは人口を接続していないので **面積ベース**で測る。
Kota Semarang は南部（Gunungpati / Mijen）に人口希薄な丘陵を抱えるため、
面積ベースは圏外率を過大に出す。人口加重は次段（Podes / WorldPop）の課題。

出力: docs/semarang/検証_カバレッジ限界寄与.csv
"""
import os

import duckdb

D = "data/semarang"
M = f"read_parquet('{D}/semarang_food_master.parquet')"
POLY = f"{D}/semarang_boundary_poly.geojson"
OUT = "docs/semarang/検証_カバレッジ限界寄与.csv"

GRID_M = 250       # 判定格子。500m 閾値の半分
THRESHOLDS = [300, 500, 1000]

# 入れ子。日本版 validate_access_difficulty.py の NESTED と同じ思想。
# 「生鮮が買えるか」を先に置き、包装食品しか無い業態を後から足す順序にしている。
NESTED = [
    ("F1 pasar のみ", "['pasar']"),
    ("F2 +supermarket", "['pasar','supermarket']"),
    ("F3 +fresh_food", "['pasar','supermarket','fresh_food']"),
    ("F4 +minimarket", "['pasar','supermarket','fresh_food','minimarket']"),
    ("F5 +toko_kelontong(全カテゴリ)",
     "['pasar','supermarket','fresh_food','minimarket','toko_kelontong']"),
]

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


# ---- 1. 市域を覆う 250m 格子 ----
# 緯度 -7 度。等距円筒近似（この環境の DuckDB は spheroid 系が nan を返す）
b = con.execute("""select ST_XMin(geom), ST_XMax(geom), ST_YMin(geom), ST_YMax(geom)
                   from kota""").fetchone()
dlat = GRID_M / 111320.0
dlon = GRID_M / (111320.0 * 0.99255)
nx = int((b[1] - b[0]) / dlon) + 1
ny = int((b[3] - b[2]) / dlat) + 1
print(f"格子 {nx} x {ny} = {nx*ny:,} セル（{GRID_M}m）")

con.execute(f"""create table cell as
  select {b[0]} + (i + 0.5) * {dlon} as lng,
         {b[2]} + (j + 0.5) * {dlat} as lat
  from range(0, {nx}) t(i), range(0, {ny}) u(j)""")
con.execute("""create table grid as
  select row_number() over () id, lng, lat, ST_Point(lng, lat) geom
  from cell c where exists (select 1 from kota k where ST_Contains(k.geom, c_pt))
  """.replace("c_pt", "ST_Point(c.lng, c.lat)"))
ncell, = con.execute("select count(*) from grid").fetchone()
print(f"市域内セル {ncell:,} 件 = {ncell * (GRID_M/1000)**2:,.1f} km2")

# ---- 2. 店舗を平面（メートル）へ投影してバケット化 ----
con.execute(f"""create table st as
  select cat, lng*111320*0.99255 x, lat*111320 y from {M}""")
con.execute("""create table gp as
  select id, lng*111320*0.99255 x, lat*111320 y from grid""")

h("① カテゴリ入れ子でのカバレッジ（面積ベース）")
rows = []
for thr in THRESHOLDS:
    print(f"\n  --- 閾値 {thr}m ---")
    print(f"  {'店舗集合':32s} {'圏内セル':>9s} {'カバー率':>8s} {'限界寄与':>9s}")
    prev = None
    for label, cats in NESTED:
        # 空間バケットで候補を絞ってから実距離（等距円筒近似）
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
        d = f"{delta:>+9,}" if delta is not None else f"{'—':>9s}"
        print(f"  {label:32s} {n_in:>9,} {rate*100:>7.1f}% {d}")
        rows.append((thr, label, n_in, ncell, round(rate, 4),
                     delta if delta is not None else 0))
        prev = n_in

h("② 単独店率 — その店が消えたら圏外になる地点を作っている店の割合")
print("  （日本版の『欠落の影響 = 不足数 × 単独店率』の単独店率にあたる）")
print(f"  {'カテゴリ':18s} {'店舗数':>7s} {'500m以内に他店なし':>18s}")
for cat in ["pasar", "supermarket", "fresh_food", "minimarket", "toko_kelontong"]:
    r = con.execute(f"""
      with a as (select * from st where cat='{cat}'),
           b as (select * from st)
      select count(*) from a where not exists (
        select 1 from b where (b.x,b.y) != (a.x,a.y)
          and sqrt(power(a.x-b.x,2)+power(a.y-b.y,2)) <= 500)""").fetchone()
    tot, = con.execute(f"select count(*) from st where cat='{cat}'").fetchone()
    print(f"  {cat:18s} {tot:>7,} {r[0]:>13,} ({r[0]/tot*100:.1f}%)")

h("③ 現在の圏外セルはどこか（南部丘陵か、市街地の穴か）")
# 全カテゴリ 500m で圏外のセルの緯度分布。Semarang は北が海岸市街、南が丘陵。
con.execute(f"""create table outside as
  select g.* from gp g where not exists (
    select 1 from st s
    where floor(s.x/500)::bigint between floor(g.x/500)::bigint - 1
                                     and floor(g.x/500)::bigint + 1
      and floor(s.y/500)::bigint between floor(g.y/500)::bigint - 1
                                     and floor(g.y/500)::bigint + 1
      and sqrt(power(g.x-s.x,2)+power(g.y-s.y,2)) <= 500)""")
n_out, = con.execute("select count(*) from outside").fetchone()
print(f"  全カテゴリ 500m で圏外のセル {n_out:,} / {ncell:,} = {n_out/ncell*100:.1f}%")
print("\n  緯度帯別（北=海岸市街 → 南=丘陵）:")
# `out` は DuckDB の予約語なので別名に使えない（Parser Error になる）
for r in con.execute(f"""
    select round(lat, 2) band, count(*) tot,
           count(*) filter (where id in (select id from outside)) n_out
    from grid group by 1 order by band desc""").fetchall():
    bar = "#" * int(r[2] / max(r[1], 1) * 40)
    print(f"    lat {r[0]:>7.2f}  圏外 {r[2]:>4,}/{r[1]:<4,} ({r[2]/r[1]*100:>5.1f}%) {bar}")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(閾値m int, 店舗集合 varchar, 圏内セル bigint, "
            "総セル bigint, カバー率 double, 限界寄与セル bigint)")
con.executemany("insert into res values (?,?,?,?,?,?)", rows)
con.execute(f"copy res to '{OUT}' (header, delimiter ',')")
print(f"\n出力: {OUT}")
