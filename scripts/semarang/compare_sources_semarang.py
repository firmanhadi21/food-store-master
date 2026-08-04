#!/usr/bin/env python3
"""
Compare Overture against OSM inside Kota Semarang, to decide which should be the primary
source.

The Japan version's criteria (the Japan-side master design doc, section 1):
  - pick the **single most complete source** per category
  - naive unions inflate through coordinate drift (133% for Japanese convenience stores)
Re-run the same checks here, and let the answer be re-derived rather than inherited.

Output: data/semarang/semarang_boundary_poly.geojson (assembled Kota Semarang polygon)
"""
import json
import os
import urllib.parse
import urllib.request

import duckdb

OUT_DIR = "data/semarang"
POLY = f"{OUT_DIR}/semarang_boundary_poly.geojson"
OV = f"read_parquet('{OUT_DIR}/overture_semarang_all.parquet')"
OSM = f"read_parquet('{OUT_DIR}/osm_semarang_food.parquet')"

KOTA_SEMARANG_REL = 8409116  # OSM relation, admin_level=5


def fetch_polygon():
    """Assemble the outer rings of the Kota Semarang relation into a polygon.

    Overpass `out geom` returns disconnected way segments, so endpoints must be stitched
    into closed rings. Skipping this leaves ST_Contains unusable.
    """
    if os.path.exists(POLY):
        return
    q = f"[out:json][timeout:180];relation({KOTA_SEMARANG_REL});out geom;"
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=urllib.parse.urlencode({"data": q}).encode(),
        headers={"User-Agent": "japan-food-store-master/semarang-poc"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())

    ways = [[(p["lon"], p["lat"]) for p in m["geometry"]]
            for m in data["elements"][0]["members"]
            if m.get("role") == "outer" and m.get("geometry")]
    print(f"stitching {len(ways)} outer ways into rings")

    rings, pending = [], list(ways)
    cur = pending.pop(0)
    while True:
        if cur[0] == cur[-1] and len(cur) > 3:
            rings.append(cur)
            if not pending:
                break
            cur = pending.pop(0)
            continue
        for i, w in enumerate(pending):
            if w[0] == cur[-1]:
                cur = cur + w[1:]; pending.pop(i); break
            if w[-1] == cur[-1]:
                cur = cur + w[::-1][1:]; pending.pop(i); break
            if w[-1] == cur[0]:
                cur = w[:-1] + cur; pending.pop(i); break
            if w[0] == cur[0]:
                cur = w[::-1][:-1] + cur; pending.pop(i); break
        else:
            rings.append(cur)          # emit unclosed fragments as-is
            if not pending:
                break
            cur = pending.pop(0)

    rings = [r for r in rings if len(r) > 3]
    main = max(rings, key=len)          # the longest ring is the city outline
    if main[0] != main[-1]:
        main = main + [main[0]]
    gj = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"name": "Kota Semarang"},
        "geometry": {"type": "Polygon", "coordinates": [main]}}]}
    with open(POLY, "w") as f:
        json.dump(gj, f)
    print(f"wrote: {POLY}  ({len(main):,} vertices)")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main():
    fetch_polygon()
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    # ST_Area_Spheroid returns nan in this environment (known, see the Japan CLAUDE.md), so
    # area is checked by equirectangular approximation in diagnose_match_radius.py instead.
    area, = con.execute("select ST_Area_Spheroid(geom)/1e6 from kota").fetchone()
    print(f"Kota Semarang area = {area:,.1f} km2 (official 373.8 km2; nan is expected here)")

    # Clip from bbox to city limits
    con.execute(f"""create table ov as
      select *, ST_Point(lon, lat) geom from {OV}
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    con.execute(f"""create table osm as
      select *, ST_Point(lon, lat) geom from {OSM}
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    nov, = con.execute("select count(*) from ov").fetchone()
    nosm, = con.execute("select count(*) from osm").fetchone()
    print(f"within city: Overture all POIs {nov:,} / OSM food POIs {nosm:,}")

    h("1. Counts by category, within city limits")
    print(f"  {'category':22s} {'Overture':>10s} {'OSM':>8s}")
    pairs = [
        ("minimarket", "category='convenience_store'", "shop='convenience'"),
        ("supermarket", "category='supermarket'", "shop='supermarket'"),
        ("grocery", "category='grocery_store'", "shop in ('grocery','general','kiosk')"),
        ("fresh produce", "category in ('butcher_shop','seafood_market','fruits_and_vegetables')",
         "shop in ('butcher','seafood','fishmonger','greengrocer','dairy','farm')"),
        ("pasar (market)", "category in ('farmers_market','market','public_market')",
         "amenity='marketplace'"),
        ("bakery", "category='bakery'", "shop='bakery'"),
    ]
    for label, ovf, osmf in pairs:
        a, = con.execute(f"select count(*) from ov where {ovf}").fetchone()
        b, = con.execute(f"select count(*) from osm where {osmf}").fetchone()
        print(f"  {label:22s} {a:>10,} {b:>8,}")

    h("2. Chain reconciliation — the only category with an external ground truth")
    print(f"  {'chain':14s} {'Overture':>9s} {'OSM':>7s} {'matched <100m':>15s} {'union':>8s}")
    for kw in ["alfamart", "indomaret", "alfamidi", "superindo"]:
        a, = con.execute(f"select count(*) from ov where name ilike '%{kw}%'").fetchone()
        b, = con.execute(f"select count(*) from osm where name ilike '%{kw}%'").fetchone()
        # 100 m ~ 0.0009 degrees; near the equator the longitude correction is negligible
        m, = con.execute(f"""
          select count(*) from osm o
          where o.name ilike '%{kw}%'
            and exists (select 1 from ov v where v.name ilike '%{kw}%'
                        and ST_DWithin(o.geom, v.geom, 0.0009))""").fetchone()
        print(f"  {kw:14s} {a:>9,} {b:>7,} {m:>15,} {a + b - m:>8,}")

    h("3. Union inflation test (Japan's convenience stores inflated to 133%)")
    a, = con.execute("select count(*) from ov where category='convenience_store'").fetchone()
    b, = con.execute("select count(*) from osm where shop='convenience'").fetchone()
    m, = con.execute("""
      select count(*) from osm o where o.shop='convenience'
        and exists (select 1 from ov v where v.category='convenience_store'
                    and ST_DWithin(o.geom, v.geom, 0.0009))""").fetchone()
    print(f"  Overture {a:,} / OSM {b:,} / matched within 100 m {m:,}")
    print(f"  -> OSM-only {b - m:,}, union {a + b - m:,}")
    print(f"  -> share of OSM records absent from Overture = {(b - m) / b * 100:.1f}%")

    h("4. pasar (traditional markets) — Indonesia-specific, the main fresh-food channel")
    print("  Sample of OSM amenity=marketplace names:")
    for row in con.execute("""
        select name from osm where amenity='marketplace' and name is not null
        order by name limit 25""").fetchall():
        print(f"    {row[0]}")
    n_pasar, = con.execute("select count(*) from osm where amenity='marketplace'").fetchone()
    n_named, = con.execute(
        "select count(*) from osm where amenity='marketplace' and name is not null").fetchone()
    print(f"  total {n_pasar} ({n_named} named)")

    h("5. Overture quality — the biggest difference from Japan is its provenance mix")
    print("  contributing datasets, within city limits:")
    for row in con.execute("""
        select ds, count(*) c from (select unnest(datasets) ds from ov)
        where ds != 'Overture' group by 1 order by c desc""").fetchall():
        print(f"    {str(row[0]):18s} {row[1]:>7,}")
    print("\n  brand fill rate (drives how well chains can be reconciled):")
    for label, f in [("Overture convenience_store", "ov where category='convenience_store'"),
                     ("OSM shop=convenience", "osm where shop='convenience'")]:
        tot, br = con.execute(
            f"select count(*), count(brand{'_name' if 'ov ' in f else ''}) from {f}").fetchone()
        print(f"    {label:28s} {br:>5,}/{tot:<5,} = {br/tot*100:5.1f}%")


if __name__ == "__main__":
    main()
