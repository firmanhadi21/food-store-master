#!/usr/bin/env python3
"""
「どのチェーン店データを信用してよいか」に答える。

状況
----
  マスター(Overture∪OSM)  Alfamart 182 / Indomaret 216 … 網羅率 約5割・空間的に偏り
  Google Places           Alfamart 330 / Indomaret 454 … 重複と非店舗を含む
  公式ロケーター                                        … 401/403 で取得不可

どれも単独では真値でない。しかし**2つの独立なソースがあれば真値を推定できる**
（Lincoln-Petersen の捕獲再捕獲推定）。warung 現地調査で recall を測るのに使う手法と同じ。

    N ≈ (n1 × n2) / m      n1,n2 = 各ソースの件数, m = 両方に現れた数

前提と、それが崩れる方向
------------------------
  1. 独立性: マスターは Overture(meta 98%)+OSM、Google は自社収集。**概ね独立**。
  2. 等捕獲性: 「どちらのソースからも漏れやすい店」が存在すると **N は過小推定**になる。
     → 出てくる数字は**下限**として読む。
  3. 閉集合・誤検出なし: 下でクリーニングして担保する。

クリーニング（Google 側）
  - 同一チェーン 50m 以内の重複を1件に畳む
  - ATM・法人格など非店舗を名称で除外
  - ※ places.businessStatus を field mask に入れ忘れたため**閉店店舗は除外できていない**。
    再取得すればさらに精度が上がる（約$8）。

出力: docs/semarang/検証_チェーン真値推定.csv
      data/semarang/chains_best_available.parquet   （現時点で最良の統合レイヤ）
"""
import os

import duckdb

D = "data/semarang"
G = f"read_parquet('{D}/google_chains_semarang.parquet')"
M = f"read_parquet('{D}/semarang_food_master.parquet')"
OUT_CSV = "docs/semarang/検証_チェーン真値推定.csv"
OUT_LAYER = f"{D}/chains_best_available.parquet"

CHAINS = ["Alfamart", "Indomaret"]
DEDUP_M = 50    # Google 内部の重複判定
MATCH_M = 100   # ソース間の同一店舗判定

# 非店舗（ATM・法人格・卸拠点など）。名称で除外する。
NON_STORE = ["atm", " pt ", "pt.", "sumber alfaria trijaya", "indomarco",
             "kantor", "gudang", "warehouse", "distribution", "head office"]

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


# ---- 1. Google 側クリーニング ----
non_store = " or ".join(f"lower(name) like '%{w}%'" for w in NON_STORE)
con.execute(f"""create table g_raw as select * from {G}""")
con.execute(f"""create table g_ns as
  select * from g_raw where not coalesce({non_store}, false)""")
# 50m 以内の同チェーン重複はクラスタ先頭のみ残す
con.execute("""create table g_seq as
  select *, row_number() over (partition by chain order by place_id) seq from g_ns""")
con.execute(f"""create table g as
  select * exclude (seq) from g_seq a
  where not exists (
    select 1 from g_seq b where b.chain = a.chain and b.seq < a.seq
      and 111320*sqrt(power(a.lat-b.lat,2)
        + power((a.lon-b.lon)*cos(radians(a.lat)),2)) <= {DEDUP_M})""")

h("① Google 側クリーニング")
print(f"  {'チェーン':12s} {'生':>6s} {'非店舗除外':>10s} {'重複除外':>9s}")
for c in CHAINS:
    a, = con.execute(f"select count(*) from g_raw where chain='{c}'").fetchone()
    b, = con.execute(f"select count(*) from g_ns  where chain='{c}'").fetchone()
    d, = con.execute(f"select count(*) from g     where chain='{c}'").fetchone()
    print(f"  {c:12s} {a:>6,} {b:>10,} {d:>9,}")
print("  ※ businessStatus 未取得のため閉店店舗は残っている（さらに減るはず）")

# ---- 2. 捕獲再捕獲推定 ----
con.execute(f"""create table m as
  select name, lat, lng as lon,
    case when name ilike '%alfamart%' then 'Alfamart'
         when name ilike '%indomaret%' then 'Indomaret' end as chain
  from {M} where cat='minimarket'
    and (name ilike '%alfamart%' or name ilike '%indomaret%')""")

h("② Lincoln-Petersen による真値推定")
rows = []
print(f"  {'チェーン':11s} {'マスター':>8s} {'Google':>7s} {'一致':>5s} "
      f"{'推定真値':>9s} {'マスター網羅':>11s} {'Google網羅':>10s}")
for c in CHAINS:
    n1, = con.execute(f"select count(*) from m where chain='{c}'").fetchone()
    n2, = con.execute(f"select count(*) from g where chain='{c}'").fetchone()
    mm, = con.execute(f"""
      select count(*) from m where chain='{c}' and exists (
        select 1 from g where g.chain='{c}'
          and 111320*sqrt(power(m.lat-g.lat,2)
            + power((m.lon-g.lon)*cos(radians(m.lat)),2)) <= {MATCH_M})""").fetchone()
    if mm == 0:
        continue
    # Chapman 補正版（小標本でのバイアスを減らす標準形）
    n_hat = ((n1 + 1) * (n2 + 1) / (mm + 1)) - 1
    print(f"  {c:11s} {n1:>8,} {n2:>7,} {mm:>5,} {n_hat:>9,.0f} "
          f"{n1/n_hat*100:>10.1f}% {n2/n_hat*100:>9.1f}%")
    rows.append((c, n1, n2, mm, round(n_hat), round(n1/n_hat, 3), round(n2/n_hat, 3)))

print("\n  ※ 推定値の誤差は**両方向**にあるので「下限」と言い切ってはいけない:")
print("     - 等捕獲性の破れ（両ソースが同じ店を揃って落とす）→ N を**過小**にする")
print("     - Google に閉店店舗が残っている（businessStatus 未取得）→ n2 が膨らみ N を**過大**に")
print("     どちらが勝つかは businessStatus を取得するまで確定しない。")
print("     参考: 推定 Indomaret 522 は Kota Semarang 人口 165万に対し 1店/3,160人。")
print("     全国平均（21,900店 / 2.82億 ＝ 1店/12,900人）の約4倍。ジャワの県都としては")
print("     あり得る密度だが、閉店の混入で上振れしている可能性も残る。")

# ---- 3. 現時点で最良の統合レイヤ ----
# Google を主（網羅が広い）、マスター独自分を足す。
con.execute(f"""create table best as
  select chain, name, lat, lon, 'google' as src from g
  union all
  select chain, name, lat, lon, 'master' as src from m
  where not exists (
    select 1 from g where g.chain = m.chain
      and 111320*sqrt(power(m.lat-g.lat,2)
        + power((m.lon-g.lon)*cos(radians(m.lat)),2)) <= {MATCH_M})""")
con.execute(f"copy best to '{OUT_LAYER}' (FORMAT parquet)")

h("③ 現時点で最良の統合レイヤ（Google ∪ マスター独自分）")
print(f"  {'チェーン':12s} {'統合':>6s} {'google':>7s} {'master独自':>10s} {'推定真値比':>11s}")
for c, n1, n2, mm, n_hat, _, _ in rows:
    tot, = con.execute(f"select count(*) from best where chain='{c}'").fetchone()
    gg, = con.execute(f"select count(*) from best where chain='{c}' and src='google'").fetchone()
    print(f"  {c:12s} {tot:>6,} {gg:>7,} {tot-gg:>10,} {tot/n_hat*100:>10.1f}%")
print(f"\n  出力: {OUT_LAYER}")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(chain varchar, master_n bigint, google_n bigint, "
            "matched bigint, est_true bigint, master_coverage double, "
            "google_coverage double)")
con.executemany("insert into res values (?,?,?,?,?,?,?)", rows)
con.execute(f"copy res to '{OUT_CSV}' (header, delimiter ',')")
print(f"  出力: {OUT_CSV}")
