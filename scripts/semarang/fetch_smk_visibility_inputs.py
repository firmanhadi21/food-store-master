#!/usr/bin/env python3
"""
Fetch the OSM layers the SMK visibility score needs, for Kota Semarang, from Overpass.

  1. Drivable road network (ways + node coordinates) — used for both the frontage factor
     (distance to an arterial/collector, class of the road at the gate) and the
     customer-reach factor (population reachable within N minutes along the network).
  2. Public-transport stops — bus_stop / platform, which covers Trans Semarang shelters.

Population comes from WorldPop 2020 constrained 100 m (downloaded separately, see
build step docstring); commercial POIs reuse data/semarang/overture_semarang_all.parquet.

Output: data/semarang/osm_roads_semarang.json   {"nodes": {id: [lon, lat]}, "ways": [...]}
        data/semarang/osm_transit_semarang.parquet
"""
import json
import os
import time
import urllib.parse
import urllib.request

import duckdb

OUT_DIR = "data/semarang"
OUT_ROADS = f"{OUT_DIR}/osm_roads_semarang.json"
OUT_TRANSIT = f"{OUT_DIR}/osm_transit_semarang.parquet"

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

BBOX = "-7.25,110.20,-6.90,110.56"  # S,W,N,E — same as fetch_osm_semarang.py

# Everything a car or motorbike can use. Footways, paths and steps are left out: a
# customer bringing a vehicle in for service does not arrive along them.
ROAD_QUERY = f"""
[out:json][timeout:300];
way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|road)$"]({BBOX});
out body geom qt;
"""

TRANSIT_QUERY = f"""
[out:json][timeout:180];
(
  node["highway"="bus_stop"]({BBOX});
  nwr["public_transport"="platform"]["bus"="yes"]({BBOX});
  nwr["public_transport"="platform"]["highway"="bus_stop"]({BBOX});
  nwr["amenity"="bus_station"]({BBOX});
);
out center tags;
"""


def overpass(query, label):
    for ep in ENDPOINTS:
        try:
            print(f"  Overpass ({label}) -> {ep}")
            req = urllib.request.Request(
                ep, data=urllib.parse.urlencode({"data": query}).encode(),
                headers={"User-Agent": "japan-food-store-master/semarang-smk"})
            with urllib.request.urlopen(req, timeout=400) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"    failed: {e}")
            time.sleep(3)
    raise SystemExit(f"all Overpass endpoints failed: {label}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---- 1. roads ----
    data = overpass(ROAD_QUERY, "roads")
    nodes, ways = {}, []
    for el in data["elements"]:
        if el["type"] == "way":
            # `out body geom` carries node ids and coordinates side by side
            for nid, g in zip(el["nodes"], el["geometry"]):
                nodes[nid] = [g["lon"], g["lat"]]
            t = el["tags"]
            ways.append({"id": el["id"], "nodes": el["nodes"], "highway": t["highway"],
                         "oneway": t.get("oneway", "no"), "name": t.get("name")})
    with open(OUT_ROADS, "w") as f:
        json.dump({"nodes": nodes, "ways": ways}, f)
    print(f"  roads: {len(ways):,} ways, {len(nodes):,} nodes -> {OUT_ROADS}")

    # ---- 2. transit stops ----
    data = overpass(TRANSIT_QUERY, "transit")
    rows = []
    for el in data["elements"]:
        lon = el.get("lon", el.get("center", {}).get("lon"))
        lat = el.get("lat", el.get("center", {}).get("lat"))
        if lon is None:
            continue
        t = el.get("tags", {})
        rows.append((f"{el['type']}/{el['id']}", t.get("name"), t.get("network"), lon, lat))
    con = duckdb.connect()
    con.execute("create table t(osm_id varchar, name varchar, network varchar, "
                "lon double, lat double)")
    con.executemany("insert into t values (?,?,?,?,?)", rows)
    con.execute(f"copy t to '{OUT_TRANSIT}' (format parquet)")
    print(f"  transit: {len(rows):,} stops -> {OUT_TRANSIT}")


if __name__ == "__main__":
    main()
