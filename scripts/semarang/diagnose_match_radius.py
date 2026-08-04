#!/usr/bin/env python3
"""
Measure how much of the same chain Overture and OSM actually share, by sweeping the match
radius.

Why this matters
----------------
compare_sources_semarang.py found that only 18 of 84 OSM Alfamart records match an Overture
Alfamart within 100 m. There are two readings, and they lead to opposite designs:

  H1: the two sources hold **different real stores** (genuinely complementary)
      => the union is correct, and unlike Japan, "Overture union OSM" is the right call.
  H2: the same stores, but **coordinates too far apart to match**
      => the union inflates, and single-source-per-category is right, as in Japan.

Test: widen the match radius and watch how the match count grows.
  - plateaus early  -> H1 (widening does not find them because they are different stores)
  - keeps climbing  -> H2 (coordinate drift)

Also verifies the assembled city polygon by area, working around ST_Area_Spheroid returning
nan in this environment (a known issue, documented on the Japan side too).
"""
import duckdb

D = "data/semarang"
POLY = f"{D}/semarang_boundary_poly.geojson"

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("0. Sanity-check the city polygon (ST_Area_Spheroid returns nan here)")
# Equirectangular: at latitude -7, one degree of longitude is 111,320 * cos(7 deg) metres
a_deg, = con.execute("select ST_Area(geom) from kota").fetchone()
km2 = a_deg * 111.320 * 111.320 * 0.99255
print(f"  ST_Area (deg^2) = {a_deg:.6f}")
print(f"  equirectangular = {km2:,.1f} km2   (Kota Semarang official 373.8 km2)")
print(f"  -> ratio {km2 / 373.8:.3f}; near 1.0 means the ring assembly is correct")

con.execute(f"""create table ov as
  select name, category, brand_name, lon, lat, ST_Point(lon, lat) geom
  from read_parquet('{D}/overture_semarang_all.parquet')
  where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
con.execute(f"""create table osm as
  select name, shop, amenity, brand, lon, lat, ST_Point(lon, lat) geom
  from read_parquet('{D}/osm_semarang_food.parquet')
  where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")

h("1. Match count against radius — the H1 vs H2 test")
# One degree of latitude ~ 111,320 m. Longitude differs by cos(7 deg) ~ 0.9926, so the grid
# is near-isotropic and degrees are an acceptable approximation.
RADII = [(50, 0.00045), (100, 0.0009), (200, 0.0018), (300, 0.0027),
         (500, 0.0045), (1000, 0.0090)]
for kw in ["alfamart", "indomaret"]:
    nov, = con.execute(f"select count(*) from ov where name ilike '%{kw}%'").fetchone()
    nosm, = con.execute(f"select count(*) from osm where name ilike '%{kw}%'").fetchone()
    print(f"\n  {kw}  (Overture {nov} / OSM {nosm})")
    print(f"    {'radius':>8s} {'matched':>8s} {'OSM matched':>13s} {'union':>8s}")
    for m, deg in RADII:
        k, = con.execute(f"""
          select count(*) from osm o where o.name ilike '%{kw}%'
            and exists (select 1 from ov v where v.name ilike '%{kw}%'
                        and ST_DWithin(o.geom, v.geom, {deg}))""").fetchone()
        print(f"    {m:>6d}m {k:>8,} {k / nosm * 100:>12.1f}% {nov + nosm - k:>8,}")

h("2. Control — distance between same-brand stores within one source")
# **This is what makes the sweep interpretable.** If neighbouring Alfamart stores are only
# ~500 m apart, then a 500 m match radius is matching a *different* store, not the same one,
# so results at wide radii are meaningless regardless of which hypothesis holds.
for src, tbl, f in [("Overture", "ov", "name ilike '%alfamart%'"),
                    ("OSM", "osm", "name ilike '%alfamart%'")]:
    row = con.execute(f"""
      with p as (select lon, lat from {tbl} where {f}),
      d as (select a.lon, a.lat,
                   min(111320*sqrt(power(b.lat-a.lat,2)
                     + power((b.lon-a.lon)*cos(radians(a.lat)),2))) m
            from p a join p b on (a.lon,a.lat) != (b.lon,b.lat) group by 1,2)
      select round(min(m)), round(quantile_cont(m,0.1)), round(median(m)),
             round(quantile_cont(m,0.9)) from d""").fetchone()
    print(f"  {src:9s} nearest same-brand store  min={row[0]:>5.0f}m p10={row[1]:>5.0f}m "
          f"median={row[2]:>5.0f}m p90={row[3]:>5.0f}m")

h("3. Are OSM-only chain stores really different stores? What lies near them")
for row in con.execute("""
    select o.name,
           (select count(*) from ov v
            where ST_DWithin(o.geom, v.geom, 0.0009)) as ov_any_poi,
           (select count(*) from ov v where v.category='convenience_store'
            and ST_DWithin(o.geom, v.geom, 0.0009)) as ov_cvs
    from osm o
    where (o.name ilike '%alfamart%' or o.name ilike '%indomaret%')
      and not exists (select 1 from ov v
                      where (v.name ilike '%alfamart%' or v.name ilike '%indomaret%')
                        and ST_DWithin(o.geom, v.geom, 0.0009))
    order by ov_any_poi limit 15""").fetchall():
    print(f"  {str(row[0])[:34]:36s} Overture POIs within 100m={row[1]:>3,} "
          f"of which convenience={row[2]}")
n_iso, = con.execute("""
    select count(*) from osm o
    where (o.name ilike '%alfamart%' or o.name ilike '%indomaret%')
      and not exists (select 1 from ov v
                      where (v.name ilike '%alfamart%' or v.name ilike '%indomaret%')
                        and ST_DWithin(o.geom, v.geom, 0.0009))
      and not exists (select 1 from ov v where v.category='convenience_store'
                      and ST_DWithin(o.geom, v.geom, 0.0009))""").fetchone()
print(f"\n  OSM-only minimarkets with **no Overture convenience store at all** within"
      f" 100 m: {n_iso}")
print("  The larger this is, the stronger the evidence for H1 — real stores Overture")
print("  missed entirely, rather than the same stores recorded at different coordinates.")
