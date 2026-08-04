#!/usr/bin/env python3
"""
Generate figures for the manuscript (docs/semarang/gambar/).

The target is a SINTA-accredited journal, so:
  - **labels are in Bahasa Indonesia**
  - 300 dpi raster plus vector (PDF)
  - **must survive greyscale printing** — information is never carried by colour alone;
    marker shape and hatching vary too
  - decimal separator is a comma, per Indonesian convention

geopandas is deliberately not used (no extra dependency). GeoJSON is read directly and drawn
with matplotlib patches. At latitude -7 the aspect ratio is corrected by 1/cos(lat).

Output:
  Gambar1_peta_sebaran.(png|pdf)      satuan pendidikan by radius status + minimarket
  Gambar2_cakupan_kecamatan.(png|pdf) data coverage per kecamatan — evidence of spatial bias
  Gambar3_distribusi_jarak.(png|pdf)  distance to nearest minimarket
  Gambar4_kelengkapan_sumber.(png|pdf) source coverage against the estimated true count
"""
import csv
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ATLAS = "atlas/public/data"
OUT = "docs/semarang/gambar"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.linewidth": 0.6,
    "axes.edgecolor": "#333333",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})

# Colourblind-safe choices; marker shape also differs so greyscale prints stay readable.
C_KENA = "#c0392b"     # has a minimarket within 200 m
C_AMAN = "#1b7a3d"     # none within 200 m
C_TOKO = "#2166ac"
LAT0 = -6.99
ASPECT = 1.0 / math.cos(math.radians(LAT0))

# Indonesian decimal comma on axes
ID_NUM = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"))
    plt.close(fig)
    print(f"  {name}.png / .pdf")


def rings_of(geom):
    return (geom["coordinates"] if geom["type"] == "Polygon"
            else [r for p in geom["coordinates"] for r in p])


def draw_kecamatan(ax, kec, **kw):
    for ft in kec["features"]:
        for ring in rings_of(ft["geometry"]):
            ax.add_patch(MplPolygon(ring, closed=True, **kw))


def scalebar(ax, x0, y0, km=5):
    """Scale bar under the equirectangular approximation: at lat -7,
    one degree of longitude is about 111,320 * cos(7 deg) metres."""
    dx = km * 1000 / (111320 * math.cos(math.radians(LAT0)))
    ax.plot([x0, x0 + dx], [y0, y0], color="#222", lw=2.2, solid_capstyle="butt")
    for x in (x0, x0 + dx):
        ax.plot([x, x], [y0, y0 + dx * 0.06], color="#222", lw=1)
    ax.text(x0 + dx / 2, y0 + dx * 0.10, f"{km} km", ha="center", va="bottom", fontsize=7.5)


def north(ax, x, y, s=0.012):
    ax.annotate("", xy=(x, y + s), xytext=(x, y),
                arrowprops=dict(arrowstyle="-|>", color="#222", lw=1.2))
    ax.text(x, y + s * 1.15, "U", ha="center", va="bottom",
            fontsize=8.5, fontweight="bold")


print("Membuat gambar:")

kec = load(f"{ATLAS}/kecamatan.geojson")
sek = load(f"{ATLAS}/sekolah.geojson")
tok = load(f"{ATLAS}/minimarket.geojson")

# ---------------- Gambar 1: distribution ----------------
fig, ax = plt.subplots(figsize=(7.2, 6.4))
draw_kecamatan(ax, kec, facecolor="#f6f7f8", edgecolor="#b8bfc7", lw=0.5)

ax.scatter([f["geometry"]["coordinates"][0] for f in tok["features"]],
           [f["geometry"]["coordinates"][1] for f in tok["features"]],
           s=5, c=C_TOKO, marker="s", linewidths=0, alpha=0.55, zorder=2)

kena = [f for f in sek["features"] if f["properties"]["n200"] > 0]
aman = [f for f in sek["features"] if f["properties"]["n200"] == 0]
for grp, col, mk, sz in ((aman, C_AMAN, "o", 7), (kena, C_KENA, "^", 11)):
    ax.scatter([f["geometry"]["coordinates"][0] for f in grp],
               [f["geometry"]["coordinates"][1] for f in grp],
               s=sz, c=col, marker=mk, linewidths=0.25, edgecolors="white", zorder=3)

ax.set_aspect(ASPECT)
ax.set_xticks([]); ax.set_yticks([])
for sp in ax.spines.values():
    sp.set_visible(False)
scalebar(ax, 110.235, -7.16)
# North arrow goes top-right, inside the frame, so it cannot collide with the legend.
north(ax, 110.545, -6.985)
ax.legend(handles=[
    Line2D([], [], marker="^", color="none", markerfacecolor=C_KENA, markersize=6.5,
           label=f"Satuan pendidikan dengan minimarket ≤200 m (n={len(kena):,})".replace(",", ".")),
    Line2D([], [], marker="o", color="none", markerfacecolor=C_AMAN, markersize=5,
           label=f"Satuan pendidikan tanpa minimarket ≤200 m (n={len(aman):,})".replace(",", ".")),
    Line2D([], [], marker="s", color="none", markerfacecolor=C_TOKO, markersize=5,
           label=f"Minimarket (yang dapat diterbitkan, n={len(tok['features'])})"),
], loc="upper left", frameon=False, fontsize=7.6, handletextpad=0.4,
    borderpad=0.2, labelspacing=0.5)
ax.set_title("Sebaran satuan pendidikan menurut keberadaan minimarket\n"
             "dalam radius 200 m, Kota Semarang", fontsize=10, pad=8)
save(fig, "Gambar1_peta_sebaran")

# ---------------- Gambar 2: coverage per kecamatan ----------------
cov = {}
with open("docs/semarang/verify_coverage-spatial-bias.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["coverage_ratio"]:
            cov[r["kecamatan"]] = float(r["coverage_ratio"])

fig, (axm, axb) = plt.subplots(1, 2, figsize=(10.2, 5.4),
                               gridspec_kw={"width_ratios": [1, 1.05], "wspace": 0.28})
cmap = plt.get_cmap("YlOrRd_r")
vmin, vmax = 0.15, 0.85
for ft in kec["features"]:
    v = cov.get(ft["properties"].get("name"))
    fc = cmap((v - vmin) / (vmax - vmin)) if v is not None else "#e9ecef"
    for ring in rings_of(ft["geometry"]):
        axm.add_patch(MplPolygon(ring, closed=True, facecolor=fc,
                                 edgecolor="white", lw=0.7))
axm.set_aspect(ASPECT)
axm.autoscale_view()
axm.set_xticks([]); axm.set_yticks([])
for sp in axm.spines.values():
    sp.set_visible(False)
axm.set_title("Cakupan basis data POI per kecamatan", fontsize=9.5, pad=6)

# Colour bar goes **horizontally beneath the map**. Placed vertically alongside it, the bar
# and its label ran straight through the kecamatan labels of the right-hand chart.
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
cb = fig.colorbar(sm, ax=axm, orientation="horizontal",
                  fraction=0.045, pad=0.04, aspect=32)
cb.set_label("Cakupan (basis data ÷ Google Places)", fontsize=8)
cb.ax.tick_params(labelsize=7.5)
cb.ax.xaxis.set_major_formatter(ID_NUM)

rows = sorted(cov.items(), key=lambda x: x[1])
axb.barh([r[0] for r in rows], [r[1] for r in rows],
         color=[cmap((v - vmin) / (vmax - vmin)) for _, v in rows],
         edgecolor="#8d99a6", lw=0.4, height=0.72)
axb.axvline(0.42, color="#c0392b", ls="--", lw=1.1)
axb.text(0.43, -0.65, "rata-rata kota 0,42", color="#c0392b", fontsize=7.5, va="bottom")
axb.set_xlim(0, 0.9)
axb.set_xlabel("Cakupan basis data (proporsi)", fontsize=8.5)
axb.xaxis.set_major_formatter(ID_NUM)
axb.tick_params(labelsize=7.8)
axb.spines[["top", "right"]].set_visible(False)
axb.set_title("Rentang 0,19–0,79 — ketidaklengkapan tidak acak", fontsize=9.5, pad=6)
save(fig, "Gambar2_cakupan_kecamatan")

# ---------------- Gambar 3: distance distribution ----------------
all_d = [f["properties"]["dmin"] for f in sek["features"]
        if f["properties"]["dmin"] is not None]
d = [x for x in all_d if x <= 1200]
med = sorted(all_d)[len(all_d) // 2]

fig, ax = plt.subplots(figsize=(7.2, 3.9))
ax.hist(d, bins=48, range=(0, 1200), color="#9fb8cd", edgecolor="white", lw=0.4)
ax.axvline(200, color="#c0392b", lw=1.6)
ax.axvline(500, color="#e08a2e", lw=1.6, ls="--")
ax.axvline(med, color="#111", lw=1.2, ls=":")
ymax = ax.get_ylim()[1]
ax.text(208, ymax * 0.96, "200 m\nlarangan jual", color="#c0392b",
        fontsize=8, va="top", fontweight="bold")
ax.text(508, ymax * 0.96, "500 m\nlarangan iklan", color="#e08a2e",
        fontsize=8, va="top", fontweight="bold")
ax.text(med + 10, ymax * 0.52, f"median {med:.0f} m", fontsize=8, color="#111")
ax.set_xlabel("Jarak satuan pendidikan ke minimarket terdekat (m)", fontsize=9)
ax.set_ylabel("Jumlah satuan pendidikan", fontsize=9)
ax.set_title(f"Distribusi jarak ke minimarket terdekat "
             f"(n = {len(all_d):,})".replace(",", "."), fontsize=10, pad=7)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "Gambar3_distribusi_jarak")

# ---------------- Gambar 4: source completeness ----------------
est = {}
with open("docs/semarang/verify_chain-truth-estimate.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        est[r["chain"]] = r

fig, ax = plt.subplots(figsize=(7.2, 3.8))
chains = list(est)
xs = range(len(chains))
w = 0.26
vals = {
    "Overture ∪ OSM": [int(est[c]["master_n"]) for c in chains],
    "Google Places": [int(est[c]["google_n"]) for c in chains],
    "Estimasi (Chapman)": [int(est[c]["est_true"]) for c in chains],
}
for i, ((lab, v), c, h) in enumerate(
        zip(vals.items(), ["#b8c4cf", "#5b8db8", "#1f4e79"], ["///", "", ""])):
    b = ax.bar([x + (i - 1) * w for x in xs], v, w, label=lab,
               color=c, edgecolor="#33414d", lw=0.5, hatch=h)
    ax.bar_label(b, fontsize=7.5, padding=1.5)
# Coverage percentage sits directly under the bar it describes (the hatched one).
for j, c in enumerate(chains):
    pct = float(est[c]["master_coverage"]) * 100
    ax.annotate(f"{pct:.0f}%".replace(".", ","), xy=(j - w, 0),
                xytext=(0, -16), textcoords="offset points", ha="center",
                fontsize=8, color="#c0392b", fontweight="bold")
ax.set_xticks(list(xs)); ax.set_xticklabels(chains, fontsize=9)
ax.tick_params(axis="x", pad=18)
ax.set_ylabel("Jumlah gerai", fontsize=9)
ax.set_ylim(0, 600)
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title("Kelengkapan sumber data terhadap estimasi jumlah sebenarnya",
             fontsize=10, pad=7)
ax.spines[["top", "right"]].set_visible(False)
save(fig, "Gambar4_kelengkapan_sumber")

print(f"\nSelesai → {OUT}/")
