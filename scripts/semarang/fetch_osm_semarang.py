#!/usr/bin/env python3
"""
Overpass API から Kota Semarang の食料品小売 POI と行政境界を取得する。

日本版が `data/osm_food_stores_japan.tsv` を前提にしているのに対し、こちらは
Overpass から直接引く（対象が1市なので現実的なサイズに収まる）。

インドネシア固有のタグ設計:
  - shop=convenience    … Alfamart/Indomaret などのミニマーケット、および toko kelontong
  - shop=supermarket    … Superindo/Hypermart など
  - shop=greengrocer/butcher/seafood/fishmonger … 生鮮
  - amenity=marketplace … **pasar tradisional**。日本版に無い最重要カテゴリ。
                          1施設が多数の売り手を抱える「面」の存在なので点として扱えない
  - shop=general/kiosk  … warung / toko kelontong に相当しうる

出力:
  data/semarang/osm_semarang_food.parquet
  data/semarang/semarang_boundary.geojson   (Kota Semarang の行政界)
"""
import json
import os
import time
import urllib.parse
import urllib.request

import duckdb

OUT_DIR = "data/semarang"
OUT_POI = f"{OUT_DIR}/osm_semarang_food.parquet"
OUT_BND = f"{OUT_DIR}/semarang_boundary.geojson"

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

BBOX = "-7.25,110.20,-6.90,110.56"  # S,W,N,E

# 食料品小売になりうる全タグ。判定は後段（build）で行い、ここでは広く取る。
POI_QUERY = f"""
[out:json][timeout:180];
(
  nwr["shop"~"^(convenience|supermarket|greengrocer|butcher|seafood|fishmonger|general|kiosk|grocery|deli|bakery|health_food|farm|frozen_food|spices|dairy|food)$"]({BBOX});
  nwr["amenity"="marketplace"]({BBOX});
);
out center tags;
"""

BND_QUERY = """
[out:json][timeout:180];
relation["boundary"="administrative"]["name"~"Semarang",i]["admin_level"~"^(5|6)$"];
out geom;
"""


def overpass(query, label):
    for ep in ENDPOINTS:
        try:
            print(f"  Overpass ({label}) -> {ep}")
            req = urllib.request.Request(
                ep, data=urllib.parse.urlencode({"data": query}).encode(),
                headers={"User-Agent": "japan-food-store-master/semarang-poc"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"    失敗: {e}")
            time.sleep(3)
    raise SystemExit(f"Overpass 全滅: {label}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---- 1. POI ----
    data = overpass(POI_QUERY, "POI")
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
        rows.append({
            "osm_id": f"{el['type']}/{el['id']}",
            "name": tags.get("name"),
            "shop": tags.get("shop"),
            "amenity": tags.get("amenity"),
            "brand": tags.get("brand"),
            "operator": tags.get("operator"),
            "lat": lat, "lon": lon,
        })
    print(f"\nOSM POI {len(rows):,} 件")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.register("r", __import__("pandas").DataFrame(rows))
    con.execute(f"copy r to '{OUT_POI}' (FORMAT parquet)")
    print(f"出力: {OUT_POI}")

    print("\n=== shop / amenity 別 ===")
    for row in con.execute("""
        select coalesce(shop, 'amenity=' || amenity) k, count(*) c
        from r group by 1 order by c desc""").fetchall():
        print(f"  {str(row[0]):24s} {row[1]:>6,}")

    print("\n=== ブランド構成（shop=convenience）===")
    for row in con.execute("""
        select coalesce(brand, operator, '(なし)') b, count(*) c
        from r where shop='convenience' group by 1 order by c desc limit 15""").fetchall():
        print(f"  {str(row[0]):28s} {row[1]:>6,}")

    print("\n=== 名称キーワード横断 ===")
    for kw in ['alfamart', 'indomaret', 'alfamidi', 'superindo', 'pasar', 'toko', 'warung']:
        c, = con.execute(f"select count(*) from r where name ilike '%{kw}%'").fetchone()
        print(f"  {kw:12s} {c:>6,}")

    # ---- 2. 行政境界 ----
    bnd = overpass(BND_QUERY, "boundary")
    feats = []
    for el in bnd["elements"]:
        tags = el.get("tags", {})
        outers = [m["geometry"] for m in el.get("members", [])
                  if m.get("role") == "outer" and m.get("geometry")]
        if not outers:
            continue
        feats.append({
            "type": "Feature",
            "properties": {"name": tags.get("name"),
                           "admin_level": tags.get("admin_level"),
                           "osm_id": el["id"]},
            "geometry": {"type": "MultiLineString",
                         "coordinates": [[[p["lon"], p["lat"]] for p in g] for g in outers]},
        })
    with open(OUT_BND, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)
    print(f"\n境界候補 {len(feats)} 件 -> {OUT_BND}")
    for ft in feats:
        p = ft["properties"]
        print(f"  admin_level={p['admin_level']:3s} {p['name']}  (osm {p['osm_id']})")


if __name__ == "__main__":
    main()
