#!/usr/bin/env python3
"""
Assemble the best outlet layer available today, to replace the master as input to the
school-buffer analysis.

Why replace it
--------------
The master's chain coverage is 42% for Alfamart and 41% for Indomaret
(estimate_chain_truth.py), and the shortfall is **spatially structured** — coverage ranges
0.19 to 0.79 across kecamatan (analyze_coverage_spatial_bias.py). Since Overture here is
98.1% Meta-derived, coverage inherits Facebook-page density, which tracks commercial
formality rather than geography.

For an exposure study that bias **corrupts proportions, not merely counts**. Swapping in the
Google-derived best layer raises coverage to ~85% and moves the layer off the mechanism
causing the bias.

Composition
-----------
  minimarket   chains_best_available.parquet (Google union master-only records)
               plus the master's non-Alfamart/Indomaret minimarkets (Alfamidi, unnamed)
  other four   unchanged from the master (supermarket / pasar / toko_kelontong / fresh_food)

  ** toko_kelontong remains a floor at 186. Only fieldwork closes that.

Output: data/semarang/semarang_outlets_best.parquet
"""
import duckdb

D = "data/semarang"
M = f"read_parquet('{D}/semarang_food_master.parquet')"
BEST = f"read_parquet('{D}/chains_best_available.parquet')"
OUT = f"{D}/semarang_outlets_best.parquet"

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 68}\n{t}\n{'=' * 68}")


# Everything from the master except Alfamart/Indomaret, which would otherwise be
# double-counted against the best chain layer.
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
h("Best available outlet layer")
old, = con.execute(f"select count(*) from {M}").fetchone()
print(f"  master {old:,} -> best {n:,}\n")
print(f"  {'category':16s} {'best':>7s} {'master':>8s} {'delta':>7s}")
for cat in ["minimarket", "toko_kelontong", "pasar", "supermarket", "fresh_food"]:
    a, = con.execute(f"select count(*) from outlets where cat='{cat}'").fetchone()
    b, = con.execute(f"select count(*) from {M} where cat='{cat}'").fetchone()
    print(f"  {cat:16s} {a:>7,} {b:>8,} {a-b:>+7,}")

print("\n  minimarket by provenance:")
for row in con.execute("""select src, count(*) c from outlets
    where cat='minimarket' group by 1 order by c desc""").fetchall():
    print(f"    {str(row[0]):16s} {row[1]:>6,}")

con.execute(f"copy outlets to '{OUT}' (FORMAT parquet)")
print(f"\nwrote: {OUT}")
print("\n  Reminder: toko_kelontong is still the 186 floor — fieldwork only.")
