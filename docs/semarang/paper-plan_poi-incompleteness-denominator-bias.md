# Paper plan — POI incompleteness biases retail-environment exposure measures asymmetrically

> Plan for a methods paper built entirely from work already in this repository.
> **No fieldwork and no further data collection required for the core claims.**
>
> Created: 2026-08-04 · Status: **plan, not drafted**
> Evidence base: `docs/semarang/analysis_tobacco-retail-near-schools.md` and the
> `scripts/semarang/` pipeline.

---

## 1. The argument in one paragraph

POI datasets (Overture, OSM, commercial aggregators) are increasingly used to measure retail food
and tobacco environments, and their completeness is usually assumed rather than measured. Using
Kota Semarang, Indonesia, we measure it directly against an independent source and find coverage
of **42% even for branded national chains** — the category researchers most expect to be reliable.
Coverage is **spatially structured** (0.19–0.79 across 16 kecamatan), tracking commercial
formality rather than geography, and the mechanism is diagnosable from dataset provenance:
Overture in Semarang is **98.1% Meta-derived**, versus 39.8% in Japan where store-locator scraping
supplies a quarter of records. Correcting the layer then produces the paper's central finding:
**the bias is asymmetric with respect to the denominator.** An outlet-denominated exposure measure
moved 0.4 points; the exposure-denominated equivalent moved 16.2 points. Studies that denominate
on outlets will therefore pass their own sensitivity checks while resting on a layer missing more
than half its data.

---

## 2. Claims and the evidence for each

| # | Claim | Evidence (all in-repo) | Status |
|---|---|---|---|
| C1 | POI coverage of branded chains is far below assumption | Capture–recapture vs Google Places: Alfamart 42%, Indomaret 41% (`estimate_chain_truth.py`) | ✅ measured |
| C2 | Incompleteness is spatially structured, not random | Kecamatan coverage 0.19–0.79 (`analyze_coverage_spatial_bias.py`) | ✅ measured |
| C3 | Distance-based tests fail to detect it | `corr(distance, coverage) = −0.140`; stratification required | ✅ measured |
| C4 | The mechanism is dataset provenance | Overture Semarang 98.1% Meta / 0.2% AllThePlaces vs Japan 39.8% / 25.7% | ✅ measured |
| C5 | **Bias is asymmetric by denominator** | Outlet-denominated +0.4 pt vs exposure-denominated +16.2 pt on the same correction | ✅ measured |
| C6 | Reference layers are also incomplete, compounding it | Schools 76.4% of Dapodik counts; SMP only 59.4% | ✅ measured |
| C7 | Capture–recapture is a practical validation method | Chapman estimator applied; union reaches ~85% of estimate | ✅ demonstrated |

**C5 is the paper.** C1–C4 establish the setting, C6 shows it compounds, C7 is the remedy.

---

## 2.5 ⚠️ Literature check — C1 and C2 are already published

Performed 2026-08-04, before drafting. **This materially narrows the contribution and the plan
below is written accordingly.**

### Already established — cite, do not claim

| Claim | Prior work |
|---|---|
| **C1** POI data is substantially incomplete for food retail | Burgoine & Harrison (2013), *Int J Health Geogr* 12:2 — POI overall PPV 74.9%; **convenience stores worst at 57.9%**, and they explicitly note these are "commonly cited as obesogenic" |
| **C2** Incompleteness is spatially and socially structured | Same paper — agreement differs rural 43% vs urban 52.8%, **and by SES quintile** |
| OSM specifically is incomplete for food POI | Chen (2025), *Geographical Analysis* — "Assessing the Validity of OpenStreetMap for Food Environment Research"; Wilkins et al., "The quality of OpenStreetMap food-related point-of-interest data for use in epidemiological research" |
| Street-audit validation of secondary sources | Multiple; e.g. *Nutrition Journal* (2017) on England |
| **C7** Capture–recapture for database completeness | Long-established in epidemiology (registry completeness). Not novel as a method |
| Measure choice changes conclusions | Systematic review, *PMC5994245* — availability vs accessibility measures yield different associations |

**Even the framing "the category you'd assume is safest is worst" has a precedent** — Burgoine &
Harrison found exactly that for convenience stores, in 2013.

### What still appears novel

| | Why it survives the check |
|---|---|
| **C4 — provenance as a pre-hoc diagnostic** | Existing work validates POI data *empirically and after the fact*, usually against expensive street audits. Identifying that **upstream contributor composition predicts coverage** — Overture 25.7% AllThePlaces in Japan → 97.6% chain coverage; 0.2% in Semarang → 42% — makes completeness **checkable from metadata before use**. No prior work found doing this. |
| **C5 — denominator asymmetry** | The prior review shows *availability vs accessibility* (different constructs) diverge. C5 is different: **same construct, same threshold, same data correction — but denominating on outlets vs on exposure receptors responds completely differently** (+0.4 pt vs +16.2 pt). Not found in the searches performed. |
| **Global South setting** | The literature is overwhelmingly UK / Canada / US. Indonesia is under-served, and the mechanism here (no store-locator scraping upstream) is specific to that context. |

### Consequence for the paper

**Re-centre on C4 + C5, with C1/C2 as confirmation-in-a-new-setting rather than contribution.**
The revised argument becomes:

> Incompleteness and its social patterning are known (Burgoine & Harrison 2013). We add two
> things: it is **predictable in advance from dataset provenance**, and its effect on exposure
> studies is **asymmetric by denominator** in a way that makes standard sensitivity analysis fail
> to detect it.

### Must do before drafting

- [ ] **Read Chen (2025), *Geographical Analysis*** in full. It is recent, directly on-topic, and
      may already contain C5 or render it moot. **This single paper determines whether the plan
      survives.**
- [ ] Read Burgoine & Harrison (2013) in full and position C1/C2 as replication.
- [ ] Search specifically for prior work on denominator choice in retail-exposure metrics — the
      searches performed were not exhaustive and C5 is the load-bearing claim.

---

## 3. Why the Japan pairing matters

The same pipeline was applied to Japan (`docs/master/`) and Semarang. This blocks the obvious
dismissal — *"data in developing countries is worse"* — and replaces it with a specific,
diagnosable mechanism:

| | Japan | Semarang |
|---|---:|---:|
| Overture: meta | 39.8% | **98.1%** |
| Overture: AllThePlaces | 25.7% | **0.2%** |
| Convenience-store coverage vs official statistics | 97.6% | **~42%** |

**AllThePlaces scrapes official store locators.** Where it is present, chain coverage is near
census; where absent, coverage collapses to whatever user-generated business pages happen to
exist. This makes the finding *predictable from provenance metadata* — a practical diagnostic any
researcher can run before trusting a POI extract, which is a usable contribution in its own right.

---

## 4. Proposed structure

1. **Introduction** — POI data in retail-environment epidemiology; completeness usually assumed
2. **Background** — measurement error in food/tobacco environment research; POI completeness literature
3. **Setting and data** — Kota Semarang; Overture, OSM, Google Places, Dapodik, Dukcapil
4. **Methods**
   - Master construction and category classification
   - Independent validation via Google Places
   - Capture–recapture (Chapman) for population estimation
   - Kecamatan-stratified coverage
   - The two-denominator comparison
5. **Results** — C1 → C6 in order
6. **Discussion** — provenance as diagnostic; which denominator to use; what sensitivity analysis misses
7. **Limitations** — single city; Google not a census; closed-store contamination; point-to-point buffers
8. **Practical guidance** — a short checklist for practitioners

---

## 5. What must be done before drafting

### Blocking

- [x] **Literature review — done 2026-08-04, see §2.5.** Outcome: **C1 and C2 are already
      published** (Burgoine & Harrison 2013). Paper re-centred on C4 + C5.
- [ ] **Read Chen (2025), *Geographical Analysis*.** The single highest-priority item — it is
      recent, directly on-topic, and could render C5 moot.
- [ ] **Exhaustive search on denominator choice** in retail-exposure metrics. C5 is now the
      load-bearing claim and the searches so far were not exhaustive.
- [ ] **Verify the Japan figures** independently from `docs/master/` rather than quoting them,
      since they were produced for a different purpose.

### Strengthening (do if time allows)

- [ ] **Confidence intervals on the capture–recapture estimates.** Chapman has a standard variance
      estimator; report CIs rather than point estimates.
- [ ] **Bootstrap the denominator comparison** so the 0.4 pt vs 16.2 pt contrast carries
      uncertainty rather than being two point estimates.
- [ ] **Re-fetch Google with `places.businessStatus`** (≈US$8) to remove closed stores. Currently
      an acknowledged upward bias in the truth estimate.
- [ ] **Geocode Dapodik school listings** to close C6 from 76.4% toward complete, and test whether
      the missing 249 schools shift the headline.
- [ ] **A second city** would convert "case study" into "generalisable." Highest-cost item;
      probably out of scope for a first paper but worth naming as future work.

### Not required

Field survey. The warung layer is *motivated* by this paper but not needed for its claims — a
useful separation, since it means this can be submitted while fieldwork is still being funded.

---

## 6. Candidate venues

| Venue | Fit |
|---|---|
| *Health & Place* | Strong — exposure measurement, health geography, methods-tolerant |
| *International Journal of Health Geographics* | Strong — explicitly methods-oriented |
| *Applied Geography* | Good — applied methods with policy relevance |
| *Computers, Environment and Urban Systems* | Good — if framed as data-quality methodology |
| *IJGIS* | Possible — would need heavier formal treatment |
| *Tobacco Control* | Only if reframed around the substantive PP 28/2024 finding rather than method |

Recommended: **Health & Place** or **IJHG**. Both take measurement-error methods papers and reach
the audience that would otherwise make this mistake.

---

## 7. Relationship to the other Semarang documents

| Document | Role |
|---|---|
| [analysis_tobacco-retail-near-schools.md](analysis_tobacco-retail-near-schools.md) | Primary evidence base; substantive application |
| [plan_warung-photo-survey.md](plan_warung-photo-survey.md) | Future work; this paper justifies it |
| [assessment_warung-dataset-value.md](assessment_warung-dataset-value.md) | Strategic context; ODbL constraint on any data release |

**Data availability:** scripts are reproducible and can be cited. Note the ODbL constraint — the
master contains OSM-derived records, so any released derivative inherits share-alike. Google
Places results cannot be redistributed under its terms; report aggregates, not the raw layer.

---

## 8. Honest risks

1. **The contribution is narrower than it first appeared.** §2.5 established that C1 and C2 were
   published in 2013. The paper now rests on **C4 and C5 alone**. If Chen (2025) covers either,
   there may not be a paper — reframe as a Global South replication with a provenance diagnostic,
   which is still publishable but is a different and smaller claim.
2. **Single-city evidence.** Reviewers will ask about generality; the Japan pairing helps for the
   mechanism but not for C5.
3. **Google Places is not ground truth.** The paper must be scrupulous that capture–recapture
   estimates a population from two incomplete sources — it does not observe truth.
4. **The substantive PP 28/2024 numbers are not publication-ready** (§4 caveats in the analysis
   doc). If the paper cites them, it must carry those caveats, or restrict itself to the
   methodological claims.
