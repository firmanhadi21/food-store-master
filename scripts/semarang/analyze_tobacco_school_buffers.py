#!/usr/bin/env python3
"""
PP 28/2024 の学校周辺規制を、**既存データだけで**先行評価する。

PP 28/2024（UU 17/2023 施行令）の該当条項:
  - 販売禁止 **200m**: satuan pendidikan（教育施設）および児童遊技場の周囲
  - 広告禁止 **500m**: 教育施設の周囲
  - 併せて rokok ketengan（ばら売り）禁止、購入年齢 18→21 歳

現時点で測れること・測れないこと
--------------------------------
測れる: minimarket（Alfamart/Indomaret 等）は確実にタバコを販売するので、
        「200m 圏内の minimarket 数」＝**販売規制の潜在的非適合の下限**が出せる。
測れない: warung / toko kelontong は現状マスターに 186 件しか無く（実態は桁違いに多い）、
        しかもタバコ販売の有無は POI 属性に無い。**ここが現地調査で埋める部分**。

したがって本スクリプトの出力は「現地調査でどれだけ数字が増えるか」の下限であり、
調査の必要性そのものを定量化する材料になる。

入力: data/semarang/semarang_food_master.parquet
      data/semarang/osm_schools_semarang.parquet
出力: docs/semarang/検証_学校周辺タバコ販売_バッファ.csv
"""
import os

import duckdb

D = "data/semarang"
M = f"read_parquet('{D}/semarang_food_master.parquet')"
S = f"read_parquet('{D}/osm_schools_semarang.parquet')"
OUT = "docs/semarang/検証_学校周辺タバコ販売_バッファ.csv"

# PP 28/2024 の2つの半径
R_SALES = 200
R_ADS = 500

# 学校集合の定義を変えて感度を見る。「satuan pendidikan」に TK/PAUD が含まれるかは
# 条文解釈が分かれうるため、含む場合と含まない場合の両方を出す。
SCHOOL_SETS = [
    ("A 小中高のみ(SD/SMP/SMA)", "level in ('SD','SMP','SMA')"),
    ("B 中高のみ(SMP/SMA)",      "level in ('SMP','SMA')"),
    ("C 幼稚園含む全校種",        "1=1"),
]

# タバコを販売する蓋然性が高い業態。minimarket は確実、toko_kelontong も通常販売する。
TOBACCO_CATS = ["minimarket", "toko_kelontong"]

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


# 等距円筒近似（この環境の DuckDB は spheroid 系が nan を返す）。緯度 -7 度。
con.execute(f"""create table st as
  select store_id, cat, name, src,
         lng*111320*0.99255 x, lat*111320 y, lat, lng
  from {M}""")
con.execute(f"""create table sc as
  select osm_id, name, level,
         lon*111320*0.99255 x, lat*111320 y, lat, lon
  from {S}""")

n_st, = con.execute("select count(*) from st").fetchone()
n_sc, = con.execute("select count(*) from sc").fetchone()
print(f"店舗 {n_st:,} 件 / 学校 {n_sc:,} 件")

h("① PP 28/2024 販売禁止 200m — 圏内の店舗数（潜在的非適合の下限）")
rows = []
for label, sfilter in SCHOOL_SETS:
    n_school, = con.execute(f"select count(*) from sc where {sfilter}").fetchone()
    print(f"\n  --- 学校集合 {label}（{n_school:,} 校）---")
    print(f"  {'業態':18s} {'総数':>6s} {'200m圏内':>9s} {'割合':>7s}")
    for cat in TOBACCO_CATS:
        tot, = con.execute(f"select count(*) from st where cat='{cat}'").fetchone()
        n_in, = con.execute(f"""
          select count(distinct t.store_id) from st t join sc s
            on floor(s.x/{R_SALES})::bigint between floor(t.x/{R_SALES})::bigint - 1
                                                and floor(t.x/{R_SALES})::bigint + 1
           and floor(s.y/{R_SALES})::bigint between floor(t.y/{R_SALES})::bigint - 1
                                                and floor(t.y/{R_SALES})::bigint + 1
          where t.cat='{cat}' and {sfilter.replace('level', 's.level')}
            and sqrt(power(t.x-s.x,2)+power(t.y-s.y,2)) <= {R_SALES}""").fetchone()
        print(f"  {cat:18s} {tot:>6,} {n_in:>9,} {n_in/tot*100:>6.1f}%")
        rows.append((label, n_school, cat, R_SALES, tot, n_in, round(n_in/tot, 4)))

h("② 広告禁止 500m — 圏内の店舗数")
print("  （現地調査では banner の実数を数えるので、これは『対象になりうる店舗』の母数）")
print(f"  {'業態':18s} {'総数':>6s} {'500m圏内':>9s} {'割合':>7s}")
sfilter = "level in ('SD','SMP','SMA')"
for cat in TOBACCO_CATS:
    tot, = con.execute(f"select count(*) from st where cat='{cat}'").fetchone()
    n_in, = con.execute(f"""
      select count(distinct t.store_id) from st t join sc s
        on floor(s.x/{R_ADS})::bigint between floor(t.x/{R_ADS})::bigint - 1
                                          and floor(t.x/{R_ADS})::bigint + 1
       and floor(s.y/{R_ADS})::bigint between floor(t.y/{R_ADS})::bigint - 1
                                          and floor(t.y/{R_ADS})::bigint + 1
      where t.cat='{cat}' and {sfilter.replace('level', 's.level')}
        and sqrt(power(t.x-s.x,2)+power(t.y-s.y,2)) <= {R_ADS}""").fetchone()
    print(f"  {cat:18s} {tot:>6,} {n_in:>9,} {n_in/tot*100:>6.1f}%")
    rows.append(("A 小中高のみ(SD/SMP/SMA)", 0, cat, R_ADS, tot, n_in, round(n_in/tot, 4)))

h("③ 学校側から見る — 200m 圏内に minimarket がある学校の割合")
for label, sfilter in SCHOOL_SETS:
    tot, = con.execute(f"select count(*) from sc where {sfilter}").fetchone()
    n_in, = con.execute(f"""
      select count(distinct s.osm_id) from sc s join st t
        on floor(t.x/{R_SALES})::bigint between floor(s.x/{R_SALES})::bigint - 1
                                            and floor(s.x/{R_SALES})::bigint + 1
       and floor(t.y/{R_SALES})::bigint between floor(s.y/{R_SALES})::bigint - 1
                                            and floor(s.y/{R_SALES})::bigint + 1
      where t.cat='minimarket' and {sfilter.replace('level', 's.level')}
        and sqrt(power(t.x-s.x,2)+power(t.y-s.y,2)) <= {R_SALES}""").fetchone()
    print(f"  {label:26s} {n_in:>5,} / {tot:<6,} = {n_in/tot*100:5.1f}%")

h("④ 最近隣 minimarket までの距離分布（学校別・SD/SMP/SMA）")
r = con.execute(f"""
  with d as (
    select s.osm_id, min(sqrt(power(t.x-s.x,2)+power(t.y-s.y,2))) m
    from sc s join st t
      on floor(t.x/1000)::bigint between floor(s.x/1000)::bigint - 1
                                     and floor(s.x/1000)::bigint + 1
     and floor(t.y/1000)::bigint between floor(s.y/1000)::bigint - 1
                                     and floor(s.y/1000)::bigint + 1
    where t.cat='minimarket' and s.level in ('SD','SMP','SMA')
    group by 1)
  select count(*), round(min(m)), round(quantile_cont(m,0.25)), round(median(m)),
         round(quantile_cont(m,0.75)), round(max(m)) from d""").fetchone()
print(f"  n={r[0]:,}  min={r[1]:.0f}m  p25={r[2]:.0f}m  median={r[3]:.0f}m  "
      f"p75={r[4]:.0f}m  max={r[5]:.0f}m")

h("⑤ 現地調査で埋まる部分の見積もり")
km, = con.execute("select count(*) from st where cat='toko_kelontong'").fetchone()
print(f"  現在の toko_kelontong は {km} 件。実態は桁違いに多い（POI に載らないため）。")
print("  → ①の toko_kelontong 行は**下限**であり、現地調査後に大きく増える。")
print("  → minimarket 行はチェーン店なので POI 網羅が比較的よく、下振れは小さい。")
print("  この差そのものが『なぜ現地調査が要るか』の定量的根拠になる。")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(学校集合 varchar, 学校数 bigint, 業態 varchar, "
            "半径m int, 店舗総数 bigint, 圏内店舗数 bigint, 割合 double)")
con.executemany("insert into res values (?,?,?,?,?,?,?)", rows)
con.execute(f"copy res to '{OUT}' (header, delimiter ',')")
print(f"\n出力: {OUT}")
