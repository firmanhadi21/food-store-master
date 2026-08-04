#!/usr/bin/env python3
"""
Write the GeoJSON the public map consumes (atlas/public/data/).

Why not PMTiles
---------------
The Japan viewer carries ~100k points nationally, so tippecanoe and PMTiles are necessary
there. Semarang is 2,765 institutions plus 1,388 outlets — a few hundred KB as plain GeoJSON.
Not requiring tippecanoe to build the site makes it far more reproducible, so **plain
GeoJSON** it is.

** Scope of "satuan pendidikan", settled against the regulation on 2026-08-04
PP 28/2024 **Pasal 434(1)(e)**:
  "dalam radius 200 (dua ratus) meter dari satuan pendidikan dan tempat bermain anak"
**Penjelasan Pasal 518 Ayat (1), p.570** — the only definition in the whole regulation:
  "Satuan pendidikan antara lain pendidikan anak usia dini, sekolah/madrasah,
   pesantren, perguruan tinggi, atau nama lain yang sejenis dengan pendidikan formal."

=> **PAUD/TK is included**, as are madrasah, pesantren and higher education. Treating
   SD/SMP/SMA as the set (the earlier approach) was legally too narrow. 'informal'
   (learning centres) is excluded, not being "sejenis dengan pendidikan formal".

On "tempat bermain anak": the article names it alongside satuan pendidikan, but it refers to
*kelompok bermain* — a form of PAUD — not a public playground. KB sits inside Dapodik's PAUD
figures (TK 856 + KB 278 + TPA 31 + SPS 274) and inside this layer's level='TK', so it is
**already covered**; no separate layer is needed.

Still missing (stated as an understatement): **pesantren** has no layer of its own, and some
are folded in as madrasah.

Output
------
  sekolah.geojson    satuan pendidikan (TK/PAUD, SD, SMP, SMA, SLB, PT)
                     properties: nama, jenjang, n200, n500, dmin
  minimarket.geojson minimarkets that may be republished (see the licence note below)
  kecamatan.geojson  district boundaries, for the aggregate table
  ringkasan.json     per-kecamatan aggregates plus the headline figures

** Individual store names are shown, but nothing is described as a violation. Proximity is
   not a legal finding. Aggregation is by kecamatan; the map is not built to name and shame
   individual businesses.
"""
import json
import os

import duckdb

D = "data/semarang"
OUT = "atlas/public/data"
R_SALES, R_ADS = 200, 500

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")

# Levels matching the statutory definition. 'informal' and 'unknown' are excluded.
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

# Outlets within each radius, per institution
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
    print(f"  {path:22s} {len(feats):>6,} features  "
          f"{os.path.getsize(os.path.join(OUT, path))/1024:>7.0f} KB")


print("writing:")
dump(con.execute("""select name, level, n200, n500, dmin, lon, lat
                    from sc2 order by n200 desc""").fetchall(),
     "sekolah.geojson", ["nama", "jenjang", "n200", "n500", "dmin"])

# ** Publish only points that may be redistributed — this matters.
#
#   The statistics (n200/n500/median) are computed over the best-available layer of 949
#   outlets, which includes Google Places records. **Google Places content may not be
#   redistributed** — the Maps Platform terms forbid storing or republishing content and
#   allow only limited caching. Derived figures such as "how many outlets are within 200 m
#   of this school" are statistics rather than Google content and may be published, but
#   **publishing the store points themselves as GeoJSON would breach the terms.**
#
#   => Points shown on the map are restricted to Overture (CDLA-Permissive-2.0) and OSM
#      (ODbL) provenance. The number of visible points therefore differs from the
#      statistical denominator, and the UI says so explicitly.
dump(con.execute("""select name, src, lon, lat from st
                    where src not like 'best:google%'""").fetchall(),
     "minimarket.geojson", ["nama", "sumber"])
n_pub, = con.execute(
    "select count(*) from st where src not like 'best:google%'").fetchone()

# District boundaries, for the aggregate table
kec_path = f"{D}/semarang_kecamatan.geojson"
if os.path.exists(kec_path):
    with open(kec_path, encoding="utf-8") as f:
        kec = json.load(f)
    with open(os.path.join(OUT, "kecamatan.geojson"), "w", encoding="utf-8") as f:
        json.dump(kec, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  kecamatan.geojson      {len(kec['features']):>6,} features")
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
# Outlet-side measure: what share of minimarkets sit inside the sales-prohibition radius.
# More arresting than the school-side figure, because it states the scale of the problem
# in terms of the city's own retail network.
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
    # Publishable points, fewer than the statistical denominator — see the licence note above
    "minimarket_ditampilkan": n_pub,
    "kecamatan": [{"nama": a[0], "sekolah": a[1], "kena": a[2],
                   "persen": round(a[2] / a[1] * 100, 1) if a[1] else None,
                   "toko": a[3]} for a in agg],
}
with open(os.path.join(OUT, "ringkasan.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=1)
print(f"  ringkasan.json         {len(agg)} kecamatan")

print(f"\n  {tot[1]:,} of {tot[0]:,} institutions ({summary['persen_sekolah']}%) "
      f"have a minimarket within {R_SALES} m")
print(f"  {toko_in:,} of {n_toko:,} minimarkets ({summary['persen_minimarket']}%) "
      f"lie within {R_SALES} m of one")
print(f"  median distance to nearest minimarket: {summary['median_jarak_m']} m")
