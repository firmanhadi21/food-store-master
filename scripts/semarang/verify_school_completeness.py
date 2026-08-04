#!/usr/bin/env python3
"""
学校レイヤの網羅性を Dapodik の**公表件数**と突合する。

なぜこれで検証できるか
----------------------
Dapodik は座標を公開していない（Verval SP 側・要認証）が、**件数は公開している**。
網羅性の検証に座標は要らないので、公表件数を分母に使えば
「OSM∪Dukcapil の学校レイヤが実数の何割か」が測れる。
チェーン店を Google Places で裏取りしたのと同じ二層構成（位置＝POI、数量＝公的統計）。

出典（いずれも referensi.data.kemendikdasmen.go.id、2026-08-04 取得）
  dikdas /pendidikan/dikdas/030000/1  → 県内 kabupaten/kota 別の SD・SMP 件数
  dikmen /pendidikan/dikmen/030000/1  → 同 SMA・SMK・SLB
  paud   /pendidikan/paud/030000/1    → 同 TK・KB・TPA・SPS
  ※ 個別校の一覧（level 3）は JS 描画で静的取得できない。県レベルの集計表を使う。

出力: docs/semarang/検証_学校網羅性_Dapodik突合.csv
"""
import os

import duckdb

D = "data/semarang"
S = f"read_parquet('{D}/schools_semarang_combined.parquet')"
OUT = "docs/semarang/検証_学校網羅性_Dapodik突合.csv"

# Dapodik 公表件数（Kota Semarang, wilayah code 036300）
DAPODIK = {
    "SD":  615,          # SD sederajat（MI 等を含む）
    "SMP": 244,          # SMP sederajat（MTs 等を含む）
    "SMA": 108 + 87,     # SMA sederajat 108 + SMK sederajat 87 = 195
    "SLB": 12,
    "TK":  856 + 278 + 31 + 274,   # TK 856 + KB 278 + TPA 31 + SPS 274 = 1,439
}

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute(f"create table s as select * from {S}")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("① 段階別 網羅率（レイヤ ÷ Dapodik 公表）")
print(f"  {'level':8s} {'レイヤ':>7s} {'Dapodik':>9s} {'網羅率':>8s}")
rows = []
for lv, official in DAPODIK.items():
    n, = con.execute(f"select count(*) from s where level='{lv}'").fetchone()
    rate = n / official
    flag = "  ← **要調査（過剰）**" if rate > 1.02 else ("  ← **不足大**" if rate < 0.7 else "")
    print(f"  {lv:8s} {n:>7,} {official:>9,} {rate:>7.1%}{flag}")
    rows.append((lv, n, official, round(rate, 3)))

h("② PP 28/2024 の分析に使う集合 A（SD/SMP/SMA）")
a_layer, = con.execute(
    "select count(*) from s where level in ('SD','SMP','SMA')").fetchone()
a_official = DAPODIK["SD"] + DAPODIK["SMP"] + DAPODIK["SMA"]
print(f"  レイヤ {a_layer:,} 校 / Dapodik {a_official:,} 校 = **{a_layer/a_official:.1%}**")
print(f"  → 欠落 約 {a_official - a_layer:,} 校")
rows.append(("A(SD+SMP+SMA)", a_layer, a_official, round(a_layer / a_official, 3)))

h("③ TK の過剰を診断（レイヤ > Dapodik となった原因）")
# 想定原因: OSM と Dukcapil で同一園の座標が 100m 以上離れており、
# build_schools_combined.py の同 level・100m 重複排除をすり抜けた。
n_tk, = con.execute("select count(*) from s where level='TK'").fetchone()
print(f"  TK レイヤ {n_tk:,} vs Dapodik {DAPODIK['TK']:,}"
      f"（{n_tk/DAPODIK['TK']:.1%}）")
print(f"\n  {'突合半径':>8s} {'重複ペアにある件数':>18s} {'重複除去後の推定':>16s}")
for m in (100, 150, 200, 300, 500):
    dup, = con.execute(f"""
      select count(*) from s a where a.level='TK' and a.src='dukcapil' and exists (
        select 1 from s b where b.level='TK' and b.src='osm'
          and 111320*sqrt(power(a.lat-b.lat,2)
            + power((a.lon-b.lon)*cos(radians(a.lat)),2)) <= {m})""").fetchone()
    # 現状の統合は 100m で除去済みなので、それより広い半径の増分が「すり抜け」
    print(f"  {m:>7,}m {dup:>18,} {n_tk - dup:>16,}")
print("\n  ※ 半径を広げるほど一致が増えるなら、同一園の座標差が原因＝統合の取りこぼし。")
print("     Dapodik の 1,439 に近づく半径が実態に近い。")

h("④ 解釈と、タバコ分析への影響")
print(f"  集合A の網羅率 {a_layer/a_official:.1%} は、店舗側（best 層 ~85%）より低い。")
print("  とくに SMP が最も不足しており、学校を分母にした主指標に直接効く。")
print("\n  学校を分母にした指標（200m 以内に minimarket がある学校の割合 49.4%）は")
print(f"  {a_layer:,} 校の上で計算されている。実数 {a_official:,} 校で計算すると変わるが、")
print("  **変化の向きは事前に決められない**:")
print("   - 欠落校が周縁部に多い → 近隣店舗が少なく 49.4% は**過大**")
print("   - 欠落校が密集カンポン内の小規模私立/madrasah → 店舗も多く**過小**")
print("  → 欠落校の空間分布が分かるまで、49.4% には ±の不確実性が残る。")
print("     Dapodik の個別校一覧（NPSN＋住所）をジオコーディングすれば解決する。")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(level varchar, layer_n bigint, dapodik_n bigint, "
            "coverage double)")
con.executemany("insert into res values (?,?,?,?)", rows)
con.execute(f"copy res to '{OUT}' (header, delimiter ',')")
print(f"\n出力: {OUT}")
