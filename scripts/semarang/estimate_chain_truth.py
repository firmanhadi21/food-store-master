#!/usr/bin/env python3
"""
Answer "which chain-store dataset can be trusted?" by estimating the true count.

The situation
  master (Overture union OSM)  Alfamart 182 / Indomaret 216 — ~42% coverage, spatially biased
  Google Places               Alfamart 330 / Indomaret 454 — contains duplicates and non-stores
  official store locators                                  — 401/403, unavailable

None is truth on its own. But **two independent sources are enough to estimate the
population** (Lincoln-Petersen capture-recapture) — the same technique proposed for measuring
recall in the warung field survey.

    N ~ (n1 * n2) / m        n1, n2 = count per source; m = records in both

Assumptions, and which way each failure bends the estimate
  1. Independence: the master is Overture (98% Meta) plus OSM; Google collects its own.
     **Broadly independent.**
  2. Equal catchability: if some stores are hard for *both* sources to see, N is
     **underestimated**.
  3. Closed population, no false positives: handled by the cleaning below.

Google-side cleaning
  - collapse same-chain records within 50 m
  - drop non-stores by name (ATMs, corporate entities, warehouses)
  - **`places.businessStatus` was not requested, so permanently closed stores remain.**
    Re-fetching with that field would tighten this (~US$8).

Output: docs/semarang/verify_chain-truth-estimate.csv
        data/semarang/chains_best_available.parquet  (best layer available today)
"""
import os

import duckdb

D = "data/semarang"
G = f"read_parquet('{D}/google_chains_semarang.parquet')"
M = f"read_parquet('{D}/semarang_food_master.parquet')"
OUT_CSV = "docs/semarang/verify_chain-truth-estimate.csv"
OUT_LAYER = f"{D}/chains_best_available.parquet"

CHAINS = ["Alfamart", "Indomaret"]
DEDUP_M = 50    # within-Google duplicate threshold
MATCH_M = 100   # cross-source "same store" threshold

# Non-stores (ATMs, corporate entities, wholesale depots), excluded by name.
NON_STORE = ["atm", " pt ", "pt.", "sumber alfaria trijaya", "indomarco",
             "kantor", "gudang", "warehouse", "distribution", "head office"]

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


# ---- 1. Clean the Google layer ----
non_store = " or ".join(f"lower(name) like '%{w}%'" for w in NON_STORE)
con.execute(f"""create table g_raw as select * from {G}""")
con.execute(f"""create table g_ns as
  select * from g_raw where not coalesce({non_store}, false)""")
# Keep only the first member of each same-chain cluster within 50 m
con.execute("""create table g_seq as
  select *, row_number() over (partition by chain order by place_id) seq from g_ns""")
con.execute(f"""create table g as
  select * exclude (seq) from g_seq a
  where not exists (
    select 1 from g_seq b where b.chain = a.chain and b.seq < a.seq
      and 111320*sqrt(power(a.lat-b.lat,2)
        + power((a.lon-b.lon)*cos(radians(a.lat)),2)) <= {DEDUP_M})""")

h("1. Google-side cleaning")
print(f"  {'chain':12s} {'raw':>6s} {'non-store removed':>18s} {'deduplicated':>13s}")
for c in CHAINS:
    a, = con.execute(f"select count(*) from g_raw where chain='{c}'").fetchone()
    b, = con.execute(f"select count(*) from g_ns  where chain='{c}'").fetchone()
    d, = con.execute(f"select count(*) from g     where chain='{c}'").fetchone()
    print(f"  {c:12s} {a:>6,} {b:>18,} {d:>13,}")
print("  Note: businessStatus was not fetched, so closed stores remain and these")
print("  counts are still slightly inflated.")

# ---- 2. Capture-recapture ----
con.execute(f"""create table m as
  select name, lat, lng as lon,
    case when name ilike '%alfamart%' then 'Alfamart'
         when name ilike '%indomaret%' then 'Indomaret' end as chain
  from {M} where cat='minimarket'
    and (name ilike '%alfamart%' or name ilike '%indomaret%')""")

h("2. Population estimate (Chapman-corrected Lincoln-Petersen)")
rows = []
print(f"  {'chain':11s} {'master':>8s} {'google':>7s} {'both':>5s} "
      f"{'est. true':>10s} {'master cov':>11s} {'google cov':>11s}")
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
    # Chapman correction — the standard small-sample form, less biased than the plain ratio
    n_hat = ((n1 + 1) * (n2 + 1) / (mm + 1)) - 1
    print(f"  {c:11s} {n1:>8,} {n2:>7,} {mm:>5,} {n_hat:>10,.0f} "
          f"{n1/n_hat*100:>10.1f}% {n2/n_hat*100:>10.1f}%")
    rows.append((c, n1, n2, mm, round(n_hat), round(n1/n_hat, 3), round(n2/n_hat, 3)))

print("\n  ** Do not call these a lower bound — the error runs both ways:")
print("     - unequal catchability (both sources missing the same stores) pushes N down")
print("     - closed stores left in Google inflate n2, pushing N up")
print("     Which dominates is unknown until businessStatus is fetched.")
print("     For scale: an estimated 522 Indomaret is 1 per 3,160 residents of Semarang,")
print("     roughly 4x the national rate (21,900 stores / 282 million). Plausible for a")
print("     dense Javanese provincial capital, but also consistent with some closed-store")
print("     contamination.")

# ---- 3. Best layer available today ----
# Google leads (wider coverage); master-only records are appended.
con.execute(f"""create table best as
  select chain, name, lat, lon, 'google' as src from g
  union all
  select chain, name, lat, lon, 'master' as src from m
  where not exists (
    select 1 from g where g.chain = m.chain
      and 111320*sqrt(power(m.lat-g.lat,2)
        + power((m.lon-g.lon)*cos(radians(m.lat)),2)) <= {MATCH_M})""")
con.execute(f"copy best to '{OUT_LAYER}' (FORMAT parquet)")

h("3. Best available layer (Google union master-only records)")
print(f"  {'chain':12s} {'union':>6s} {'google':>7s} {'master-only':>12s} {'vs estimate':>12s}")
for c, n1, n2, mm, n_hat, _, _ in rows:
    tot, = con.execute(f"select count(*) from best where chain='{c}'").fetchone()
    gg, = con.execute(f"select count(*) from best where chain='{c}' and src='google'").fetchone()
    print(f"  {c:12s} {tot:>6,} {gg:>7,} {tot-gg:>12,} {tot/n_hat*100:>11.1f}%")
print(f"\n  wrote: {OUT_LAYER}")
print("  The master contributes stores Google lacks, so it cannot simply be discarded.")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(chain varchar, master_n bigint, google_n bigint, "
            "matched bigint, est_true bigint, master_coverage double, "
            "google_coverage double)")
con.executemany("insert into res values (?,?,?,?,?,?,?)", rows)
con.execute(f"copy res to '{OUT_CSV}' (header, delimiter ',')")
print(f"  wrote: {OUT_CSV}")
