#!/usr/bin/env python3
"""
Kota Semarang 内に限定して Overture と OSM を突き合わせ、
「どちらを主ソースにすべきか」を日本版と同じ観点で判定する。

日本版の判定基準（docs/master/設計_食料品店マスター構築.md §1）:
  - カテゴリごとに最網羅の**単一ソース**を主に据える
  - 素朴な和集合は座標ズレで膨張する（日本のコンビニで 133%）
  → Semarang でも同じ検査をして、主ソースを決め直す。

出力: data/semarang/semarang_boundary_poly.geojson （Kota Semarang ポリゴン）
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
    """Kota Semarang の relation から outer リングを組み立ててポリゴン化する。

    Overpass の `out geom` は way 単位のバラバラな線分を返すので、端点を突き合わせて
    環に閉じる必要がある（この処理を省くと ST_Contains が使えない）。
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
    print(f"outer way {len(ways)} 本を環に組み立て")

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
            rings.append(cur)          # 閉じない断片はそのまま出す
            if not pending:
                break
            cur = pending.pop(0)

    rings = [r for r in rings if len(r) > 3]
    main = max(rings, key=len)          # 本体は最長リング
    if main[0] != main[-1]:
        main = main + [main[0]]
    gj = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"name": "Kota Semarang"},
        "geometry": {"type": "Polygon", "coordinates": [main]}}]}
    with open(POLY, "w") as f:
        json.dump(gj, f)
    print(f"出力: {POLY}  （頂点 {len(main):,}）")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


def main():
    fetch_polygon()
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    area, = con.execute(
        "select ST_Area_Spheroid(geom)/1e6 from kota").fetchone()
    print(f"Kota Semarang 面積 = {area:,.1f} km2 （公称 373.8 km2 と比較）")

    # bbox -> 市域にクリップ
    con.execute(f"""create table ov as
      select *, ST_Point(lon, lat) geom from {OV}
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    con.execute(f"""create table osm as
      select *, ST_Point(lon, lat) geom from {OSM}
      where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    nov, = con.execute("select count(*) from ov").fetchone()
    nosm, = con.execute("select count(*) from osm").fetchone()
    print(f"市域内: Overture 全POI {nov:,} 件 / OSM 食料品POI {nosm:,} 件")

    h("① カテゴリ別 件数比較（市域内）")
    print(f"  {'カテゴリ':22s} {'Overture':>10s} {'OSM':>8s}")
    pairs = [
        ("ミニマーケット", "category='convenience_store'",
         "shop='convenience'"),
        ("スーパー", "category='supermarket'", "shop='supermarket'"),
        ("食料品店(grocery)", "category='grocery_store'", "shop in ('grocery','general','kiosk')"),
        ("生鮮", "category in ('butcher_shop','seafood_market','fruits_and_vegetables')",
         "shop in ('butcher','seafood','fishmonger','greengrocer','dairy','farm')"),
        ("pasar(市場)", "category in ('farmers_market','market','public_market')",
         "amenity='marketplace'"),
        ("bakery", "category='bakery'", "shop='bakery'"),
    ]
    for label, ovf, osmf in pairs:
        a, = con.execute(f"select count(*) from ov where {ovf}").fetchone()
        b, = con.execute(f"select count(*) from osm where {osmf}").fetchone()
        print(f"  {label:22s} {a:>10,} {b:>8,}")

    h("② チェーン別 突合（実在店舗数が外部から検証できる唯一のカテゴリ）")
    print(f"  {'チェーン':14s} {'Overture':>9s} {'OSM':>7s} {'100m以内で一致':>14s} {'和集合':>8s}")
    for kw in ["alfamart", "indomaret", "alfamidi", "superindo"]:
        a, = con.execute(f"select count(*) from ov where name ilike '%{kw}%'").fetchone()
        b, = con.execute(f"select count(*) from osm where name ilike '%{kw}%'").fetchone()
        # 100m ≒ 0.0009 度（緯度）。赤道近傍なので経度補正はほぼ不要
        m, = con.execute(f"""
          select count(*) from osm o
          where o.name ilike '%{kw}%'
            and exists (select 1 from ov v where v.name ilike '%{kw}%'
                        and ST_DWithin(o.geom, v.geom, 0.0009))""").fetchone()
        union = a + b - m
        print(f"  {kw:14s} {a:>9,} {b:>7,} {m:>14,} {union:>8,}")

    h("③ 和集合の膨張率テスト（日本のコンビニは 133% に膨張して単一ソース採用の根拠になった）")
    a, = con.execute("select count(*) from ov where category='convenience_store'").fetchone()
    b, = con.execute("select count(*) from osm where shop='convenience'").fetchone()
    m, = con.execute("""
      select count(*) from osm o where o.shop='convenience'
        and exists (select 1 from ov v where v.category='convenience_store'
                    and ST_DWithin(o.geom, v.geom, 0.0009))""").fetchone()
    print(f"  Overture {a:,} / OSM {b:,} / 100m以内で一致 {m:,}")
    print(f"  → OSM 独自 {b - m:,} 件、和集合 {a + b - m:,} 件")
    print(f"  → OSM のうち Overture に無いもの = {(b - m) / b * 100:.1f}%")

    h("④ pasar（伝統市場）の詳細 — インドネシア固有・生鮮アクセスの主役")
    print("  OSM amenity=marketplace の名称サンプル:")
    for row in con.execute("""
        select name from osm where amenity='marketplace' and name is not null
        order by name limit 25""").fetchall():
        print(f"    {row[0]}")
    n_pasar, = con.execute("select count(*) from osm where amenity='marketplace'").fetchone()
    n_named, = con.execute(
        "select count(*) from osm where amenity='marketplace' and name is not null").fetchone()
    print(f"  計 {n_pasar} 件（うち名称あり {n_named}）")

    h("⑤ Overture の品質（日本との最大の違い＝原典構成）")
    print("  市域内 原典データセット構成:")
    for row in con.execute("""
        select ds, count(*) c from (select unnest(datasets) ds from ov)
        where ds != 'Overture' group by 1 order by c desc""").fetchall():
        print(f"    {str(row[0]):18s} {row[1]:>7,}")
    print("\n  ブランド付与率（チェーン店の名寄せ可能性に直結）:")
    for label, f in [("Overture convenience_store", "ov where category='convenience_store'"),
                     ("OSM shop=convenience", "osm where shop='convenience'")]:
        tot, br = con.execute(
            f"select count(*), count(brand{'_name' if 'ov ' in f else ''}) from {f}").fetchone()
        print(f"    {label:28s} {br:>5,}/{tot:<5,} = {br/tot*100:5.1f}%")


if __name__ == "__main__":
    main()
