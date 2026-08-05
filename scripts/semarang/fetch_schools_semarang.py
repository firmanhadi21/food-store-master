#!/usr/bin/env python3
"""
Fetch school locations for Kota Semarang from OpenStreetMap (for the tobacco-near-schools
analysis).

PP 28/2024 defines two radii that need a school layer:
  - 200 m: sale of tobacco prohibited around satuan pendidikan, which per the Penjelasan to
    Pasal 518 includes PAUD/TK, madrasah, pesantren and higher education
  - 500 m: advertising prohibited

On source choice
----------------
The obvious first choice is Dapodik, but **it does not publish coordinates** — they live in
Verval SP, which is authenticated. dapo.kemendikdasmen.go.id returns 403 to bots;
referensi.data.kemendikdasmen.go.id publishes NPSN and names but no latitude/longitude
(the existing scraper egin10/dapodik confirms the same).

=> **OSM is the only source immediately usable with coordinates.** Dapodik is used instead
   for completeness verification, matching published counts against this layer
   (verify_school_completeness.py). Dukcapil republishes Kemendikbud data *with* coordinates
   and is fetched separately (fetch_schools_dukcapil.py), but holds no SD or SMP for Semarang.

Output: data/semarang/osm_schools_semarang.parquet
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

import duckdb

OUT_DIR = "data/semarang"
OUT = f"{OUT_DIR}/osm_schools_semarang.parquet"
POLY = f"{OUT_DIR}/semarang_boundary_poly.geojson"

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

BBOX = "-7.25,110.20,-6.90,110.56"  # S,W,N,E

# Indonesian school levels:
#   SD/MI       primary            isced:level=1
#   SMP/MTs     lower secondary    isced:level=2
#   SMA/SMK/MA  upper secondary    isced:level=3
#   TK/PAUD     early childhood
# For smoking initiation SMP and SMA matter most; for exposure, SD and TK matter too.
QUERY = f"""
[out:json][timeout:180];
(
  nwr["amenity"="school"]({BBOX});
  nwr["amenity"="kindergarten"]({BBOX});
);
out center tags;
"""

# Level tokens found in school names. **Matched as whole tokens, not substrings.**
#
# ** The first version used `if pattern in name` and misfiled "SD Negeri **Man**gunharjo"
#   as SMA, because MANGUNHARJO contains MAN (Madrasah Aliyah Negeri) — turning a primary
#   school into a secondary one. Same class of bug as griya / mart / toko in the master
#   build. Indonesian school names carry these abbreviations as standalone tokens, so
#   token matching is both sufficient and safe.
LEVEL_TOKENS = {
    "TK":  {"TK", "TKIT", "TKS", "PAUD", "RA", "KB", "BA", "TPA"},
    "SD":  {"SD", "SDN", "SDIT", "SDS", "SDI", "MI", "MIN", "MIS", "MIT"},
    "SMP": {"SMP", "SMPN", "SMPIT", "SMPS", "MTS", "MTSN", "MTSS"},
    "SMA": {"SMA", "SMAN", "SMAS", "SMAIT", "SMK", "SMKN", "SMKS",
            "MA", "MAN", "MAS", "MAK"},
}
# Order of evaluation. With token matching the order barely matters, but checking SMP/SMA
# before SD removes any chance of SD swallowing a longer abbreviation.
LEVEL_ORDER = ["TK", "SMA", "SMP", "SD"]


def overpass(query):
    for ep in ENDPOINTS:
        try:
            print(f"  Overpass -> {ep}")
            req = urllib.request.Request(
                ep, data=urllib.parse.urlencode({"data": query}).encode(),
                headers={"User-Agent": "japan-food-store-master/semarang-poc"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"    failed: {e}")
            time.sleep(3)
    raise SystemExit("all Overpass endpoints failed")


def school_level(name, tags):
    """Infer level from the school name; Indonesian names carry the abbreviation.

    Prefers OSM's isced:level where present.
    """
    isced = tags.get("isced:level")
    if isced:
        return {"0": "TK", "1": "SD", "2": "SMP", "3": "SMA"}.get(str(isced)[0], "unknown")
    if tags.get("amenity") == "kindergarten":
        return "TK"
    # Tokenise on non-alphanumerics so "SDN-01" and "SD/MI" both split correctly
    tokens = {t for t in re.split(r"[^A-Z0-9]+", (name or "").upper()) if t}
    for lv in LEVEL_ORDER:
        if tokens & LEVEL_TOKENS[lv]:
            return lv
    return "unknown"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = overpass(QUERY)
    rows = []
    for el in data["elements"]:
        tags = el.get("tags", {})
        if el["type"] == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            c = el.get("center") or {}
            lat, lon = c.get("lat"), c.get("lon")
        if lat is None or lon is None:
            continue
        name = tags.get("name")
        rows.append({
            "osm_id": f"{el['type']}/{el['id']}",
            "name": name,
            "level": school_level(name, tags),
            "amenity": tags.get("amenity"),
            "operator_type": tags.get("operator:type"),
            "lat": lat, "lon": lon,
        })
    print(f"\nOSM schools in bbox: {len(rows):,}")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.register("r", __import__("pandas").DataFrame(rows))
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    con.execute("""create table s as
      select * from r
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    n, = con.execute("select count(*) from s").fetchone()
    print(f"within Kota Semarang: {n:,}")

    con.execute(f"copy s to '{OUT}' (FORMAT parquet)")
    print(f"wrote: {OUT}")

    print("\n=== by level ===")
    for row in con.execute(
            "select level, count(*) c, count(name) named from s group by 1 order by c desc"
    ).fetchall():
        print(f"  {row[0]:8s} {row[1]:>4,}  (named {row[2]:,})")

    print("\n=== name samples ===")
    for row in con.execute(
            "select level, name from s where name is not null order by random() limit 15"
    ).fetchall():
        print(f"  {row[0]:6s} {row[1]}")


if __name__ == "__main__":
    main()
