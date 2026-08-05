#!/usr/bin/env python3
"""
Quality check on the Semarang master. **The main goal is to name false positives.**

Same intent as the Japan version's verify_master_quality.py, but with a different emphasis.
There the point was measuring shortfall against official statistics; here classification is
name-driven and the false-positive risk is high, so **over-counting is checked first**.

The asymmetry that makes this the right priority (from the Japan version):
  - surplus (inventing outlets that do not exist) moves residents from "outside" to
    "inside" the threshold => **understates the difficulty**
  - shortfall overstates it
In Semarang the false positives are the greater danger: loose name rules grow outlets in
places that have none.
"""
import os
import sys

import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semarang_food_rules import CATEGORIES  # noqa: E402

D = "data/semarang"
M = f"read_parquet('{D}/semarang_food_master.parquet')"

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("1. Inspect the supermarket category in full")
print("  Overture-derived supermarket names, 40 by confidence:")
for r in con.execute(f"""select name, round(confidence,2) from {M}
    where cat='supermarket' and src='overture' order by confidence desc limit 40""").fetchall():
    print(f"    {r[1]}  {r[0]}")

h("2. Which token put each record into supermarket")
for kw in ["superindo", "hypermart", "transmart", "carrefour", "giant ", "lotte",
           "ada swalayan", "gelael", "griya", "yogya", "luwes", "sri ratu",
           "matahari", "toserba", "swalayan", "supermarket", "aeon", "ranch"]:
    c, = con.execute(f"select count(*) from {M} where cat='supermarket' "
                     f"and name ilike '%{kw}%'").fetchone()
    if c:
        print(f"  {kw:16s} {c:>4,}")
none_kw, = con.execute(f"""select count(*) from {M} where cat='supermarket'
    and not (name ilike '%superindo%' or name ilike '%hypermart%' or name ilike '%transmart%'
      or name ilike '%carrefour%' or name ilike '%giant %' or name ilike '%lotte%'
      or name ilike '%ada swalayan%' or name ilike '%gelael%' or name ilike '%griya%'
      or name ilike '%yogya%' or name ilike '%luwes%' or name ilike '%sri ratu%'
      or name ilike '%matahari%' or name ilike '%toserba%' or name ilike '%swalayan%'
      or name ilike '%supermarket%' or name ilike '%aeon%' or name ilike '%ranch%')""").fetchone()
print(f"  (matches no token, i.e. from an OSM tag) {none_kw:,}")

h("3. Inspect pasar — is the name rule misfiring?")
print("  Overture-derived pasar names, 30:")
for r in con.execute(f"""select name from {M}
    where cat='pasar' and src='overture' limit 30""").fetchall():
    print(f"    {r[0]}")

h("4. Inspect toko_kelontong")
for r in con.execute(f"""select name, round(confidence,2) from {M}
    where cat='toko_kelontong' and src='overture' order by random() limit 40""").fetchall():
    print(f"    {r[1]}  {r[0]}")

h("5. Spatial duplication — another record of the same category within 50 m")
con.execute(f"create table m as select *, ST_Point(lng, lat) geom from {M}")
con.execute("create index m_ix on m using rtree(geom)")
for cat in CATEGORIES:
    r = con.execute(f"""select count(*) from m a
        where a.cat='{cat}' and exists (
          select 1 from m b where b.cat='{cat}' and b.store_id != a.store_id
            and ST_DWithin(a.geom, b.geom, 0.00045))""").fetchone()
    tot, = con.execute(f"select count(*) from m where cat='{cat}'").fetchone()
    print(f"  {cat:16s} {r[0]:>5,} / {tot:<5,} = {r[0]/tot*100:5.1f}% have a same-category"
          f" neighbour within 50 m")
print("\n  For minimarket this is expected rather than alarming — Alfamart and Indomaret")
print("  deliberately open opposite one another. check_minimarket_pairs.py separates")
print("  genuine co-location from missed deduplication.")

h("6. Same name, nearby — unambiguous duplicates")
for r in con.execute("""select a.cat, a.name, count(*) c from m a
    join m b on a.cat=b.cat and a.store_id < b.store_id
      and lower(a.name)=lower(b.name)
      and ST_DWithin(a.geom, b.geom, 0.0018)
    where a.name is not null group by 1,2 order by c desc limit 15""").fetchall():
    print(f"  {r[0]:16s} {str(r[1])[:36]:38s} {r[2]}")

h("7. Coordinate quality — clustering on identical points suggests geocoded centroids")
for r in con.execute("""select lat, lng, count(*) c from m
    group by 1,2 having count(*) > 1 order by c desc limit 10""").fetchall():
    print(f"  ({r[0]:.5f}, {r[1]:.5f}) holds {r[2]} records")
dup, = con.execute("""select count(*) from (
    select lat, lng from m group by 1,2 having count(*) > 1)""").fetchone()
print(f"  locations holding more than one record: {dup}")

h("8. Missing names")
# The Japan version lost 495 records here: `where not (...)` silently drops NULL rows
# because ilike returns NULL. The rules module wraps every predicate in coalesce for this
# reason; this section confirms named and unnamed records both survived.
for cat in CATEGORIES:
    r = con.execute(f"select count(*) filter (where name is null), count(*) "
                    f"from m where cat='{cat}'").fetchone()
    print(f"  {cat:16s} unnamed {r[0]:>4,} / {r[1]:<5,}")
