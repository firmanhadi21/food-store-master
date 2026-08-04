#!/usr/bin/env python3
"""
PP 28/2024 の学校周辺規制を、**既存データだけで**先行評価する。

PP 28/2024（UU 17/2023 施行令）の該当条項:
  - 販売禁止 **200m**: satuan pendidikan の周囲
    （条文は "tempat bermain anak" も併記するが、これは一般の児童公園ではなく
     **kelompok bermain＝PAUD の一形態**を指す。TK/PAUD に含まれるので別レイヤは不要）
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

学校レイヤについて
------------------
`build_schools_combined.py` の出力（OSM ∪ Dukcapil）を使う。ただし **Dukcapil は
Semarang で SD/SMP を1件も持たない**（全国では持つが地域的に不均一。'Senior High School'
に至ってはタグ自体が全国に存在しない）ため、**集合 A（SD/SMP/SMA）は実質 OSM 単独**。
Dukcapil の寄与は TK/PAUD（+480 校）に限られ、集合 C にのみ効く。
→ **A の網羅性は未検証のまま**であることを結果の解釈時に忘れないこと。

入力: data/semarang/semarang_food_master.parquet
      data/semarang/schools_semarang_combined.parquet
出力: docs/semarang/verify_tobacco-school-buffers.csv
"""
import os

import duckdb

D = "data/semarang"
# ★ 店舗レイヤは best-available を優先する（build_outlets_best_available.py の出力）。
#   マスターのチェーン網羅率は 42%、しかも kecamatan 別 0.19〜0.79 と**空間的に偏る**ため、
#   曝露研究の入力としては絶対数だけでなく割合まで壊れる。best 層は網羅 ~85%。
_BEST = f"{D}/semarang_outlets_best.parquet"
_MASTER = f"{D}/semarang_food_master.parquet"
_SRC = _BEST if os.path.exists(_BEST) else _MASTER
M = f"read_parquet('{_SRC}')"
S = f"read_parquet('{D}/schools_semarang_combined.parquet')"
OUT = "docs/semarang/verify_tobacco-school-buffers.csv"

# PP 28/2024 の2つの半径
R_SALES = 200
R_ADS = 500

# ★ 2026-08-04、条文で確定した。感度分析ではなく**法定の集合が決まった**。
#
#   Pasal 434(1)(e):
#     「dalam radius 200 (dua ratus) meter dari satuan pendidikan dan tempat bermain anak」
#   Penjelasan Pasal 518 Ayat (1)（p.570）＝ PP 全体で唯一の satuan pendidikan の定義:
#     「Satuan pendidikan antara lain pendidikan anak usia dini, sekolah/madrasah,
#       pesantren, perguruan tinggi, atau nama lain yang sejenis dengan pendidikan formal.」
#
#   → **PAUD/TK を含む**。madrasah・pesantren・perguruan tinggi も含む。
#     条文が並記する "tempat bermain anak" は一般の児童公園ではなく
#     **kelompok bermain（KB）＝PAUD の一形態**を指すので、TK/PAUD に含まれている。
#     当初「集合A（SD/SMP/SMA）」を主指標にしていたのは**法的に過小**だった。
#     informal（learning center 等）は「pendidikan formal と同種」と言えないので除く。
LEGAL = "level in ('TK','SD','SMP','SMA','SLB','PT')"
SCHOOL_SETS = [
    ("★法定 satuan pendidikan", LEGAL),
    ("（参考）SD/SMP/SMA のみ", "level in ('SD','SMP','SMA')"),
    ("（参考）SMP/SMA のみ",    "level in ('SMP','SMA')"),
]

# タバコを販売する蓋然性が高い業態。minimarket は確実、toko_kelontong も通常販売する。
TOBACCO_CATS = ["minimarket", "toko_kelontong"]

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


# 等距円筒近似（この環境の DuckDB は spheroid 系が nan を返す）。緯度 -7 度。
con.execute(f"""create table st as
  select cat, name, src,
         lon*111320*0.99255 x, lat*111320 y, lat, lon
  from {M}""")
con.execute(f"""create table sc as
  select school_id as osm_id, name, level,
         lon*111320*0.99255 x, lat*111320 y, lat, lon
  from {S}""")

n_st, = con.execute("select count(*) from st").fetchone()
n_sc, = con.execute("select count(*) from sc").fetchone()
print(f"店舗 {n_st:,} 件 / 学校 {n_sc:,} 件")
print(f"店舗レイヤ: {os.path.basename(_SRC)}")

h("① PP 28/2024 販売禁止 200m — 圏内の店舗数（潜在的非適合の下限）")
rows = []
for label, sfilter in SCHOOL_SETS:
    n_school, = con.execute(f"select count(*) from sc where {sfilter}").fetchone()
    print(f"\n  --- 学校集合 {label}（{n_school:,} 校）---")
    print(f"  {'業態':18s} {'総数':>6s} {'200m圏内':>9s} {'割合':>7s}")
    for cat in TOBACCO_CATS:
        tot, = con.execute(f"select count(*) from st where cat='{cat}'").fetchone()
        n_in, = con.execute(f"""
          select count(distinct (t.x, t.y, t.name)) from st t join sc s
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
sfilter = LEGAL
for cat in TOBACCO_CATS:
    tot, = con.execute(f"select count(*) from st where cat='{cat}'").fetchone()
    n_in, = con.execute(f"""
      select count(distinct (t.x, t.y, t.name)) from st t join sc s
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
    where t.cat='minimarket' and s.level in ('TK','SD','SMP','SMA','SLB','PT')
    group by 1)
  select count(*), round(min(m)), round(quantile_cont(m,0.25)), round(median(m)),
         round(quantile_cont(m,0.75)), round(max(m)) from d""").fetchone()
print(f"  n={r[0]:,}  min={r[1]:.0f}m  p25={r[2]:.0f}m  median={r[3]:.0f}m  "
      f"p75={r[4]:.0f}m  max={r[5]:.0f}m")

h("⑤ 現地調査で埋まる部分の見積もり")
km, = con.execute("select count(*) from st where cat='toko_kelontong'").fetchone()
print(f"  現在の toko_kelontong は {km} 件。実態は桁違いに多い（POI に載らないため）。")
print("  → ①の toko_kelontong 行は依然**下限**。現地調査でしか埋まらない。")
print("  → minimarket は best-available 層（推定真値の ~85%）に差し替え済み。")
print("     マスター単独では網羅 42%・kecamatan 別 0.19〜0.79 の偏りがあり使えなかった。")
print("\n  ★ 差し替えで分かった重要な非対称性:")
print("     - **店舗を分母にした割合はほぼ動かない**（200m 圏内 46.7% → 47.1%）")
print("     - **学校を分母にした割合は大きく動く**（33.2% → 49.4%）")
print("     店舗と学校が同じ商業街路に共在するため、店を足しても『学校の近くにある店の")
print("     割合』は変わらないが、『近くに店がある学校の割合』は閾値越えが増えて跳ね上がる。")
print("     → 曝露研究の主指標には**学校を分母にした指標**を採ること。網羅率の影響を")
print("        受けやすく、かつ政策的にも意味がある（規制半径内の学校数）。")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(学校集合 varchar, 学校数 bigint, 業態 varchar, "
            "半径m int, 店舗総数 bigint, 圏内店舗数 bigint, 割合 double)")
con.executemany("insert into res values (?,?,?,?,?,?,?)", rows)
con.execute(f"copy res to '{OUT}' (header, delimiter ',')")
print(f"\n出力: {OUT}")
