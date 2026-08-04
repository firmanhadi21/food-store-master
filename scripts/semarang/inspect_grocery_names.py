#!/usr/bin/env python3
"""
Read the actual contents of Overture's grocery_store and shopping categories, so the
Indonesian cleaning rules are derived from data rather than guessed.

The Japan version found grocery_store to be a mix of three things: neighbourhood shops,
misfiled supermarket chains, and cafe/homeware noise. Indonesia should have far more
warung makan (prepared food) noise, so rather than assume a keyword list, look first.

What this script established, and which drove semarang_food_rules.py
  - grocery_store is comparatively clean: toko 43, sembako 20, grosir 7 against only a
    handful of eatery words.
  - `shopping` (851 records) is a junk bucket — opticians, garment workshops, laundries,
    steel suppliers — but real food retail is buried in it: Ada Swalayan (a local
    supermarket chain), Harmony Mart, Java Frozen Food, Grosir Pasar Bulu. It therefore
    needs a **positive** rescue filter, not a negative noise filter.
  - convenience_store is dirtier than expected: The Backyard Cafe, Victory Cell (phones),
    Art'Classico Vespa, a computer repair shop.

=> Food retail is smeared across convenience_store / grocery_store / shopping with heavy
   non-food contamination in each, because Overture's categories here are ~98% Meta-derived
   (self-declared Facebook page categories). Hence name-first classification.
"""
import duckdb

D = "data/semarang"
con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute(f"create table kota as select geom::GEOMETRY geom "
            f"from ST_Read('{D}/semarang_boundary_poly.geojson')")
con.execute(f"""create table ov as
  select name, category, category_alt, confidence, brand_name
  from read_parquet('{D}/overture_semarang_all.parquet')
  where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("1. grocery_store names, 60 samples by confidence")
for r in con.execute("""select name, round(confidence,2) from ov
    where category='grocery_store' and name is not null
    order by confidence desc limit 60""").fetchall():
    print(f"  {r[1]}  {r[0]}")

h("2. Leading word frequency in grocery_store names (to find the vocabulary)")
for r in con.execute("""
    select lower(split_part(trim(name), ' ', 1)) w, count(*) c from ov
    where category='grocery_store' and name is not null
    group by 1 having count(*) >= 2 order by c desc limit 30""").fetchall():
    print(f"  {str(r[0]):20s} {r[1]:>4,}")

h("3. How much prepared-food noise is mixed into grocery_store")
NOISE = ['warung', 'warteg', 'rumah makan', 'resto', 'cafe', 'kopi', 'kedai',
         'bakso', 'soto', 'sate', 'nasi', 'ayam', 'mie', 'mi ', 'es ', 'jus',
         'catering', 'depot', 'seafood', 'steak', 'pizza', 'roti', 'kue',
         'martabak', 'gorengan', 'juice', 'boba', 'dimsum']
for kw in NOISE:
    c, = con.execute(
        f"select count(*) from ov where category='grocery_store' and name ilike '%{kw}%'"
    ).fetchone()
    if c:
        print(f"  {kw:14s} {c:>4,}")

h("4. Non-food noise")
NONFOOD = ['konter', 'counter', 'pulsa', 'servis', 'service', 'bengkel', 'salon',
           'laundry', 'butik', 'fashion', 'aksesoris', 'optik', 'apotek', 'klinik',
           'bangunan', 'material', 'elektronik', 'komputer', 'hp ', 'motor']
for kw in NONFOOD:
    c, = con.execute(
        f"select count(*) from ov where category='grocery_store' and name ilike '%{kw}%'"
    ).fetchone()
    if c:
        print(f"  {kw:14s} {c:>4,}")

h("5. Words indicating genuine food retail (what to keep)")
KEEP = ['toko', 'sembako', 'kelontong', 'minimarket', 'swalayan', 'mart', 'pasar',
        'agen', 'grosir', 'jaya', 'berkah', 'barokah', 'makmur', 'sumber', 'buah',
        'sayur', 'daging', 'ikan', 'beras', 'telur']
for kw in KEEP:
    c, = con.execute(
        f"select count(*) from ov where category='grocery_store' and name ilike '%{kw}%'"
    ).fetchone()
    if c:
        print(f"  {kw:14s} {c:>4,}")

h("6. Inside category='shopping' — the largest unclassified pool")
for r in con.execute("""select name, round(confidence,2) from ov
    where category='shopping' and name is not null
    order by confidence desc limit 30""").fetchall():
    print(f"  {r[1]}  {r[0]}")

h("7. convenience_store records that are not Alfamart/Indomaret — what are they?")
for r in con.execute("""select name, round(confidence,2) from ov
    where category='convenience_store' and name is not null
      and name not ilike '%alfamart%' and name not ilike '%indomaret%'
      and name not ilike '%alfamidi%'
    order by confidence desc limit 30""").fetchall():
    print(f"  {r[1]}  {r[0]}")
