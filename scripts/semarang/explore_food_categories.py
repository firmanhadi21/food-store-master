#!/usr/bin/env python3
"""
Semarang の Overture 抽出から「食料品小売になりうる」カテゴリを洗い出し、
ブランド構成・件数を実数感覚と突き合わせるための探索スクリプト。

日本版で最初にやった「コンビニは Overture 単独で実数の 97.6%」に相当する
一次チェックを Semarang で行うのが目的。
"""
import duckdb

SRC = "read_parquet('data/semarang/overture_semarang_all.parquet')"

# 食料品小売になりうる Overture カテゴリの候補（広めに取る）
CANDIDATES = [
    'convenience_store', 'supermarket', 'grocery_store', 'market', 'farmers_market',
    'public_market', 'wholesale_store', 'discount_store', 'department_store',
    'butcher_shop', 'seafood_market', 'fruit_and_vegetable_store', 'greengrocer',
    'bakery', 'food', 'shopping', 'pharmacy', 'drugstore', 'health_food_store',
    'specialty_grocery_store', 'liquor_store', 'delicatessen', 'food_and_beverage_retail',
]

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("① 候補カテゴリの実在件数（primary）")
lst = "','".join(CANDIDATES)
rows = con.execute(f"""
  select category, count(*) c from {SRC}
  where category in ('{lst}') group by 1 order by c desc""").fetchall()
for cat, c in rows:
    print(f"  {cat:32s} {c:>6,}")
found = {r[0] for r in rows}
print("\n  （bbox 内に 0 件だったカテゴリ）:", ", ".join(sorted(set(CANDIDATES) - found)) or "なし")

h("② 'market' や 'pasar' を含む category 名を総当たりで探す")
for row in con.execute(f"""
  select category, count(*) c from {SRC}
  where category ilike '%market%' or category ilike '%grocer%'
     or category ilike '%store%' or category ilike '%shop%'
  group by 1 order by c desc limit 30""").fetchall():
    print(f"  {str(row[0]):40s} {row[1]:>6,}")

h("③ convenience_store のブランド構成（Alfamart / Indomaret が取れているか）")
for row in con.execute(f"""
  select coalesce(brand_name, '(brand なし)') b, count(*) c from {SRC}
  where category = 'convenience_store' group by 1 order by c desc limit 20""").fetchall():
    print(f"  {str(row[0]):32s} {row[1]:>6,}")

h("④ 名称に Alfamart/Indomaret を含むものを category 横断で数える")
for kw in ['alfamart', 'indomaret', 'alfamidi', 'superindo', 'hypermart',
           'transmart', 'giant', 'carrefour', 'pasar', 'toko', 'warung', 'apotek']:
    rows = con.execute(f"""
      select category, count(*) c from {SRC}
      where name ilike '%{kw}%' group by 1 order by c desc limit 4""").fetchall()
    total = sum(r[1] for r in rows)
    detail = " / ".join(f"{r[0]}:{r[1]}" for r in rows)
    print(f"  {kw:12s} 計 {total:>6,}   {detail}")

h("⑤ 原典データセット構成比（日本は meta 39.8% / Foursquare 26.9% / ATP 25.7%）")
for row in con.execute(f"""
  select ds, count(*) c from (select unnest(datasets) ds from {SRC})
  where ds != 'Overture' group by 1 order by c desc""").fetchall():
    print(f"  {str(row[0]):24s} {row[1]:>7,}")

h("⑥ confidence 分布（食料品候補カテゴリのみ）")
for row in con.execute(f"""
  select category,
         count(*) c,
         round(median(confidence),3) med,
         count(*) filter (where confidence < 0.5) lo
  from {SRC} where category in ('{lst}') group by 1 order by c desc""").fetchall():
    print(f"  {str(row[0]):32s} n={row[1]:>6,}  median conf={row[2]}  conf<0.5: {row[3]:,}")
