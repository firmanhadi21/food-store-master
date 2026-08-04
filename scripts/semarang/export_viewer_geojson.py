#!/usr/bin/env python3
"""
公開マップ用の GeoJSON を書き出す（atlas/public/data/）。

PMTiles を使わない理由
----------------------
日本版ビューアは全国 10 万点規模なので tippecanoe → PMTiles が要る。Semarang は
学校 2,765 + 店舗 1,388 = 4 千点規模で、GeoJSON なら合計数百 KB に収まる。
ビルドに tippecanoe を要求しないほうが再現性が高いので**素の GeoJSON**にする。

★ 対象とする「satuan pendidikan」の範囲（2026-08-04 に条文で確定）
--------------------------------------------------------------
PP 28/2024 **Pasal 434(1)(e)**:
  「dalam radius 200 (dua ratus) meter dari satuan pendidikan dan tempat bermain anak」
**Penjelasan Pasal 518 Ayat (1)（p.570）** — PP 全体で唯一の satuan pendidikan の定義:
  「Satuan pendidikan antara lain pendidikan anak usia dini, sekolah/madrasah,
    pesantren, perguruan tinggi, atau nama lain yang sejenis dengan pendidikan formal.」

→ **PAUD/TK を含む。madrasah・pesantren・perguruan tinggi も含む。**
  したがって当初の集合A（SD/SMP/SMA のみ）は**法的に過小**であり、TK/PAUD/PT を
  含めた集合が正しい。informal（learning center 等）は「pendidikan formal と同種」と
  言えないので除外する。

  「tempat bermain anak」について: 条文は satuan pendidikan と並べて挙げるが、これは
  一般の児童公園ではなく **kelompok bermain（KB）＝ PAUD の一形態**を指す（現地での用法）。
  KB は Dapodik の PAUD 区分（TK 856 + KB 278 + TPA 31 + SPS 274）に含まれ、
  本レイヤの level='TK' に入っているので**すでに対象に含まれている**。別レイヤは不要。

  未対応（過小評価として明記する）:
   - **pesantren** は独立したレイヤとして持っていない（一部は madrasah として混在）

出力
----
  sekolah.geojson    satuan pendidikan（TK/PAUD・SD・SMP・SMA・SLB・PT）
                     属性: nama, jenjang, n200（200m 以内の minimarket 数）, n500
  minimarket.geojson ミニマーケット（best-available 層）
  kecamatan.geojson  行政区界（集計表示用）
  ringkasan.json     kecamatan 別の集計 + 全体サマリ

★ 個別の店舗名は出すが「違反」とは書かない。近接は法的判断ではない（doc §4）。
  集計は kecamatan 単位。個別事業者を名指しで糾弾する作りにはしない。
"""
import json
import os

import duckdb

D = "data/semarang"
OUT = "atlas/public/data"
R_SALES, R_ADS = 200, 500

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")

# 条文の定義に該当する校種。'informal'（learning center 等）と 'unknown' は除く。
SATUAN = "('TK','SD','SMP','SMA','SLB','PT')"
con.execute(f"""create table sc as
  select school_id, name, level,
         lon, lat, lon*111320*0.99255 x, lat*111320 y
  from read_parquet('{D}/schools_semarang_combined.parquet')
  where level in {SATUAN} and name is not null""")
con.execute(f"""create table st as
  select cat, name, src, lon, lat, lon*111320*0.99255 x, lat*111320 y
  from read_parquet('{D}/semarang_outlets_best.parquet')
  where cat = 'minimarket'""")

# 学校ごとの 200m/500m 圏内店舗数
con.execute(f"""create table sc2 as
  select s.*,
    (select count(*) from st t
      where sqrt(power(t.x-s.x,2)+power(t.y-s.y,2)) <= {R_SALES}) n200,
    (select count(*) from st t
      where sqrt(power(t.x-s.x,2)+power(t.y-s.y,2)) <= {R_ADS}) n500,
    (select round(min(sqrt(power(t.x-s.x,2)+power(t.y-s.y,2)))) from st t) dmin
  from sc s""")

os.makedirs(OUT, exist_ok=True)


def dump(rows, path, props):
    feats = [{
        "type": "Feature",
        "properties": {k: r[i] for i, k in enumerate(props)},
        "geometry": {"type": "Point", "coordinates": [round(r[-2], 6), round(r[-1], 6)]},
    } for r in rows]
    with open(os.path.join(OUT, path), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f,
                  ensure_ascii=False, separators=(",", ":"))
    print(f"  {path:22s} {len(feats):>6,} 件  "
          f"{os.path.getsize(os.path.join(OUT, path))/1024:>7.0f} KB")


print("出力:")
dump(con.execute("""select name, level, n200, n500, dmin, lon, lat
                    from sc2 order by n200 desc""").fetchall(),
     "sekolah.geojson", ["nama", "jenjang", "n200", "n500", "dmin"])

dump(con.execute("select name, src, lon, lat from st").fetchall(),
     "minimarket.geojson", ["nama", "sumber"])

# kecamatan 界（集計表示用）
kec_path = f"{D}/semarang_kecamatan.geojson"
if os.path.exists(kec_path):
    with open(kec_path, encoding="utf-8") as f:
        kec = json.load(f)
    with open(os.path.join(OUT, "kecamatan.geojson"), "w", encoding="utf-8") as f:
        json.dump(kec, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  kecamatan.geojson      {len(kec['features']):>6,} 件")
    con.execute(f"""create table kec as
      select name, geom::GEOMETRY geom from ST_Read('{kec_path}')""")
    agg = con.execute(f"""
      select k.name,
        (select count(*) from sc2 s where ST_Contains(k.geom, ST_Point(s.lon, s.lat))) n_sekolah,
        (select count(*) from sc2 s where ST_Contains(k.geom, ST_Point(s.lon, s.lat))
           and s.n200 > 0) n_kena,
        (select count(*) from st t where ST_Contains(k.geom, ST_Point(t.lon, t.lat))) n_toko
      from kec k order by 1""").fetchall()
else:
    agg = []

tot = con.execute("""select count(*), count(*) filter (where n200 > 0),
    round(median(dmin)) from sc2""").fetchone()
n_toko, = con.execute("select count(*) from st").fetchone()
# 店舗側の指標: 何割の minimarket が「販売禁止半径」の中にあるか。
# 学校側の指標より訴求力が強い（=市内の大半の店が規制圏内にある）。
toko_in, = con.execute(f"""select count(*) from st t where exists (
    select 1 from sc s
    where sqrt(power(t.x-s.x,2)+power(t.y-s.y,2)) <= {R_SALES})""").fetchone()

summary = {
    "total_sekolah": tot[0],
    "sekolah_dalam_200m": tot[1],
    "persen_sekolah": round(tot[1] / tot[0] * 100, 1),
    "median_jarak_m": int(tot[2]),
    "total_minimarket": n_toko,
    "minimarket_dalam_200m": toko_in,
    "persen_minimarket": round(toko_in / n_toko * 100, 1),
    "kecamatan": [{"nama": a[0], "sekolah": a[1], "kena": a[2],
                   "persen": round(a[2] / a[1] * 100, 1) if a[1] else None,
                   "toko": a[3]} for a in agg],
}
with open(os.path.join(OUT, "ringkasan.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=1)
print(f"  ringkasan.json         kecamatan {len(agg)} 区")

print(f"\n  学校 {tot[0]:,} 校中 {tot[1]:,} 校（{summary['persen_sekolah']}%）が "
      f"200m 以内に minimarket あり")
print(f"  最近隣 minimarket までの距離 中央値 {summary['median_jarak_m']}m")
