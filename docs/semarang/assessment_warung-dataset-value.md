# Assessment — Value, licensing, and use cases for a warung dataset

> Strategic assessment of what a surveyed warung / toko kelontong layer is worth, who would use
> it, and what constrains how it can be licensed.
>
> Created: 2026-08-04 · Companion to [plan_warung-photo-survey.md](plan_warung-photo-survey.md)
>
> **This is a technical and strategic assessment, not legal or financial advice.** The licensing
> analysis in §2 reflects a reading of the source licences and should be confirmed with your
> institution before any commercial commitment. Market observations in §1 are judgement as of
> August 2026 and will age.

---

## 0. Summary

| Question | Verdict |
|---|---|
| Worth selling as a location dataset? | **Probably not** — incumbents already hold better data (§1) |
| Is anything in it commercially differentiated? | **Yes** — brand-visibility observations from the photos, not the coordinates (§1.4) |
| Biggest practical risk to future options? | **ODbL contamination via the existing master** — act before first merge (§2) |
| Highest-value application overall? | **Tobacco / food retail environment near schools** (§3.1) |
| Does the research value exceed commercial value? | **Likely yes** (§4) |

---

## 1. Commercial assessment

### 1.1 The obvious buyers already have this

The natural market is FMCG — Unilever, Indofood, Wings, Mayora. Their distribution runs through
*general trade*, which accounts for the majority of Indonesian FMCG volume, so "where are the
warung" appears to be exactly what they would pay for.

They already have it. Every distributor maintains a route list built and visited weekly by its
own salesforce over decades. Nielsen and Kantar run retail measurement on top of that. A survey
dataset would be **less complete, less current, and unvalidated against sales** — competing
against an incumbent dataset that is effectively free to the buyer because it is a byproduct of
operations.

### 1.2 Secondary buyers are weaker than they were

- **Warung-digitisation platforms** (Ula, Warung Pintar, GudangAda, Mitra platforms) were the
  other obvious segment. That funding cycle has cooled considerably since ~2022.
- **Telcos** — pulsa distribution through warung; largely already mapped by their own channels.
- **Banks / fintech** — more interesting. Branchless banking agents are frequently warung, and
  coverage-gap analysis is a genuine need. But this is a narrow, relationship-driven sale, not a
  product.
- **Government** (BPS, Bapanas, Kemendag, Dinas) rarely pays well for data, and BPS would
  reasonably regard this as within its own mandate.

### 1.3 The scale problem

Semarang alone is a proof of concept, not a product. FMCG buyers need national or at least
multi-city coverage. **Bicycle survey does not scale there** — Indonesia has 500+ kabupaten/kota
and the method caps out at city scale.

> **Run this number before anything else:** if the dataset cannot sell for more than the survey
> labour cost, it is not a business.

### 1.4 What would actually be differentiated

**The photos, not the points.** If images capture which rokok banner is displayed, which brands
are visible, and what is in the window, that is *retail execution intelligence* — a category with
established commercial demand (Trax and similar built businesses on it). Locations are commodity;
systematic observation of brand presence is not.

This requires a **different capture protocol** — consistent framing, systematic revisits — so it
must be decided before the survey, not retrofitted after.

Thinner but real: **neutrality** (a third-party layer not tied to one distributor's territory)
and **freshness** (updates on a known cycle).

### 1.5 Most likely commercial form

Not row sales. If commercial return is wanted, the realistic vehicle is **the method and analysis
as consulting** — helping a specific buyer size a specific coverage gap — rather than licensing
the dataset itself.

---

## 2. ⚠️ The ODbL constraint — act before the first merge

**This is the one time-sensitive item in this document.**

The existing Semarang master is **40.0% OSM-derived** (395 of 987 records;
`data/semarang/semarang_food_master.parquet`). OSM is **ODbL 1.0**, which is share-alike: a
derived database must itself be offered under ODbL. That effectively forecloses selling the
combined product as proprietary data.

### What to do

**Keep the warung survey as a legally separate layer.** Your own photos, your own GPS track, your
own classification — that provenance is clean and unencumbered.

- Store and version the warung layer **standalone**, not merged into `semarang_food_master`.
- Treat any merge with the master as a **published derivative** (ODbL, as the master already
  requires), never as the commercial asset.
- Record provenance per record so the two can always be separated again.

This costs nothing now and preserves every option later. **Doing it after the first merge is
much harder than doing it before.** See also `docs/master/調査_食料品店マスターのライセンス.md`
for the equivalent analysis on the Japan side — the constraint is the same.

### Related decision

Contributing the survey to **OpenStreetMap** is a genuine public good and would improve the base
map for everyone working on Indonesia. It also **forecloses proprietary use of what you
contribute**. A subset can be contributed while retaining the rest, but the split should be
deliberate and recorded, not incidental.

---

## 3. Non-commercial applications

Ranked by impact-per-effort. What differentiates this dataset for these purposes is that it has
**photos** and **reaches the gang** — not that it has coordinates.

### 3.1 Tobacco and food retail environment near schools — *highest value*

Warung are the primary cigarette retail channel in Indonesia, including single-stick sales
(*rokok ketengan*), which is the main pathway to youth smoking initiation. Indonesia has among the
world's highest male smoking prevalence and comparatively weak retail-side controls.

**Warung density and tobacco advertising within a set radius of schools** is a direct,
high-impact policy question that existing data cannot answer, because the outlets are not mapped.

The photos make this substantially stronger than a point layer: **the rokok banners that serve as
detection cues are themselves the exposure variable.** You would be measuring advertising density,
not merely outlet density.

The same structure applies to sugary drinks, relevant to ongoing SSB tax debates.

Well-established internationally as a research field; badly under-served in Indonesia.
**Fieldwork is identical to what the survey plan already specifies** — only the analysis differs.

### 3.2 Nutrition and stunting — food environment composition

Stunting reduction is a top-tier national priority with attached budget. Warung sell
predominantly packaged and ultra-processed goods; pasar sells fresh.

**Mapping the ratio** yields a food-environment measure — the "food swamp" question rather than
the food desert one — speaking directly to Indonesia's double burden of stunting alongside rising
obesity. The existing master already supplies the pasar and supermarket layers; the warung layer
completes the denominator.

### 3.3 Flood resilience — specifically relevant to Semarang

Semarang has severe land subsidence and recurrent tidal flooding (*rob*) in the north. Warung are
the first and often only food access point during and immediately after a flood — so a baseline
map supports emergency distribution planning and post-event damage assessment.

**Convenient alignment:** the northern coastal zone is where the coverage analysis
(`検証_カバレッジ限界寄与.csv`) showed the largest gaps — 70–100% of cells outside 500m of any
mapped store. It is both where the survey adds most and where the resilience question is most
acute.

### 3.4 Longitudinal value — the photo archive

Underrated. A geolocated photographic record of Semarang street frontage in 2026 **cannot be
recreated retrospectively**. Resurvey in two to three years yields:

- Business formation and closure rates in the informal sector
- Response to shocks — COVID demonstrated how much warung survival matters and how little data
  existed to measure it
- Land use change in kampung areas undergoing redevelopment

The points are worth something now; the archive is worth more later.

### 3.5 Financial inclusion and MSME policy

Warung frequently double as branchless banking agents, and are the archetypal UMKM that
government programmes target. The layer serves as a **sampling frame** for anyone studying or
serving the informal economy. Weaker than the health applications, but real.

### 3.6 The negative result is also useful

If the pilot shows warung are uniformly ubiquitous, that is policy-relevant evidence in itself:
proximity is not the binding constraint, so interventions should target **affordability, quality,
and what is stocked** — not location. This finding has value whether or not the full layer is
ever built.

---

## 4. Decisions this forces

| Decision | Options | Consequence |
|---|---|---|
| **Census or sample?** | Selling needs a census; publishing needs a stratified sample | Cannot optimise for both — **decide before Phase 3** of the survey plan |
| **Capture protocol** | Location-only vs brand-visibility | Brand visibility requires consistent framing and revisits; retrofitting is not possible |
| **Merge with master?** | Standalone vs merged | Merging inherits ODbL (§2). Keep standalone by default |
| **Contribute to OSM?** | All / subset / none | Public good vs proprietary optionality; record the split deliberately |
| **Primary application** | Food access / tobacco / resilience | Determines what attributes must be captured in the field |

### Recommendation

**The research value likely exceeds the commercial value.** "POI datasets systematically miss
informal retail in Global South cities — here is the measured gap and a reproducible low-cost
method" is a solid contribution, and the Overture-is-98%-Meta finding (§1 of the survey plan) is
already the setup for it.

Of the applications above, **§3.1 (tobacco / retail environment near schools)** is the one to
pursue: differentiated, policy-relevant, uses the photographs rather than merely the coordinates,
and requires no change to the planned fieldwork.
