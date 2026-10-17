#!/usr/bin/env python3
"""
SMK visibility score for Kota Semarang: how well placed each vocational school is to sell
the output of its unit produksi / teaching factory (vehicle servicing, catering, printing,
salon, ...) to the public.

Prompted by a public complaint that SMK service units sit 'nyelempit' — tucked away in
side streets — so customers never find them. The score turns that into five measured
factors and a weighted sum. Weights are a judgement, so the map lets readers move them;
the defaults below are only a starting point.

Factors (each scaled 0–100)
---------------------------
  jangkauan  Customer reach: residents (WorldPop 2020) who can reach the school within
             10 minutes along the road network. Scaled against the 90th percentile of
             Semarang SMK, so 100 = "as good as the best-placed tenth".
  arteri     Distance to the nearest arterial/collector (trunk/primary/secondary).
             100 at <= 50 m, 0 at >= 800 m, linear between. Toll roads excluded: there
             is no frontage on a motorway.
  depan      Class of the road at the gate (nearest non-service drivable road). A school
             on a residential lane scores low even if an arterial is 300 m away —
             this is the 'nyelempit' measure in its most literal form.
  keramaian  Commercial activity: Overture places (confidence >= 0.5) within 500 m,
             scaled against the 90th percentile like jangkauan. A proxy for passers-by.
  transit    Distance to the nearest bus stop (incl. Trans Semarang shelters).
             100 at <= 100 m, 0 at >= 1,000 m.

Default weights: jangkauan 35, arteri 25, depan 15, keramaian 15, transit 10.

SMK layer
---------
The combined school layer does not separate SMK: Dukcapil tags them 'College' (so they
land in level='PT') and OSM tags them school/SMA, and because the levels differ the two
copies were **never merged** — most SMK appear twice. Here Dukcapil is the list of record
(official names) and each school takes its coordinate from OSM, else Overture, matched by
name (similarity >= 0.9 within 4 km, or >= 0.75 within 500 m). **Dukcapil coordinates
drift by up to ~3 km** while the names are exact, and the frontage factors are only as good
as the point. Schools with no OSM/Overture match keep the Dukcapil point and are flagged
lokasi='perkiraan'; the map draws them hollow. OSM-only SMK are added.
Result 2026-10-17: 94 SMK — 55 OSM / 24 Overture / 15 perkiraan.

Travel time
-----------
Motorbike-like effective speeds per road class (including junction delay), oneway
respected, computed to the school (reverse graph). Population cells snap to the nearest
node of the largest connected component if within 250 m; cells further away (no mapped
road) do not count — an understatement where OSM road coverage is thin.

Inputs : data/semarang/schools_semarang_combined.parquet
         data/semarang/osm_roads_semarang.json, osm_transit_semarang.parquet
         data/semarang/overture_semarang_all.parquet
         data/semarang/worldpop_semarang_2020.tif   (clip of WorldPop idn_ppp_2020_constrained)
         data/semarang/semarang_boundary_poly.geojson, semarang_kecamatan.geojson
Output : $ATLAS_DATA/smk-visibility/{smk.geojson, jangkauan.geojson, ringkasan.json}
"""
import difflib
import json
import os
import re

import duckdb
import numpy as np
import rasterio
from pyproj import Transformer
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
import shapely
from shapely import STRtree
from shapely.geometry import LineString, MultiPoint, Point, mapping, shape
from shapely.ops import transform

D = "data/semarang"
OUT = os.path.join(os.environ.get("ATLAS_DATA", "atlas/public/data"), "smk-visibility")

WEIGHTS = {"jangkauan": 35, "arteri": 25, "depan": 15, "keramaian": 15, "transit": 10}
REACH_MIN = 10           # minutes, for the jangkauan factor
SNAP_POP_M = 250         # population cell -> road node
COMMERCIAL_R = 500       # m, for the keramaian factor

ARTERIAL = {"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link"}
TOLL = {"motorway", "motorway_link"}
# Effective km/h, junction delay included — closer to what a motorbike averages in town
# than to the posted limit.
SPEED = {"trunk": 35, "primary": 30, "secondary": 27, "tertiary": 22, "unclassified": 18,
         "residential": 15, "road": 15, "living_street": 10, "service": 10}
# Score for the road class at the gate
FRONT = {"trunk": 100, "primary": 100, "secondary": 85, "tertiary": 65, "unclassified": 45,
         "residential": 30, "road": 30, "living_street": 15, "service": 10}

to_m = Transformer.from_crs(4326, 32749, always_xy=True).transform     # UTM 49S
to_ll = Transformer.from_crs(32749, 4326, always_xy=True).transform


def base(hw):
    return hw.removesuffix("_link")


def lin(d, full, zero):
    """100 at d <= full, 0 at d >= zero, linear between."""
    return float(np.clip((zero - d) / (zero - full), 0, 1) * 100)


def norm(name):
    s = re.sub(r"[^A-Z0-9 ]", " ", name.upper())
    s = re.sub(r"\bSMKN\b", "SMK NEGERI", s)
    s = re.sub(r"\bSMKS\b", "SMK", s)
    s = re.sub(r"\bJATENG\b", "JAWA TENGAH", s)
    s = re.sub(r"\bPL\b", "PANGUDI LUHUR", s)
    s = re.sub(r"\b0+(\d)", r"\1", s)                      # "NEGERI 03" -> "NEGERI 3"
    s = re.sub(r"\b(KOTA|SEMARANG|DI)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ratio(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def match(name, x, y, cands, taken):
    """Best candidate (name, lon, lat, x, y) for a school, or None.

    ** Dukcapil coordinates drift by up to ~3 km from the campus while the names are
       exact (checked 2026-10-17: 'SMK BAGIMU NEGERIKU' sits 2.2 km from the OSM building),
       so a strong name match is accepted over a wide radius. A pure-distance rule is not:
       several campuses (Theresiana, PL) host more than one SMK side by side."""
    best, best_r = None, 0.0
    for i, c in enumerate(cands):
        if i in taken:
            continue
        d = np.hypot(c[3] - x, c[4] - y)
        r = ratio(name, c[0])
        if ((r >= 0.9 and d <= 4000) or (r >= 0.75 and d <= 500)) and r > best_r:
            best, best_r = i, r
    return best


# ---------------------------------------------------------------- 1. SMK layer
con = duckdb.connect()
SMK_RE = "'^\\s*SMK|SEKOLAH MENENGAH KEJURUAN'"
rows = con.execute(f"""
  select name, src, lon, lat from read_parquet('{D}/schools_semarang_combined.parquet')
  where regexp_matches(upper(name), {SMK_RE})""").fetchall()
ovr = con.execute(f"""
  select name, lon, lat from read_parquet('{D}/overture_semarang_all.parquet')
  where regexp_matches(upper(name), {SMK_RE}) and confidence >= 0.5""").fetchall()
with_xy = lambda rs: [(r[0], r[-2], r[-1], *to_m(r[-2], r[-1])) for r in rs]
osm = with_xy([r for r in rows if r[1] == "osm"])
duk = with_xy([r for r in rows if r[1] == "dukcapil"])
ovr = with_xy(ovr)

# Dukcapil is the list of record (official names, existence); the coordinate comes from
# OSM, then Overture, and only as a last resort from Dukcapil itself ('perkiraan').
smk, used_o, used_v = [], set(), set()
for k in duk:
    i = match(k[0], k[3], k[4], osm, used_o)
    if i is not None:
        used_o.add(i)
        smk.append({"nama": k[0], "lokasi": "osm", "lon": osm[i][1], "lat": osm[i][2]})
        continue
    j = match(k[0], k[3], k[4], ovr, used_v)
    if j is not None:
        used_v.add(j)
        smk.append({"nama": k[0], "lokasi": "overture", "lon": ovr[j][1], "lat": ovr[j][2]})
        continue
    smk.append({"nama": k[0], "lokasi": "perkiraan", "lon": k[1], "lat": k[2]})
# SMK that OSM knows but Dukcapil does not
smk += [{"nama": o[0], "lokasi": "osm", "lon": o[1], "lat": o[2]}
        for i, o in enumerate(osm) if i not in used_o]

# Same normalised name within 300 m = one school listed twice in one source
dedup = []
for s in smk:
    if any(norm(s["nama"]) == norm(t["nama"]) and
           np.hypot(*(np.array(to_m(s["lon"], s["lat"])) - to_m(t["lon"], t["lat"]))) < 300
           for t in dedup):
        continue
    dedup.append(s)

with open(f"{D}/semarang_boundary_poly.geojson") as f:
    city = shape(json.load(f)["features"][0]["geometry"])
shapely.prepare(city)
smk = [s for s in dedup if city.contains(Point(s["lon"], s["lat"]))]
n_src = {k: sum(s["lokasi"] == k for s in smk) for k in ("osm", "overture", "perkiraan")}
print(f"SMK: dukcapil {len(duk)}, osm {len(osm)}, overture {len(ovr)} "
      f"-> {len(smk)} unique in city; coordinate from {n_src}")
for s in smk:
    s["status"] = "Negeri" if re.search(r"\bNEGERI\b|\bSMKN\b", s["nama"].upper()) else "Swasta"
    s["x"], s["y"] = to_m(s["lon"], s["lat"])
P = np.array([[s["x"], s["y"]] for s in smk])

# ---------------------------------------------------------------- 2. roads
with open(f"{D}/osm_roads_semarang.json") as f:
    roads = json.load(f)
nid = list(roads["nodes"].keys())
idx = {k: i for i, k in enumerate(nid)}
ll = np.array([roads["nodes"][k] for k in nid])
NX, NY = to_m(ll[:, 0], ll[:, 1])
NXY = np.column_stack([NX, NY])

art_geom, art_name, front_geom, front_cls = [], [], [], []
eu, ev, ew = [], [], []
for w in roads["ways"]:
    hw = w["highway"]
    if hw in TOLL:
        continue
    ii = [idx[str(n)] for n in w["nodes"] if str(n) in idx]
    if len(ii) < 2:
        continue
    line = LineString(NXY[ii])
    if hw in ARTERIAL:
        art_geom.append(line)
        art_name.append(w["name"])
    if hw != "service":
        front_geom.append(line)
        front_cls.append(base(hw))
    a, b = np.array(ii[:-1]), np.array(ii[1:])
    t = np.hypot(*(NXY[b] - NXY[a]).T) / (SPEED.get(base(hw), 15) / 3.6)   # seconds
    ow = w["oneway"]
    if ow in ("yes", "1", "true"):
        pairs = [(a, b)]
    elif ow == "-1":
        pairs = [(b, a)]
    else:
        pairs = [(a, b), (b, a)]
    for u, v in pairs:
        eu.append(u); ev.append(v); ew.append(t)

art_tree, front_tree = STRtree(art_geom), STRtree(front_geom)
pts = [Point(p) for p in P]
for s, p in zip(smk, pts):
    i = art_tree.query_nearest(p)[0]
    s["d_arteri"] = round(art_geom[i].distance(p))
    s["arteri"] = art_name[i]
    j = front_tree.query_nearest(p)[0]
    s["kelas_depan"] = front_cls[j]

# ---------------------------------------------------------------- 3. network reach
N = len(nid)
u, v, w = (np.concatenate(x) for x in (eu, ev, ew))
# Reverse graph (travel *to* the school). Duplicate edges would be summed by csr, so
# keep the fastest of each (v, u) pair first.
order = np.lexsort((w, u, v))
u, v, w = u[order], v[order], w[order]
keep = np.ones(len(u), bool)
keep[1:] = (v[1:] != v[:-1]) | (u[1:] != u[:-1])
G = csr_matrix((w[keep], (v[keep], u[keep])), shape=(N, N))

_, lab = connected_components(G, directed=True, connection="weak")
main = lab == np.bincount(lab).argmax()
main_idx = np.flatnonzero(main)
node_tree = cKDTree(NXY[main_idx])

with rasterio.open(f"{D}/worldpop_semarang_2020.tif") as r:
    pop = np.asarray(r.read(1))
    rr, cc = np.nonzero(pop > 0)
    lon, lat = rasterio.transform.xy(r.transform, rr, cc)
    vals = pop[rr, cc].astype(float)
cx, cy = to_m(np.array(lon), np.array(lat))
cell_in_city = shapely.contains_xy(city, np.array(lon), np.array(lat))
dist, near = node_tree.query(np.column_stack([cx, cy]))
ok = dist <= SNAP_POP_M
node_pop = np.zeros(N)
np.add.at(node_pop, main_idx[near[ok]], vals[ok])
print(f"population: {vals[cell_in_city].sum():,.0f} in city cells; "
      f"{vals[ok].sum() / vals.sum() * 100:.1f}% of bbox population snapped to the network")

_, src_near = node_tree.query(P)
src = main_idx[src_near]
reach_polys = []
for c0 in range(0, len(src), 20):
    print(f"  travel times {c0}/{len(src)}")
    T = dijkstra(G, indices=src[c0:c0 + 20], limit=15 * 60 + 1)
    for k, row in enumerate(T):
        s = smk[c0 + k]
        for m in (5, 10, 15):
            s[f"pop{m}"] = int(node_pop[row <= m * 60].sum())
        # Reached nodes thinned to a 100 m grid first: buffering tens of thousands of
        # raw nodes per school is what makes this step slow, and adds nothing visible.
        reached = np.unique(np.round(NXY[row <= REACH_MIN * 60] / 100) * 100, axis=0)
        poly = MultiPoint(reached).buffer(150, quad_segs=4).simplify(40)
        reach_polys.append(transform(to_ll, poly))

# ---------------------------------------------------------------- 4. commercial + transit
ov = con.execute(f"""select lon, lat from read_parquet('{D}/overture_semarang_all.parquet')
                     where confidence >= 0.5""").fetchnumpy()
ov_tree = cKDTree(np.column_stack(to_m(ov["lon"], ov["lat"])))
tr = con.execute(f"select lon, lat from read_parquet('{D}/osm_transit_semarang.parquet')"
                 ).fetchnumpy()
tr_tree = cKDTree(np.column_stack(to_m(tr["lon"], tr["lat"])))
d_halte, _ = tr_tree.query(P)
for s, p, dh in zip(smk, P, d_halte):
    s["n500"] = len(ov_tree.query_ball_point(p, COMMERCIAL_R))
    s["d_halte"] = round(float(dh))

# ---------------------------------------------------------------- 5. scores
p90_pop = np.percentile([s[f"pop{REACH_MIN}"] for s in smk], 90)
p90_poi = np.percentile([s["n500"] for s in smk], 90)
for s in smk:
    s["s_jangkauan"] = round(min(s[f"pop{REACH_MIN}"] / p90_pop, 1) * 100)
    s["s_arteri"] = round(lin(s["d_arteri"], 50, 800))
    s["s_depan"] = FRONT[s["kelas_depan"]]
    s["s_keramaian"] = round(min(s["n500"] / p90_poi, 1) * 100)
    s["s_transit"] = round(lin(s["d_halte"], 100, 1000))
    s["skor"] = round(sum(WEIGHTS[k] * s[f"s_{k}"] for k in WEIGHTS) / sum(WEIGHTS.values()))

with open(f"{D}/semarang_kecamatan.geojson") as f:
    kec = [(k["properties"]["name"], shape(k["geometry"])) for k in json.load(f)["features"]]
for s in smk:
    s["kec"] = next((n for n, g in kec if g.contains(Point(s["lon"], s["lat"]))), None)

# ---------------------------------------------------------------- 6. write
os.makedirs(OUT, exist_ok=True)
order = sorted(range(len(smk)), key=lambda i: -smk[i]["skor"])
PROPS = ["nama", "status", "kec", "lokasi", "skor", "s_jangkauan", "s_arteri", "s_depan",
         "s_keramaian", "s_transit", "pop5", "pop10", "pop15", "d_arteri", "arteri",
         "kelas_depan", "n500", "d_halte"]
feats, rfeats = [], []
for rank, i in enumerate(order):
    s = smk[i]
    feats.append({"type": "Feature", "id": rank,
                  "properties": {"id": rank, **{k: s[k] for k in PROPS}},
                  "geometry": {"type": "Point",
                               "coordinates": [round(s["lon"], 6), round(s["lat"], 6)]}})
    g = json.loads(json.dumps(mapping(reach_polys[i])),
                   parse_float=lambda x: round(float(x), 5))
    rfeats.append({"type": "Feature", "properties": {"id": rank}, "geometry": g})


def dump(obj, name):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  {name:18s} {os.path.getsize(path) / 1024:>7.0f} KB")


print("writing:")
dump({"type": "FeatureCollection", "features": feats}, "smk.geojson")
dump({"type": "FeatureCollection", "features": rfeats}, "jangkauan.geojson")

d_art = np.array([s["d_arteri"] for s in smk])
side = [s for s in smk if s["kelas_depan"] in ("residential", "road", "living_street")]
nyelempit = [s for s in side if s["d_arteri"] > 300]
by_kec = {}
for s in smk:
    by_kec.setdefault(s["kec"] or "—", []).append(s["skor"])
summary = {
    "total_smk": len(smk),
    "sumber": n_src,
    "negeri": sum(s["status"] == "Negeri" for s in smk),
    "median_d_arteri": int(np.median(d_art)),
    "persen_arteri_300": round(float((d_art > 300).mean() * 100), 1),
    "smk_jalan_lingkungan": len(side),
    "smk_nyelempit": len(nyelempit),
    "persen_nyelempit": round(len(nyelempit) / len(smk) * 100, 1),
    "median_pop10": int(np.median([s["pop10"] for s in smk])),
    "bobot": WEIGHTS,
    "skala": {"p90_pop10": int(p90_pop), "p90_n500": int(p90_poi),
              "arteri_m": [50, 800], "transit_m": [100, 1000], "depan": FRONT},
    "kecamatan": sorted([{"nama": k, "smk": len(v), "skor": round(float(np.mean(v)))}
                         for k, v in by_kec.items()], key=lambda r: -r["skor"]),
}
dump(summary, "ringkasan.json")

print(f"\n  {len(smk)} SMK; median distance to an arterial/collector {summary['median_d_arteri']} m;"
      f" {summary['persen_arteri_300']}% further than 300 m")
print(f"  {len(side)} front onto a residential/living street; {len(nyelempit)} "
      f"({summary['persen_nyelempit']}%) of those are also > 300 m from an arterial")
print(f"  median residents within {REACH_MIN} min: {summary['median_pop10']:,}")
