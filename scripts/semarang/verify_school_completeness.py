#!/usr/bin/env python3
"""
Measure the school layer's completeness against Dapodik's **published counts**.

Why counts are enough
---------------------
Dapodik does not publish coordinates (they live in Verval SP, which is authenticated), but it
does publish counts. Completeness needs no coordinates, so the published totals serve as the
denominator. Same two-layer principle used for the stores: position from POI sources,
quantity from official statistics.

Source (referensi.data.kemendikdasmen.go.id, Kota Semarang wilayah 036300, retrieved
2026-08-04):
  dikdas /pendidikan/dikdas/030000/1  -> SD and SMP counts per kabupaten/kota
  dikmen /pendidikan/dikmen/030000/1  -> SMA, SMK, SLB
  paud   /pendidikan/paud/030000/1    -> TK, KB, TPA, SPS
  Note: the per-school listings (level 3) are JS-rendered and cannot be fetched statically,
  so the province-level summary tables are used instead.

Output: docs/semarang/verify_school-completeness-vs-dapodik.csv
"""
import os

import duckdb

D = "data/semarang"
S = f"read_parquet('{D}/schools_semarang_combined.parquet')"
OUT = "docs/semarang/verify_school-completeness-vs-dapodik.csv"

# Dapodik published counts for Kota Semarang
DAPODIK = {
    "SD":  615,          # SD sederajat, including MI
    "SMP": 244,          # SMP sederajat, including MTs
    "SMA": 108 + 87,     # SMA sederajat 108 + SMK sederajat 87 = 195
    "SLB": 12,
    "TK":  856 + 278 + 31 + 274,   # TK 856 + KB 278 + TPA 31 + SPS 274 = 1,439
}

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute(f"create table s as select * from {S}")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("1. Coverage by level (layer / Dapodik published)")
print(f"  {'level':8s} {'layer':>7s} {'Dapodik':>9s} {'coverage':>10s}")
rows = []
for lv, official in DAPODIK.items():
    n, = con.execute(f"select count(*) from s where level='{lv}'").fetchone()
    rate = n / official
    flag = ("  <- **over 100%, investigate**" if rate > 1.02
            else "  <- **large shortfall**" if rate < 0.7 else "")
    print(f"  {lv:8s} {n:>7,} {official:>9,} {rate:>9.1%}{flag}")
    rows.append((lv, n, official, round(rate, 3)))

h("2. The set used in the PP 28/2024 analysis (SD/SMP/SMA)")
a_layer, = con.execute(
    "select count(*) from s where level in ('SD','SMP','SMA')").fetchone()
a_official = DAPODIK["SD"] + DAPODIK["SMP"] + DAPODIK["SMA"]
print(f"  layer {a_layer:,} / Dapodik {a_official:,} = **{a_layer/a_official:.1%}**")
print(f"  -> roughly {a_official - a_layer:,} institutions missing")
rows.append(("A(SD+SMP+SMA)", a_layer, a_official, round(a_layer / a_official, 3)))

h("3. Diagnosing the TK excess (why the layer once exceeded Dapodik)")
# Cause: the same kindergarten appearing in both OSM and Dukcapil with coordinates more than
# 100 m apart, so it slipped past the same-level 100 m deduplication in
# build_schools_combined.py.
n_tk, = con.execute("select count(*) from s where level='TK'").fetchone()
print(f"  TK layer {n_tk:,} vs Dapodik {DAPODIK['TK']:,} ({n_tk/DAPODIK['TK']:.1%})")
print(f"\n  {'radius':>8s} {'records in a matched pair':>26s} {'implied count':>15s}")
for m in (100, 150, 200, 300, 500):
    dup, = con.execute(f"""
      select count(*) from s a where a.level='TK' and a.src='dukcapil' and exists (
        select 1 from s b where b.level='TK' and b.src='osm'
          and 111320*sqrt(power(a.lat-b.lat,2)
            + power((a.lon-b.lon)*cos(radians(a.lat)),2)) <= {m})""").fetchone()
    print(f"  {m:>7,}m {dup:>26,} {n_tk - dup:>15,}")
print("\n  Matches rising with radius means the cause is reference-point spread for the")
print("  same institution, not distinct facilities. The radius whose implied count lands")
print("  near Dapodik's is the realistic one. build_schools_combined.py now uses 150 m.")

h("4. Interpretation, and the effect on the tobacco analysis")
print(f"  Set A coverage {a_layer/a_official:.1%} is lower than the outlet layer's ~85%.")
print("  SMP is the weakest level, and it feeds the primary exposure-side measure directly.")
print("\n  The headline (share of institutions with a minimarket within 200 m) is computed")
print(f"  over {a_layer:,} institutions when {a_official:,} exist. Recomputing over the full")
print("  set would change it, but **the direction cannot be predicted in advance**:")
print("   - if the missing schools are peripheral -> fewer nearby outlets -> figure overstated")
print("   - if they are small private/madrasah inside dense kampung -> understated")
print("  Geocoding Dapodik's per-school listings (NPSN + address) would settle it.")

os.makedirs("docs/semarang", exist_ok=True)
con.execute("create table res(level varchar, layer_n bigint, dapodik_n bigint, "
            "coverage double)")
con.executemany("insert into res values (?,?,?,?)", rows)
con.execute(f"copy res to '{OUT}' (header, delimiter ',')")
print(f"\nwrote: {OUT}")
