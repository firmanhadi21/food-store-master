#!/usr/bin/env python3
"""
Find which Overture categories plausibly hold food retail in Semarang, and sanity-check the
counts against real-world expectations.

This is the Semarang equivalent of the first check the Japan project ran — "Overture alone
covers 97.6% of convenience stores against official statistics". The point is to establish,
before building anything, whether the same source strategy can work here.
"""
import duckdb

SRC = "read_parquet('data/semarang/overture_semarang_all.parquet')"

# Categories that could plausibly hold food retail. Deliberately broad.
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


h("1. How many records each candidate category actually holds (primary)")
lst = "','".join(CANDIDATES)
rows = con.execute(f"""
  select category, count(*) c from {SRC}
  where category in ('{lst}') group by 1 order by c desc""").fetchall()
for cat, c in rows:
    print(f"  {cat:32s} {c:>6,}")
found = {r[0] for r in rows}
print("\n  (absent from the bbox):", ", ".join(sorted(set(CANDIDATES) - found)) or "none")

h("2. Brute-force search for any category naming a market or store")
for row in con.execute(f"""
  select category, count(*) c from {SRC}
  where category ilike '%market%' or category ilike '%grocer%'
     or category ilike '%store%' or category ilike '%shop%'
  group by 1 order by c desc limit 30""").fetchall():
    print(f"  {str(row[0]):40s} {row[1]:>6,}")

h("3. Brands on convenience_store — are Alfamart and Indomaret being captured?")
for row in con.execute(f"""
  select coalesce(brand_name, '(no brand)') b, count(*) c from {SRC}
  where category = 'convenience_store' group by 1 order by c desc limit 20""").fetchall():
    print(f"  {str(row[0]):32s} {row[1]:>6,}")

h("4. Name keywords across all categories")
for kw in ['alfamart', 'indomaret', 'alfamidi', 'superindo', 'hypermart',
           'transmart', 'giant', 'carrefour', 'pasar', 'toko', 'warung', 'apotek']:
    rows = con.execute(f"""
      select category, count(*) c from {SRC}
      where name ilike '%{kw}%' group by 1 order by c desc limit 4""").fetchall()
    total = sum(r[1] for r in rows)
    detail = " / ".join(f"{r[0]}:{r[1]}" for r in rows)
    print(f"  {kw:12s} total {total:>6,}   {detail}")

h("5. Contributing datasets — Japan is meta 39.8% / Foursquare 26.9% / ATP 25.7%")
for row in con.execute(f"""
  select ds, count(*) c from (select unnest(datasets) ds from {SRC})
  where ds != 'Overture' group by 1 order by c desc""").fetchall():
    print(f"  {str(row[0]):24s} {row[1]:>7,}")

h("6. Confidence distribution across the candidate categories")
for row in con.execute(f"""
  select category,
         count(*) c,
         round(median(confidence),3) med,
         count(*) filter (where confidence < 0.5) lo
  from {SRC} where category in ('{lst}') group by 1 order by c desc""").fetchall():
    print(f"  {str(row[0]):32s} n={row[1]:>6,}  median conf={row[2]}  conf<0.5: {row[3]:,}")
