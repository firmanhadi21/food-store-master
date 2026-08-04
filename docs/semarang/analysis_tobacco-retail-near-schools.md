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

### 2.1 Schools — Dapodik does not publish coordinates

Attempted and ruled out:

| Source | Result |
|---|---|
| `dapo.kemendikdasmen.go.id` | **403** — bot-blocked |
| `referensi.data.kemdikbud.go.id` | **Dead** — ministry renamed, domain retired |
| `referensi.data.kemendikdasmen.go.id` | **Live**, but aggregate counts per province and NPSN/name search only — **no coordinates** |
| Existing scrapers (`egin10/dapodik`) | Confirm NPSN, name, counts only |

The reason is structural: **school coordinates live in Verval SP, not Dapodik**, and Verval SP is
authenticated for school operators. There is no public scrape path.

**Routes to Dapodik coordinates, if needed:** a formal request to Dinas Pendidikan Kota Semarang,
or Semarang's local open data portal. Neither is a scrape.

**Used instead — OpenStreetMap** (`scripts/semarang/fetch_schools_semarang.py`):
**2,017 schools** within Kota Semarang.

| Level | Count |
|---|---:|
| TK / PAUD / RA | 1,110 |
| SD / MI | 507 |
| SMA / SMK / MA | 152 |
| SMP / MTs | 145 |
| unknown | 103 |

The distribution has the expected shape for an Indonesian city (SD ≫ SMP ≈ SMA).
**Dapodik's public counts should be used to validate OSM completeness** — counts are public even
though coordinates are not.

> **Classifier bug worth recording.** The first version used substring matching and put
> `SD Negeri Mangunharjo` in SMA, because `MAN` (Madrasah Aliyah Negeri) matched inside
> `Mangunharjo`. Same failure mode as `griya` / `mart` / `toko` in the master build. Fixed with
> **token matching** on `[^A-Z0-9]+` splits. SMA fell 183 → 152, SD rose 480 → 507.

### 2.2 Outlets

`data/semarang/semarang_food_master.parquet` — 987 stores. Categories assumed to sell tobacco:

- **minimarket** (548) — Alfamart / Indomaret / Alfamidi. Tobacco sales effectively certain.
  POI coverage is comparatively good because these are chains.
- **toko_kelontong** (186) — **a floor, not a count.** Real number is orders of magnitude higher;
  small warung do not appear in Overture or OSM. This is the gap the survey exists to fill.

---

## 3. Results

Reproduce with `python3 scripts/semarang/analyze_tobacco_school_buffers.py`
→ `docs/semarang/検証_学校周辺タバコ販売_バッファ.csv`

### 3.1 Outlets within the 200 m sales-restriction radius

Sensitivity to whether *satuan pendidikan* includes TK/PAUD — an interpretation question that
materially changes the answer:

| School set | Schools | minimarket | share | toko_kelontong | share |
|---|---:|---:|---:|---:|---:|
| **A** SD/SMP/SMA | 804 | 256 / 548 | **46.7%** | 93 / 186 | 50.0% |
| **B** SMP/SMA only | 297 | 114 / 548 | 20.8% | 40 / 186 | 21.5% |
| **C** incl. TK/PAUD | 2,017 | 402 / 548 | **73.4%** | 131 / 186 | 70.4% |

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
| A SD/SMP/SMA | 267 / 804 = **33.2%** |
| B SMP/SMA | 102 / 297 = 34.3% |
| C all levels | 649 / 2,017 = 32.2% |

### 3.4 Distance from school to nearest minimarket

SD/SMP/SMA, n = 773 (31 of 804 schools had no minimarket within the search window, so the true
median is marginally higher than shown):

| min | p25 | median | p75 | max |
|---:|---:|---:|---:|---:|
| 6 m | 150 m | **259 m** | 444 m | 2,096 m |

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
4. **The toko_kelontong rows are floors.** 186 known against a real count orders of magnitude
   higher — the true figures only rise with fieldwork.
5. **Transition provisions unchecked.** Whether PP 28/2024 grants existing outlets a compliance
   period is not established here and would change the interpretation of §3.1 entirely.

---

## 5. What fieldwork adds

The asymmetry between the two outlet types is the argument for the survey:

| | minimarket | toko_kelontong |
|---|---|---|
| POI coverage | Good — chains, well mapped | **Severely incomplete** |
| Baseline figures above | Roughly reliable | **Floor only** |
| Tobacco sale observable from POI | Inferred (chain policy) | **Not observable** |
| Advertising observable from POI | **No** | **No** |

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
   *satuan pendidikan* includes TK/PAUD. §3.1 swings from 20.8% to 73.4% on that last point alone.
2. **Validate OSM school coverage** against Dapodik public counts per level.
3. **Select the school sample** — stratify by level and neighbourhood type.
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
