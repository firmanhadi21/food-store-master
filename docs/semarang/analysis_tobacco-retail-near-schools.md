# Analysis — Tobacco retail near schools, Kota Semarang (baseline)

> Baseline measurement of food/tobacco retail outlets within the buffers defined by
> **PP 28/2024**, computed from existing POI data before any field survey.
>
> Created: 2026-08-04 · Companions:
> [plan_warung-photo-survey.md](plan_warung-photo-survey.md) ·
> [assessment_warung-dataset-value.md](assessment_warung-dataset-value.md)
>
> **Not legal advice.** The regulatory summary in §1 is drawn from secondary sources and
> should be checked against the regulation text before being relied on. Distance results in §3
> measure *proximity*, not verified sales or legal violation — see §4.

---

## 0. Why this analysis

Of the applications considered for a Semarang warung layer
([assessment_warung-dataset-value.md](assessment_warung-dataset-value.md) §3), tobacco retail
around schools ranks highest on impact-per-effort, for a structural reason:

**In Indonesia the exposure variable is visible from the street.** Indonesia is not a party to
the WHO FCTC, tobacco advertising remains widespread, and warung frontages carry
manufacturer-supplied branded banners. The banners that would serve as *detection cues* in a
photo survey **are themselves the thing being measured**. No change to the planned fieldwork is
required — only to the analysis.

This document establishes what can be measured **without** fieldwork, so the marginal value of
the survey is quantified before it is funded.

---

## 1. PP 28/2024 — the regulatory basis

Government Regulation 28/2024, implementing UU 17/2023 (health omnibus law). Relevant provisions:

| Provision | Radius | Measured from |
|---|---|---|
| **Sale** of tobacco products prohibited | **200 m** | *satuan pendidikan* and children's playgrounds |
| **Advertising** prohibited | **500 m** | educational institutions |

Also introduced:

- Ban on ***rokok ketengan*** (single-stick sales) — the principal affordability pathway for youth
- Minimum purchase age raised **18 → 21**
- Complete ban on social media tobacco advertising
- Television advertising restricted to 22:00–05:00

### Implementation is contested

APRINDO (retail association) and AMLI (outdoor media association) have both formally objected,
arguing the radius provisions are unclear and were set without stakeholder consultation.

**This is favourable for the research, not a problem.** Compliance is politically live and no
party currently holds the outlet-level data needed to settle it.

### Two measurements, one survey

The two radii map onto two distinct field observations:

- **200 m** → does the outlet *sell* tobacco (visible display, ketengan jar)
- **500 m** → does the outlet *advertise* tobacco (banner presence, count, area, height)

Both are obtainable from the same photographs.

---

## 2. Data sources

### 2.1 Schools — two sources, both incomplete in different ways

**Dapodik itself does not publish coordinates.** Attempted and ruled out:

| Source | Result |
|---|---|
| `dapo.kemendikdasmen.go.id` | **403** — bot-blocked |
| `referensi.data.kemdikbud.go.id` | **Dead** — ministry renamed, domain retired |
| `referensi.data.kemendikdasmen.go.id` | **Live**, but aggregate counts per province and NPSN/name search only — **no coordinates** |
| Existing scrapers (`egin10/dapodik`) | Confirm NPSN, name, counts only |

Structural reason: **coordinates live in Verval SP, not Dapodik**, and Verval SP is authenticated
for school operators.

**However — Dukcapil republishes Kemendikbud data *with* coordinates**, via an ArcGIS
FeatureServer (`scripts/semarang/fetch_schools_dukcapil.py`):

```
https://gis.dukcapil.kemendagri.go.id/arcgis/rest/services/Hosted/
  Fasilitas_Pendidikan/FeatureServer/1        (layer "education", 448,810 national)
```

`source` values are *Website Kemendikbud* / *Website Kemdikbud* / *Website Pindai Dikti* —
**Kemendikbud-derived, independent of OSM**, so it is a genuine cross-validation source and
carries no ODbL inheritance.

> ⚠️ **But its coverage is regionally uneven and level-incomplete — verified by direct query:**
> - Within the Semarang bbox, `tags='Elementary School'` returns **0** and
>   `'Junior High School'` returns **0**, while nationally these hold **54,159** and **93,714**
>   records respectively.
> - `'Senior High School'` **does not exist as a tag anywhere nationally** (count 0; the 95,457
>   `High` matches are all Junior High).
>
> **Therefore Dukcapil contributes nothing to SD/SMP/SMA in Semarang.** Its value is confined to
> TK/PAUD and higher education.

**Combined layer** (`scripts/semarang/build_schools_combined.py`) — union, deduped at 100 m and
**only within the same level** (TK and SD share sites routinely; merging on proximity alone would
destroy real facilities, the same failure avoided in the store master with Alfamart/Indomaret):

| Level | Combined | osm | dukcapil |
|---|---:|---:|---:|
| TK / PAUD | 1,590 | 1,110 | **+480** |
| SD / MI | 507 | 507 | 0 |
| PT (higher ed) | 270 | 0 | 270 |
| SMA / SMK / MA | 153 | 152 | 1 |
| SMP / MTs | 145 | 145 | 0 |
| unknown | 175 | 103 | 72 |
| informal / SLB | 56 | 0 | 56 |
| **Total** | **2,896** | 2,017 | 879 |

**Consequence for this analysis:** school set **A (SD/SMP/SMA) is effectively OSM-only**, so
**its completeness remains unvalidated** — the open problem in §6. Dukcapil's contribution lands
entirely in set C.

> **Classifier bug worth recording.** The first version used substring matching and put
> `SD Negeri Mangunharjo` in SMA, because `MAN` (Madrasah Aliyah Negeri) matched inside
> `Mangunharjo`. Same failure mode as `griya` / `mart` / `toko` in the master build. Fixed with
> **token matching** on `[^A-Z0-9]+` splits. SMA fell 183 → 152, SD rose 480 → 507.

### 2.2 Outlets

`data/semarang/semarang_food_master.parquet` — 987 stores. Categories assumed to sell tobacco:

- **minimarket** (548) — Alfamart / Indomaret / Alfamidi. Tobacco sales effectively certain.
  **Coverage is ~50%, not "good" — see §2.3.**
- **toko_kelontong** (186) — **a floor, not a count.** Real number is orders of magnitude higher;
  small warung do not appear in Overture or OSM. This is the gap the survey exists to fill.

### 2.3 ⚠️ Chain ground-truth — the master holds only ~half the minimarkets

Validated against **Google Places API (New)** as an independent third source
(`scripts/semarang/fetch_chains_google_places.py`; 252 requests, ≈ US$8).

The official locators could not be used, and were **not** circumvented:

| Locator | Endpoint | Result |
|---|---|---|
| Alfamart / Alfagift | `webcommerce-gw.alfagift.id/v2/stores/coordinate/candidate-list` | **401** — requires account token |
| Indomaret / klikindomaret | `www.klikindomaret.com/webapi/api/store/*` | **403** — WAF-blocked |

Authenticating or defeating a WAF to harvest a store database would breach those companies'
terms of service. Google Places is a legitimate third-party alternative.

| Chain | Google | Master | Ratio | Matched @100 m | Google-only |
|---|---:|---:|---:|---:|---:|
| Alfamart | 330 | 182 | **0.55** | 141 | 189 |
| Indomaret | 454 | 216 | **0.48** | 198 | 256 |

**Google inflates somewhat, and this was checked rather than assumed:**

- Same-chain records within 50 m: **Alfamart 10.0%, Indomaret 24.9%** — real stores rarely sit
  that close, so Indomaret in particular is double-listed.
- Name variants confirm contamination: `ATM BCA Indomaret` (an ATM), `Sumber Alfaria Trijaya. PT
  (Alfamart)` (corporate entity), repeated names such as `Indomaret Klipang` ×2.

Discounting duplicate pairs gives roughly **Alfamart ~314 / Indomaret ~398**, leaving the master
at **~0.55 / ~0.54**. The master also holds stores Google lacks (41 Alfamart, 18 Indomaret
unmatched at 100 m), so a three-source union floors the true count near
**~350 Alfamart / ~420 Indomaret**.

> **This falsifies an earlier assumption in this document.** Chain minimarkets were expected to be
> the *well-covered* category because they are branded and mapped. They are at **~50%**.
> Overture ∪ OSM was the right call and still reaches only half.

**Known limitation:** `places.businessStatus` was not requested in the field mask, so
**permanently-closed stores are not filtered** and form part of Google's inflation. Re-running
with that field (≈ US$8) would tighten the estimate and **should be done before publishing these
figures**.

---

## 3. Results

Reproduce with `python3 scripts/semarang/analyze_tobacco_school_buffers.py`
→ `docs/semarang/検証_学校周辺タバコ販売_バッファ.csv`

### 3.1 Outlets within the 200 m sales-restriction radius

Sensitivity to whether *satuan pendidikan* includes TK/PAUD — an interpretation question that
materially changes the answer:

| School set | Schools | minimarket | share | toko_kelontong | share |
|---|---:|---:|---:|---:|---:|
| **A** SD/SMP/SMA | 805 | 256 / 548 | **46.7%** | 93 / 186 | 50.0% |
| **B** SMP/SMA only | 298 | 114 / 548 | 20.8% | 40 / 186 | 21.5% |
| **C** incl. TK/PAUD + all | 2,896 | 464 / 548 | **84.7%** | 145 / 186 | 78.0% |

Set C rose from 73.4% to 84.7% once Dukcapil's additional 480 TK/PAUD were included — the
interpretation question in §6.1 is therefore worth even more than it first appeared. Sets A and B
are unchanged, because Dukcapil adds no SD/SMP/SMA in Semarang.

### 3.2 Outlets within the 500 m advertising-restriction radius

School set A (SD/SMP/SMA):

| Outlet type | Within 500 m | Share |
|---|---:|---:|
| minimarket | 495 / 548 | **90.3%** |
| toko_kelontong | 163 / 186 | 87.6% |

**Essentially the entire chain minimarket network sits inside the advertising-restricted zone.**

### 3.3 Seen from the schools

Schools with a minimarket within 200 m:

| School set | Share |
|---|---:|
| A SD/SMP/SMA | 267 / 805 = **33.2%** |
| B SMP/SMA | 102 / 298 = 34.2% |
| C all levels | 965 / 2,896 = 33.3% |

Notably **stable at ~33% across all three definitions** — the share of schools with a minimarket
within 200 m does not depend on which levels are counted, even though the share of *outlets*
inside the radius (§3.1) swings from 20.8% to 84.7%. Schools and minimarkets are both distributed
along the same commercial streets.

### 3.4 Distance from school to nearest minimarket

SD/SMP/SMA, n = 774 (31 of 805 schools had no minimarket within the search window, so the true
median is marginally higher than shown):

| min | p25 | median | p75 | max |
|---:|---:|---:|---:|---:|
| 6 m | 150 m | **258 m** | 444 m | 2,096 m |

---

## 4. Caveats — required before quoting these figures

1. **Point-to-point, not boundary-to-boundary.** The regulation presumably measures from school
   grounds, not a centroid. Real buffers would be *larger*, so **these figures are likely
   underestimates.**
2. **Proximity is not verified sale.** Chain minimarkets certainly sell tobacco, but
   non-compliance is a legal determination, not a distance calculation.
   **Report as "outlets within the restricted radius", never as "violations".**
3. **School coordinates are OSM and unvalidated.** Validate a sample against imagery before
   publication; check completeness against Dapodik counts.
4. **Every outlet row is a floor — including minimarket.** §2.3 measured chain coverage at ~50%,
   so the absolute counts in §3.1–3.2 are roughly **half of reality**. The *shares* may survive if
   the missing stores are spatially random, but **that is now an assumption requiring a check**,
   not a given: if Overture and OSM miss stores preferentially in peripheral areas, the shares are
   biased too. Testing it needs the Google layer compared against the master **by kecamatan**.
5. **Transition provisions unchecked.** Whether PP 28/2024 grants existing outlets a compliance
   period is not established here and would change the interpretation of §3.1 entirely.

---

## 5. What fieldwork adds

The asymmetry between the two outlet types is the argument for the survey:

| | minimarket | toko_kelontong |
|---|---|---|
| POI coverage | **~50%** (measured, §2.3) | **Severely incomplete** |
| Baseline figures above | **Floor — roughly half of reality** | **Floor only** |
| Tobacco sale observable from POI | Inferred (chain policy) | **Not observable** |
| Advertising observable from POI | **No** | **No** |

Both columns are floors. The chain measurement in §2.3 makes the case for fieldwork *stronger*,
not weaker: if branded chains with national store locators are only half-captured by the best
available POI union, the informal layer cannot plausibly be better.

Neither outlet type has *advertising* data in any existing source. That is only obtainable by
photographing frontages — which is precisely what
[plan_warung-photo-survey.md](plan_warung-photo-survey.md) already specifies.

### Design change implied

Survey **school buffers**, not whole kelurahan (see the survey plan §4, Phase 3). A census within
200 m and 500 m buffers around a stratified sample of schools is more defensible for this question
*and* requires less total riding than sampling kelurahan.

Add matched control buffers around non-school points to test whether outlet and advertising
density near schools is genuinely elevated.

---

## 6. Next steps

1. **Verify the regulation text directly** — both radii, transition provisions, and whether
   *satuan pendidikan* includes TK/PAUD. §3.1 swings from **20.8% to 84.7%** on that last point
   alone; it is worth more than any further analysis.
2. **Validate SD/SMP/SMA coverage — the open problem.** Dukcapil has no SD/SMP for Semarang, so
   set A rests on OSM alone and is unvalidated. Use Dapodik's *public counts* per level
   (coordinates are not needed to check completeness), or request the layer from Dinas
   Pendidikan Kota Semarang.
3. **Re-run the Google fetch with `places.businessStatus`** (≈US$8) to exclude permanently-closed
   stores, and **compare master-vs-Google coverage by kecamatan** to test whether the ~50% miss is
   spatially random. That single check determines whether the *shares* in §3 are usable at all.
4. **Select the school sample** — stratify by level and neighbourhood type.
4. **Extend the capture protocol** with the tobacco attributes (survey plan §4, Phase 0).
5. **Ethics clearance** — surveying near schools raises children-in-frame risk. Survey during
   class hours, avoid arrival and dismissal, blur at ingest.

Potential partners: Undip (in Semarang, natural collaboration and strengthens the ethics
application), Komnas Pengendalian Tembakau, IAKMI, CISDI. Funding for tobacco control in Indonesia
is comparatively available — Bloomberg Philanthropies, Vital Strategies, Campaign for
Tobacco-Free Kids.

Candidate venues: *Tobacco Control* (BMJ), *Nicotine & Tobacco Research*, *Health & Place*.

---

## Sources

- [Tobacco Induced Diseases — Strengthening tobacco control in Indonesia: key advancements in PP 28/2024](https://www.tobaccoinduceddiseases.org/Strengthening-tobacco-control-in-Indonesia-Key-advancements-in-government-regulation,206720,0,2.html)
- [Campaign for Tobacco-Free Kids — New tobacco control regulations for Indonesia](https://www.tobaccofreekids.org/press-releases/2024_07-31_new-tobacco-control-regulations-for-indonesia)
- [CNBC Indonesia — Alasan rokok dilarang dijual eceran & 200 meter dari sekolah](https://www.cnbcindonesia.com/news/20240805090134-4-560325/nih-alasan-rokok-dilarang-dijual-eceran-200-meter-dari-sekolah)
- [AMLI — Joint statement rejecting PP 28/2024 and RPMK](https://amli.or.id/news/press-release-joint-statement-of-the-indonesian-outdoor-media-companies-association-reject-pp-28-2024-and-rpmk/)
- [Dapodik reference portal (Kemendikdasmen)](https://referensi.data.kemendikdasmen.go.id/pendidikan/dikdas)
