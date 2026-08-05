#!/usr/bin/env python3
"""
Count Alfamart and Indomaret via the Google Places API (New), as an external check on the
master.

Why this is needed
------------------
Nothing yet establishes what share of real chain stores the master holds (Alfamart 182,
Indomaret 216). This is the Semarang counterpart of the "verify quantity against official
statistics" step the Japan project did with retail-dynamics data and JFA figures; without it,
"can the master be trusted?" is unanswerable.

The official store locators are unusable (measured):
  Alfagift  webcommerce-gw.alfagift.id/v2/stores/coordinate/candidate-list -> **401** (login)
  klikindomaret  www.klikindomaret.com/webapi/api/store/*                  -> **403** (WAF)
  Authenticating or defeating a WAF to harvest a store database would breach both companies'
  terms of service, so neither is attempted. Google Places is used instead: a third party,
  and legitimate.

Design
------
- Text Search returns at most 20 results per request and 60 with paging, so the city cannot be
  covered in one call. It is **split into a grid**, searched per cell, and deduplicated by
  place id.
- A cell returning 60 results is **probably truncated**, so it is flagged for subdivision.
- Calls cost money, so **dry-run is the default**: counts and an estimate are printed and no
  request is made. `--run` is required. Responses are cached so a re-run does not bill twice.

Usage
-----
  # 1. estimate first, no charge
  python3 scripts/semarang/fetch_chains_google_places.py

  # 2. supply the key via the environment (never as an argument, which lands in shell history)
  export GOOGLE_MAPS_API_KEY='...'
  python3 scripts/semarang/fetch_chains_google_places.py --run

Output: data/semarang/google_chains_semarang.parquet
        docs/semarang/verify_chain-counts-vs-google.csv
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

import duckdb

D = "data/semarang"
POLY = f"{D}/semarang_boundary_poly.geojson"
CACHE = f"{D}/google_cache"
OUT = f"{D}/google_chains_semarang.parquet"
OUT_CSV = "docs/semarang/verify_chain-counts-vs-google.csv"

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
# Minimal Pro-tier field set. Enterprise fields such as rating are not requested, because
# they move the call into a more expensive SKU.
FIELD_MASK = ("places.id,places.displayName,places.location,"
              "places.formattedAddress,places.primaryType")

CHAINS = ["Alfamart", "Indomaret"]
CELL_KM = 2.0          # grid pitch, fine enough that no cell should exceed 60 results
PAGE_LIMIT = 3         # Text Search paging cap (20 x 3 = 60)
COST_PER_1K = 32.0     # approximate Text Search Pro unit price, USD; actual billing varies


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def grid_cells():
    """Return CELL_KM grid cells (as rectangles) that intersect the city polygon."""
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    xmin, xmax, ymin, ymax = con.execute(
        "select ST_XMin(geom), ST_XMax(geom), ST_YMin(geom), ST_YMax(geom) from kota"
    ).fetchone()
    dlat = CELL_KM / 111.320
    dlon = CELL_KM / (111.320 * 0.99255)
    cells = []
    y = ymin
    while y < ymax:
        x = xmin
        while x < xmax:
            # Keep only cells that touch the city, to avoid paying for empty ones
            hit, = con.execute(
                "select count(*) from kota where ST_Intersects(geom, "
                f"ST_MakeEnvelope({x}, {y}, {x + dlon}, {y + dlat}))").fetchone()
            if hit:
                cells.append((y, x, y + dlat, x + dlon))
            x += dlon
        y += dlat
    return cells


def search(chain, cell, key):
    """Search one cell, paging up to 60 results. Uses the cache when present."""
    os.makedirs(CACHE, exist_ok=True)
    tag = f"{chain}_{cell[0]:.4f}_{cell[1]:.4f}".replace("-", "m").replace(".", "_")
    cpath = os.path.join(CACHE, f"{tag}.json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f), True

    out, token = [], None
    for _ in range(PAGE_LIMIT):
        body = {
            "textQuery": chain,
            "locationRestriction": {"rectangle": {
                "low": {"latitude": cell[0], "longitude": cell[1]},
                "high": {"latitude": cell[2], "longitude": cell[3]}}},
        }
        if token:
            body["pageToken"] = token
        req = urllib.request.Request(
            ENDPOINT, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "X-Goog-Api-Key": key,
                     "X-Goog-FieldMask": FIELD_MASK})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            sys.exit(f"\nAPI error {e.code}: {msg}\n"
                     "(401/403 usually means the key is unset, Places API (New) is not "
                     "enabled, or the key's API restrictions exclude it)")
        out.extend(data.get("places", []))
        token = data.get("nextPageToken")
        if not token:
            break
        time.sleep(2)  # a pageToken can be rejected if used immediately after issue
    with open(cpath, "w") as f:
        json.dump(out, f)
    return out, False


def main():
    run = "--run" in sys.argv
    cells = grid_cells()
    n_req = len(cells) * len(CHAINS)
    print(f"{CELL_KM} km cells touching the city: {len(cells)}")
    print(f"{len(CHAINS)} chains x cells = **at least {n_req} requests** "
          f"(up to {n_req * PAGE_LIMIT} with paging)")
    print(f"estimated cost: ${n_req * COST_PER_1K / 1000:.2f} to "
          f"${n_req * PAGE_LIMIT * COST_PER_1K / 1000:.2f} "
          f"(assuming Text Search Pro at ${COST_PER_1K}/1000)")

    if not run:
        print("\nDry run — no API calls were made.")
        print("  To execute, set GOOGLE_MAPS_API_KEY and pass --run.")
        return

    key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("GOOGLE_MAPS_API_KEY is not set. Pass the key by environment variable, "
                 "not as an argument.")

    rows, saturated = {}, []
    for chain in CHAINS:
        hit_cache = 0
        for i, cell in enumerate(cells, 1):
            places, cached = search(chain, cell, key)
            hit_cache += cached
            if len(places) >= 20 * PAGE_LIMIT:
                saturated.append((chain, cell))
            for p in places:
                loc = p.get("location") or {}
                rows[p["id"]] = {
                    "place_id": p["id"],
                    "chain": chain,
                    "name": (p.get("displayName") or {}).get("text"),
                    "address": p.get("formattedAddress"),
                    "primary_type": p.get("primaryType"),
                    "lat": loc.get("latitude"), "lon": loc.get("longitude"),
                }
            if i % 20 == 0:
                print(f"  {chain}: {i}/{len(cells)} cells "
                      f"(cached {hit_cache}) running total {len(rows):,}")
        print(f"  {chain}: done. cache hits {hit_cache}/{len(cells)}")

    if saturated:
        print(f"\n! {len(saturated)} cells hit the 60-result ceiling and may be truncated. "
              "Consider reducing CELL_KM and re-running.")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.register("r", __import__("pandas").DataFrame(list(rows.values())))
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    # ** Text Search can return places outside the rectangle (locationRestriction is not
    #   always strict), so always clip to the city polygon.
    con.execute("""create table g as select * from r
      where lat is not null and exists (
        select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    # Drop results whose name does not contain the brand — searching "Alfamart" also returns
    # unrelated businesses.
    con.execute("""create or replace table g as select * from g
      where lower(name) like '%' || lower(chain) || '%'""")
    con.execute(f"copy g to '{OUT}' (FORMAT parquet)")
    n, = con.execute("select count(*) from g").fetchone()
    print(f"\nin city and brand-name matched: {n:,} -> {OUT}")

    # ---- Duplicate diagnosis on the Google side ----
    # When the ratio lands near 0.5, "the master is missing half" and "Google is
    # double-counting" have to be separated. Google Places can hold the same store under
    # several place ids (Point/Fresh sub-formats, ATMs, parcel points, closed stores).
    h("Duplicates within Google (same chain within 50 m)")
    for chain in CHAINS:
        dup, = con.execute(f"""
          select count(*) from g a where a.chain='{chain}' and exists (
            select 1 from g b where b.chain='{chain}' and b.place_id != a.place_id
              and 111320*sqrt(power(a.lat-b.lat,2)
                + power((a.lon-b.lon)*cos(radians(a.lat)),2)) <= 50)""").fetchone()
        tot, = con.execute(f"select count(*) from g where chain='{chain}'").fetchone()
        print(f"  {chain:12s} {dup:>4,}/{tot:<5,} = {dup/tot*100:5.1f}% have a same-chain"
              f" record within 50 m")
    print("  The higher this is, the more likely Google is double-counting — real stores")
    print("  rarely stand 50 m apart.")

    h("Name variants in Google (checking for sub-formats and non-stores)")
    for row in con.execute("""
        select chain, name, count(*) c from g
        where lower(name) not in (lower(chain))
        group by 1,2 order by c desc limit 15""").fetchall():
        print(f"  {row[0]:11s} {str(row[1])[:44]:46s} {row[2]:>3,}")

    h("Reconciliation against the master")
    con.execute(f"""create table m as
      select * from read_parquet('{D}/semarang_food_master.parquet')""")
    out_rows = []
    print(f"  {'chain':12s} {'Google':>7s} {'master':>8s} {'ratio':>6s} "
          f"{'matched 100m':>13s} {'Google-only':>12s}")
    for chain in CHAINS:
        gc, = con.execute(f"select count(*) from g where chain='{chain}'").fetchone()
        mc, = con.execute(
            f"select count(*) from m where name ilike '%{chain}%'").fetchone()
        match, = con.execute(f"""
          select count(*) from g where chain='{chain}' and exists (
            select 1 from m where m.name ilike '%{chain}%'
              and 111320*sqrt(power(m.lat-g.lat,2)
                + power((m.lng-g.lon)*cos(radians(g.lat)),2)) <= 100)""").fetchone()
        ratio = mc / gc if gc else 0
        print(f"  {chain:12s} {gc:>7,} {mc:>8,} {ratio:>6.2f} {match:>13,} {gc - match:>12,}")
        out_rows.append((chain, gc, mc, round(ratio, 3), match, gc - match))

    os.makedirs("docs/semarang", exist_ok=True)
    # ** DuckDB identifiers cannot begin with a digit — a column named "100m_match" raises a
    #   Parser Error, which this actually hit. Keep column names alphabetic-initial.
    con.execute('create table res(chain varchar, google_n bigint, master_n bigint, '
                'master_ratio double, match_100m bigint, google_only bigint)')
    con.executemany("insert into res values (?,?,?,?,?,?)", out_rows)
    con.execute(f"copy res to '{OUT_CSV}' (header, delimiter ',')")
    print(f"\nwrote: {OUT_CSV}")
    print("\nNote: Google Places is not a census either. Treat it as a third source and ask")
    print("whether the magnitudes agree and whether there are large spatial holes — not")
    print("whether the master/Google ratio is 1.0.")


if __name__ == "__main__":
    main()
