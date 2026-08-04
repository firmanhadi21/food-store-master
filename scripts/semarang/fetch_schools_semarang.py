#!/usr/bin/env python3
"""
Kota Semarang の学校位置を取得する（tobacco-near-schools 分析用）。

PP 28/2024 の2つの規制半径を測るために学校レイヤが要る:
  - 販売禁止 200m（satuan pendidikan / 児童遊技場から）
  - 広告禁止 500m（教育施設から）

ソースの選択について
--------------------
第一候補は Dapodik（Kemendikdasmen）だが、**座標は Verval SP 側にあり公開 API から
取れない**。dapo.kemendikdasmen.go.id は bot に 403 を返す。referensi.data.kemdikbud.go.id
は NPSN と学校名は出すが緯度経度を出さない（既存スクレイパ egin10/dapodik も
NPSN・名称・件数のみ）。
→ **座標付きで即座に使えるのは OSM のみ**。Dapodik は名寄せによる網羅性検証に使う
   （NPSN と学校名の突合で「OSM に無い学校」を数える）。

出力: data/semarang/osm_schools_semarang.parquet
"""
import json
import os
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

# インドネシアの学校段階:
#   SD/MI  = 小学校（初等）      isced:level=1
#   SMP/MTs= 中学校（前期中等）  isced:level=2
#   SMA/SMK/MA = 高校（後期中等）isced:level=3
# 喫煙開始年齢の観点では SMP/SMA が主対象、曝露の観点では SD も対象になる。
QUERY = f"""
[out:json][timeout:180];
(
  nwr["amenity"="school"]({BBOX});
  nwr["amenity"="kindergarten"]({BBOX});
);
out center tags;
"""


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
            print(f"    失敗: {e}")
            time.sleep(3)
    raise SystemExit("Overpass 全滅")


# 校名トークン → 段階。**部分一致ではなく単語単位で判定する。**
#
# ★ 第1版は `if pat in n` の部分一致で書いたため "SD Negeri **Man**gunharjo" の
#   MANGUNHARJO が略号 MAN（Madrasah Aliyah Negeri）に誤爆し、小学校が高校になった。
#   マスター構築で griya / mart / toko が誤爆したのと同じ型のバグ。
#   インドネシアの校名は略号が独立した語として現れるので、トークン一致で十分かつ安全。
LEVEL_TOKENS = {
    "TK":  {"TK", "TKIT", "TKS", "PAUD", "RA", "KB", "BA", "TPA"},
    "SD":  {"SD", "SDN", "SDIT", "SDS", "SDI", "MI", "MIN", "MIS", "MIT"},
    "SMP": {"SMP", "SMPN", "SMPIT", "SMPS", "MTS", "MTSN", "MTSS"},
    "SMA": {"SMA", "SMAN", "SMAS", "SMAIT", "SMK", "SMKN", "SMKS",
            "MA", "MAN", "MAS", "MAK"},
}
# 判定順。長い段階名から見る必要はないが、SD より SMP/SMA を先に見ることで
# "SD" が "SDN" 以外に紛れる余地をなくす。
LEVEL_ORDER = ["TK", "SMA", "SMP", "SD"]


def school_level(name, tags):
    """学校名から段階を推定する。インドネシアは校名に段階の略号が入るので名称判定が効く。

    SDN/SD Negeri（小）, SMPN/MTs（中）, SMAN/SMK/MA（高）, TK/PAUD/RA（幼）。
    OSM の isced:level があればそちらを優先する。
    """
    isced = tags.get("isced:level")
    if isced:
        return {"0": "TK", "1": "SD", "2": "SMP", "3": "SMA"}.get(str(isced)[0], "unknown")
    if tags.get("amenity") == "kindergarten":
        return "TK"
    # 記号を区切りに落としてトークン化（"SDN-01" "SD/MI" 等に対応）
    tokens = {t for t in __import__("re").split(r"[^A-Z0-9]+", (name or "").upper()) if t}
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
    print(f"\nOSM 学校 {len(rows):,} 件（bbox）")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.register("r", __import__("pandas").DataFrame(rows))
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    con.execute("""create table s as
      select * from r
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    n, = con.execute("select count(*) from s").fetchone()
    print(f"Kota Semarang 市域内 {n:,} 件")

    con.execute(f"copy s to '{OUT}' (FORMAT parquet)")
    print(f"出力: {OUT}")

    print("\n=== 段階別 ===")
    for row in con.execute(
            "select level, count(*) c, count(name) named from s group by 1 order by c desc"
    ).fetchall():
        print(f"  {row[0]:8s} {row[1]:>4,}  (名称あり {row[2]:,})")

    print("\n=== 名称サンプル ===")
    for row in con.execute(
            "select level, name from s where name is not null order by random() limit 15"
    ).fetchall():
        print(f"  {row[0]:6s} {row[1]}")


if __name__ == "__main__":
    main()
