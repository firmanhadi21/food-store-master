#!/usr/bin/env python3
"""
Fetch school locations for Kota Semarang from the **Dukcapil (Kemendagri) ArcGIS
FeatureServer**.

Why this is the source that matters
-----------------------------------
fetch_schools_semarang.py notes that Dapodik does not publish coordinates. That is true of
Dapodik itself — but **Dukcapil republishes the same Kemendikbud data with coordinates**:

  https://gis.dukcapil.kemendagri.go.id/arcgis/rest/services/Hosted/
    Fasilitas_Pendidikan/FeatureServer/1        (layer "education")

  - The `source` column reads "Website Kemendikbud" / "Website Kemdikbud" /
    "Website Pindai Dikti" — i.e. **Kemendikbud-derived, not OSM-derived**. That makes it a
    genuine cross-validation source, and it carries no ODbL inheritance.
  - 448,810 records nationally; 3,078 inside the Semarang bbox (about 48% more than OSM).
  - The `tags` column carries a structured level such as "Education;School;Kindergarden",
    removing the need to parse school names — the step that produced the MAN/Mangunharjo
    misclassification in the OSM path.

** Its coverage is uneven, and this was verified rather than assumed:
  - within the Semarang bbox, tags='Elementary School' returns 0 and 'Junior High School'
    returns 0, while nationally they hold 54,159 and 93,714 — regionally incomplete
  - 'Senior High School' does not exist as a tag anywhere nationally
  => **Dukcapil contributes nothing to SD/SMP/SMA here.** Its value is TK/PAUD and higher
     education.

API notes
---------
  - `maxRecordCount` is 2000, so **paginate with resultOffset**.
  - The service's native SR is 3857; pass `outSR=4326` to receive lat/lon.
  - A WGS84 envelope can be passed directly if `inSR=4326` is set.

Output: data/semarang/dukcapil_schools_semarang.parquet
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

import duckdb

BASE = ("https://gis.dukcapil.kemendagri.go.id/arcgis/rest/services/Hosted/"
        "Fasilitas_Pendidikan/FeatureServer/1/query")
OUT_DIR = "data/semarang"
OUT = f"{OUT_DIR}/dukcapil_schools_semarang.parquet"
POLY = f"{OUT_DIR}/semarang_boundary_poly.geojson"

BBOX = {"xmin": 110.20, "ymin": -7.25, "xmax": 110.56, "ymax": -6.90,
        "spatialReference": {"wkid": 4326}}
PAGE = 2000

# tags ("Education;School;Kindergarden" style) -> level.
# **Preferred over name parsing**, which is where the OSM path went wrong.
TAG_LEVEL = {
    "kindergarden": "TK", "kindergarten": "TK", "playgroup": "TK",
    "elementary": "SD", "primary": "SD",
    "junior": "SMP", "middle": "SMP",
    "senior": "SMA", "high school": "SMA", "vocational": "SMA",
    "university": "PT", "college": "PT", "higher education": "PT",
    "informal education": "informal", "special": "SLB",
}


def fetch_page(offset):
    params = {
        "geometry": json.dumps(BBOX),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "where": "1=1",
        "outFields": "poi_name,address,tags,source",
        "outSR": "4326",
        "returnGeometry": "true",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE),
        "f": "json",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "japan-food-store-master/semarang"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"    retry {attempt + 1}: {e}")
            time.sleep(5)
    raise SystemExit(f"fetch failed at offset={offset}")


def level_from_tags(tags, name):
    """Use tags first, school-name tokens only as a fallback.

    Name parsing misfiled "SD Negeri **Man**gunharjo" as SMA (see
    fetch_schools_semarang.py), so structured tags take priority wherever present.
    """
    t = (tags or "").lower()
    for key, lv in TAG_LEVEL.items():
        if key in t:
            return lv
    # Fall back to name tokens only when tags are ambiguous — never substring matching
    toks = {x for x in re.split(r"[^A-Z0-9]+", (name or "").upper()) if x}
    for lv, s in [("TK", {"TK", "TKIT", "PAUD", "RA", "KB", "TPA", "BA"}),
                  ("SMA", {"SMA", "SMAN", "SMK", "SMKN", "MA", "MAN", "MAS", "SMAS", "SMKS"}),
                  ("SMP", {"SMP", "SMPN", "MTS", "MTSN", "SMPS", "SMPIT"}),
                  ("SD", {"SD", "SDN", "SDIT", "MI", "MIN", "MIS", "SDS"})]:
        if toks & s:
            return lv
    return "unknown"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows, offset = [], 0
    while True:
        print(f"  offset={offset:,} ...")
        data = fetch_page(offset)
        feats = data.get("features", [])
        for f in feats:
            a, g = f.get("attributes", {}), f.get("geometry") or {}
            if g.get("x") is None:
                continue
            rows.append({
                "poi_name": a.get("poi_name"),
                "address": a.get("address"),
                "tags": a.get("tags"),
                "source": a.get("source"),
                "level": level_from_tags(a.get("tags"), a.get("poi_name")),
                "lon": g["x"], "lat": g["y"],
            })
        if not data.get("exceededTransferLimit") or not feats:
            break
        offset += PAGE
    print(f"\nfetched {len(rows):,} (bbox)")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.register("r", __import__("pandas").DataFrame(rows))
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    con.execute("""create table s as select * from r
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    n, = con.execute("select count(*) from s").fetchone()
    print(f"within Kota Semarang: {n:,}")
    con.execute(f"copy s to '{OUT}' (FORMAT parquet)")
    print(f"wrote: {OUT}")

    print("\n=== by level ===")
    for row in con.execute(
            "select level, count(*) c from s group by 1 order by c desc").fetchall():
        print(f"  {row[0]:10s} {row[1]:>5,}")

    print("\n=== actual tag values (top) ===")
    for row in con.execute(
            "select tags, count(*) c from s group by 1 order by c desc limit 12").fetchall():
        print(f"  {str(row[0])[:52]:54s} {row[1]:>5,}")

    print("\n=== by source ===")
    for row in con.execute(
            "select source, count(*) c from s group by 1 order by c desc").fetchall():
        print(f"  {str(row[0]):28s} {row[1]:>5,}")

    # Cross-check against OSM. The sources are independent, so the overlap is meaningful.
    osm = f"{OUT_DIR}/osm_schools_semarang.parquet"
    if os.path.exists(osm):
        print("\n=== compared with OSM (within city limits) ===")
        con.execute(f"create table o as select * from read_parquet('{osm}')")
        no, = con.execute("select count(*) from o").fetchone()
        print(f"  Dukcapil {n:,} / OSM {no:,}")
        con.execute("""create table pair as
          select count(*) filter (where hit) m, count(*) t from (
            select exists (select 1 from o
              where 111320*sqrt(power(o.lat-s.lat,2)
                  + power((o.lon-s.lon)*cos(radians(s.lat)),2)) <= 100) hit
            from s)""")
        m, t = con.execute("select m, t from pair").fetchone()
        print(f"  Dukcapil records with an OSM counterpart within 100 m: "
              f"{m:,}/{t:,} = {m/t*100:.1f}%")
        print(f"  -> Dukcapil-only (absent from OSM): {t - m:,}")


if __name__ == "__main__":
    main()
