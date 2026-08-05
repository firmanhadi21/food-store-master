#!/usr/bin/env python3
"""
Evaluate the PP 28/2024 school-radius provisions **from existing data alone**, before any
field survey.

Relevant provisions of PP 28/2024 (implementing UU 17/2023)
  - **200 m**: sale of tobacco products prohibited around satuan pendidikan.
    The article also names "tempat bermain anak", but that means *kelompok bermain* —
    a form of PAUD — rather than a public playground, so it is already inside the TK/PAUD
    layer and needs no separate source.
  - **500 m**: advertising of tobacco products prohibited around educational facilities.
  - Also: ban on rokok ketengan (single-stick sales); purchase age raised 18 -> 21.

What can and cannot be measured here
------------------------------------
Measurable: minimarkets (Alfamart/Indomaret etc.) certainly sell tobacco, so the count within
200 m is a **lower bound on potential non-compliance**.

Not measurable: warung / toko kelontong number only 186 in the master (reality is orders of
magnitude higher), and whether an outlet sells tobacco is not a POI attribute at all.
**That gap is what the field survey exists to fill.**

So the output is a floor, and the size of the floor quantifies why the survey is needed.

About the school layer
----------------------
Uses the output of build_schools_combined.py (OSM union Dukcapil). Note that **Dukcapil holds
no SD or SMP for Semarang** (it does nationally, but coverage is regionally uneven, and
'Senior High School' does not exist as a tag anywhere). Dukcapil therefore contributes only
TK/PAUD (+352 institutions). Completeness of the SD/SMP/SMA layer is measured separately in
verify_school_completeness.py — it is 76.4%.

Input:  data/semarang/semarang_outlets_best.parquet (falls back to the master)
        data/semarang/schools_semarang_combined.parquet
Output: docs/semarang/verify_tobacco-school-buffers.csv
"""
import os

import duckdb

D = "data/semarang"
# Prefer the best-available outlet layer (build_outlets_best_available.py). The master's own
# chain coverage is 42% and, worse, **spatially biased** (0.19-0.79 by kecamatan), which
# corrupts proportions and not merely counts. The best layer reaches ~85%.
_BEST = f"{D}/semarang_outlets_best.parquet"
_MASTER = f"{D}/semarang_food_master.parquet"
_SRC = _BEST if os.path.exists(_BEST) else _MASTER
M = f"read_parquet('{_SRC}')"
S = f"read_parquet('{D}/schools_semarang_combined.parquet')"
OUT = "docs/semarang/verify_tobacco-school-buffers.csv"

# The two radii in PP 28/2024
R_SALES = 200
R_ADS = 500

# Settled against the regulation text on 2026-08-04. This is no longer a sensitivity
# analysis over plausible readings — **the statutory set is known**.
#
#   Pasal 434(1)(e):
#     "dalam radius 200 (dua ratus) meter dari satuan pendidikan dan tempat bermain anak"
#   Penjelasan Pasal 518 Ayat (1), p.570 — the only definition of satuan pendidikan in the
#   entire regulation:
#     "Satuan pendidikan antara lain pendidikan anak usia dini, sekolah/madrasah,
#      pesantren, perguruan tinggi, atau nama lain yang sejenis dengan pendidikan formal."
#
#   => **PAUD/TK is included**, as are madrasah, pesantren and higher education.
#      Treating SD/SMP/SMA as the primary set (the earlier approach) was legally too narrow.
#      'informal' (learning centres) is excluded — not "sejenis dengan pendidikan formal".
LEGAL = "level in ('TK','SD','SMP','SMA','SLB','PT')"
SCHOOL_SETS = [
    ("statutory satuan pendidikan", LEGAL),
    ("(ref) SD/SMP/SMA only", "level in ('SD','SMP','SMA')"),
    ("(ref) SMP/SMA only", "level in ('SMP','SMA')"),
]

# Formats that very likely sell tobacco. Minimarkets certainly do; toko kelontong normally do.
TOBACCO_CATS = ["minimarket", "toko_kelontong"]

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


# Equirectangular approximation — ST_Distance_Spheroid returns nan in this environment.
# Latitude -7, so the longitude correction is cos(7 deg) ~ 0.993.
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
print(f"outlets {n_st:,} / educational institutions {n_sc:,}")
print(f"outlet layer: {os.path.basename(_SRC)}")

h("1. 200 m sales-prohibition radius — outlets inside (lower bound)")
rows = []
for label, sfilter in SCHOOL_SETS:
    n_school, = con.execute(f"select count(*) from sc where {sfilter}").fetchone()
    print(f"\n  --- school set: {label} ({n_school:,}) ---")
    print(f"  {'format':18s} {'total':>6s} {'within 200m':>12s} {'share':>7s}")
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
        print(f"  {cat:18s} {tot:>6,} {n_in:>12,} {n_in/tot*100:>6.1f}%")
        rows.append((label, n_school, cat, R_SALES, tot, n_in, round(n_in/tot, 4)))

h("2. 500 m advertising-prohibition radius — outlets inside")
print("  (a field survey counts actual banners; this is the population at risk)")
print(f"  {'format':18s} {'total':>6s} {'within 500m':>12s} {'share':>7s}")
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
    print(f"  {cat:18s} {tot:>6,} {n_in:>12,} {n_in/tot*100:>6.1f}%")
    rows.append(("statutory satuan pendidikan", 0, cat, R_ADS, tot, n_in,
                 round(n_in/tot, 4)))

h("3. Seen from the schools — share with a minimarket within 200 m")
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
    print(f"  {label:30s} {n_in:>5,} / {tot:<6,} = {n_in/tot*100:5.1f}%")

h("4. Distance to nearest minimarket, per institution")
r = con.execute(f"""
  with d as (
    select s.osm_id, min(sqrt(power(t.x-s.x,2)+power(t.y-s.y,2))) m
    from sc s join st t
      on floor(t.x/1000)::bigint between floor(s.x/1000)::bigint - 1
                                     and floor(s.x/1000)::bigint + 1
     and floor(t.y/1000)::bigint between floor(s.y/1000)::bigint - 1
                                     and floor(s.y/1000)::bigint + 1
    where t.cat='minimarket' and s.{LEGAL}
    group by 1)
  select count(*), round(min(m)), round(quantile_cont(m,0.25)), round(median(m)),
         round(quantile_cont(m,0.75)), round(max(m)) from d""").fetchone()
print(f"  n={r[0]:,}  min={r[1]:.0f}m  p25={r[2]:.0f}m  median={r[3]:.0f}m  "
      f"p75={r[4]:.0f}m  max={r[5]:.0f}m")
print("  Note: the bucketed search truncates very distant pairs, so this median runs a few"
      "\n  metres low. export_viewer_geojson.py computes it over the full layer (210 m).")

h("5. What the field survey would add")
km, = con.execute("select count(*) from st where cat='toko_kelontong'").fetchone()
print(f"  toko_kelontong currently {km}. Reality is orders of magnitude higher — these")
print("  outlets appear in no POI source, so only fieldwork closes the gap.")
print("  minimarket has already been swapped to the best-available layer (~85% of the")
print("  estimated true count). The master alone was 42% and spatially biased (0.19-0.79")
print("  by kecamatan), so it was unusable as an exposure input.")
print("\n  ** The asymmetry the swap revealed:")
print("     - outlet-denominated share barely moves    (within 200 m: 46.7% -> 47.1%)")
print("     - exposure-denominated share moves sharply (33.2% -> 49.4%)")
print("     Outlets and schools sit on the same commercial streets, so adding ~400 stores")
print("     hardly changes what fraction of stores happen to be near a school — but it")
print("     pushes many schools across the 200 m threshold for the first time.")
print("  => Use the **exposure-side denominator** as the primary measure. It is the one")
print("     sensitive to coverage, and the policy-relevant quantity.")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(school_set varchar, n_schools bigint, format varchar, "
            "radius_m int, outlets_total bigint, outlets_within bigint, share double)")
con.executemany("insert into res values (?,?,?,?,?,?,?)", rows)
con.execute(f"copy res to '{OUT}' (header, delimiter ',')")
print(f"\nwrote: {OUT}")
