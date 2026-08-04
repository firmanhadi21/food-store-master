#!/usr/bin/env python3
"""
Kota Semarang の学校位置を **Dukcapil（Kemendagri）の ArcGIS FeatureServer** から取得する。

なぜこれが本命か
----------------
fetch_schools_semarang.py の docstring に「Dapodik は座標を公開していない」と書いたが、
**それは Dapodik 本体の話で、Dukcapil が座標付きで再公開している**ことが判明した。

  https://gis.dukcapil.kemendagri.go.id/arcgis/rest/services/Hosted/
    Fasilitas_Pendidikan/FeatureServer/1        （レイヤ名 "education"）

  - `source` 列は "Website Kemendikbud" / "Website Kemdikbud" / "Website Pindai Dikti"
    ＝ **Kemendikbud（Dapodik）由来であって OSM 由来ではない**。
    → OSM と独立したソースなので、網羅性の相互検証に使える（ODbL の継承も及ばない）。
  - 全国 448,810 件。Semarang bbox で 3,078 件（OSM の 2,077 件より約 48% 多い）。
  - `tags` 列が "Education;School;Kindergarden" のように**校種を構造化**して持つ。
    OSM で校名パースに頼っていた段階判定（MAN 誤爆事故を起こした箇所）が不要になる。

API の作法
----------
  - `maxRecordCount` = 2000。**resultOffset でページングする**。
  - サービスの既定 SR は 3857 なので `outSR=4326` を明示して緯度経度で受け取る。
  - bbox 検索は `inSR=4326` を付ければ WGS84 の envelope をそのまま渡せる。

出力: data/semarang/dukcapil_schools_semarang.parquet
"""
import json
import os
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

# tags（"Education;School;Kindergarden" 形式）→ 段階。
# 名称パースより信頼できるので**こちらを優先**する。
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
    raise SystemExit(f"取得失敗: offset={offset}")


def level_from_tags(tags, name):
    """tags を第一、校名トークンを第二の手がかりに段階を決める。

    校名パースは "SD Negeri **Man**gunharjo" が略号 MAN に誤爆する事故を起こしたので
    （fetch_schools_semarang.py 参照）、構造化された tags があるならそちらを使う。
    """
    t = (tags or "").lower()
    for key, lv in TAG_LEVEL.items():
        if key in t:
            return lv
    # tags が曖昧なときだけ校名トークンに落とす（部分一致は使わない）
    import re
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
    print(f"\n取得 {len(rows):,} 件（bbox）")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.register("r", __import__("pandas").DataFrame(rows))
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    con.execute("""create table s as select * from r
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    n, = con.execute("select count(*) from s").fetchone()
    print(f"Kota Semarang 市域内 {n:,} 件")
    con.execute(f"copy s to '{OUT}' (FORMAT parquet)")
    print(f"出力: {OUT}")

    print("\n=== 段階別 ===")
    for row in con.execute(
            "select level, count(*) c from s group by 1 order by c desc").fetchall():
        print(f"  {row[0]:10s} {row[1]:>5,}")

    print("\n=== tags の実値（上位）===")
    for row in con.execute(
            "select tags, count(*) c from s group by 1 order by c desc limit 12").fetchall():
        print(f"  {str(row[0])[:52]:54s} {row[1]:>5,}")

    print("\n=== source 別 ===")
    for row in con.execute(
            "select source, count(*) c from s group by 1 order by c desc").fetchall():
        print(f"  {str(row[0]):28s} {row[1]:>5,}")

    # OSM との突合（独立ソースなので網羅性の相互検証になる）
    osm = f"{OUT_DIR}/osm_schools_semarang.parquet"
    if os.path.exists(osm):
        print("\n=== OSM との比較（市域内）===")
        con.execute(f"create table o as select * from read_parquet('{osm}')")
        no, = con.execute("select count(*) from o").fetchone()
        print(f"  Dukcapil {n:,} 件 / OSM {no:,} 件")
        # 100m 以内に相手がいるか（≒同一施設）
        con.execute("""create table pair as
          select count(*) filter (where hit) m, count(*) t from (
            select exists (select 1 from o
              where 111320*sqrt(power(o.lat-s.lat,2)
                  + power((o.lon-s.lon)*cos(radians(s.lat)),2)) <= 100) hit
            from s)""")
        m, t = con.execute("select m, t from pair").fetchone()
        print(f"  Dukcapil のうち OSM に 100m 以内の対応あり: {m:,}/{t:,} = {m/t*100:.1f}%")
        print(f"  → Dukcapil 独自（OSM に無い）: {t - m:,} 件")


if __name__ == "__main__":
    main()
