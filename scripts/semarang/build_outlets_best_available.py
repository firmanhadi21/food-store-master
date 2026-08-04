#!/usr/bin/env python3
"""
現時点で最良の店舗レイヤを組む（学校バッファ分析の入力を差し替えるため）。

なぜ差し替えるか
----------------
マスターのチェーン網羅率は Alfamart 42% / Indomaret 41%（estimate_chain_truth.py）。
しかも欠落は**空間的に偏っている**（kecamatan 別 0.19〜0.79、analyze_coverage_spatial_bias.py）。
Overture が meta 由来 98.1% なので、網羅率が Facebook ページ密度を継承しているのが機構。

→ 学校バッファ分析（曝露研究）にとって、この偏りは**絶対数だけでなく割合も壊す**。
   Google 由来の best-available 層に差し替えれば網羅率 ~85% になり、
   かつ偏りの主因（Facebook 依存）から外れる。

レイヤ構成
----------
  minimarket   : chains_best_available.parquet（Google ∪ マスター独自分）
                 + マスターの Alfamart/Indomaret 以外の minimarket（Alfamidi・無名店等）
  その他4カテゴリ: マスターのまま（supermarket / pasar / toko_kelontong / fresh_food）

  ★ toko_kelontong は依然として 186 件の**下限**のまま。ここは現地調査でしか埋まらない。

出力: data/semarang/semarang_outlets_best.parquet
"""
import os

import duckdb

D = "data/semarang"
M = f"read_parquet('{D}/semarang_food_master.parquet')"
BEST = f"read_parquet('{D}/chains_best_available.parquet')"
OUT = f"{D}/semarang_outlets_best.parquet"

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 68}\n{t}\n{'=' * 68}")


# マスターのうち Alfamart/Indomaret **以外**（best 層と二重計上しないため除く）
con.execute(f"""create table m_other as
  select cat, name, src, lat, lng as lon from {M}
  where not (cat = 'minimarket'
             and (name ilike '%alfamart%' or name ilike '%indomaret%'))""")

con.execute(f"""create table best_chain as
  select 'minimarket' as cat, name, 'best:' || src as src, lat, lon from {BEST}""")

con.execute("""create table outlets as
  select row_number() over () as outlet_id, cat, name, src, lat, lon
  from (select cat, name, src, lat, lon from best_chain
        union all
        select cat, name, src, lat, lon from m_other)""")

n, = con.execute("select count(*) from outlets").fetchone()
h("最良の店舗レイヤ")
old, = con.execute(f"select count(*) from {M}").fetchone()
print(f"  マスター {old:,} 件 → best {n:,} 件\n")
print(f"  {'カテゴリ':16s} {'best':>7s} {'master':>8s} {'差':>7s}")
for cat in ["minimarket", "toko_kelontong", "pasar", "supermarket", "fresh_food"]:
    a, = con.execute(f"select count(*) from outlets where cat='{cat}'").fetchone()
    b, = con.execute(f"select count(*) from {M} where cat='{cat}'").fetchone()
    print(f"  {cat:16s} {a:>7,} {b:>8,} {a-b:>+7,}")

print("\n  minimarket の内訳:")
for row in con.execute("""select src, count(*) c from outlets
    where cat='minimarket' group by 1 order by c desc""").fetchall():
    print(f"    {str(row[0]):16s} {row[1]:>6,}")

con.execute(f"copy outlets to '{OUT}' (FORMAT parquet)")
print(f"\n出力: {OUT}")
print("\n  ※ toko_kelontong は 186 件の下限のまま。現地調査でしか埋まらない。")
