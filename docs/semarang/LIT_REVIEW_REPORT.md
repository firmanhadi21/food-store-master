# Literature review — tobacco retail near schools, and POI completeness

> Run: 2026-08-04 · For `naskah_sinta_ritel-rokok-sekolah.md`
>
> ⚠️ **Method limitation, read first.** No Zotero or Obsidian MCP was configured, no local
> `papers/` library exists, and neither `arxiv_fetch.py` nor `semantic_scholar_fetch.py` was
> present. This review therefore ran on **web search alone** — titles, URLs and snippets, not
> full texts, abstracts or citation counts. Everything below should be treated as a **map of
> the literature to go and read**, not as a completed review. Nothing here has been read in
> full. Several conclusions hinge on papers behind paywalls.

---

## 1. Findings (2026-08-04)

- **Indonesian GIS work on cigarette retailers near schools already exists** — Banyuwangi
  (2020) is a direct precedent. The manuscript cannot claim to be first.
- **The strongest Indonesian studies use field enumeration, not POI data** — one 2024 study
  counted 21,460 retailers across four districts by survey. This is the established method
  in this literature, and a POI-based study must justify itself against it.
- **PP 28/2024 dates from 26 July 2024**, so **no prior work measures compliance against its
  radii**. This is the manuscript's defensible first.
- Burgoine & Harrison (2013) already established POI incompleteness *and* its social
  patterning — confirming the earlier finding that C1/C2 are not novel.
- Chen et al. (2025) is a Canadian OSM-vs-commercial-vs-administrative **agreement** study.
  It does **not** appear to address denominator direction — so the asymmetry finding survives.
- **No study found applying capture–recapture to POI/geospatial database completeness.**
  Apparent gap, but a single search is weak evidence.
- Overture globally draws **~40% of records from OSM**; Semarang's 98.1% Meta share is
  therefore an outlier worth reporting.

---

## 2. Papers by theme

### 2.1 Tobacco retail density near schools and youth smoking

| Paper | Venue | What it does | Relevance |
|---|---|---|---|
| Marsh et al. (2021), *Association between density and proximity of tobacco retail outlets with smoking: a systematic review of youth studies* | Health & Place ([PMC8171582](https://pmc.ncbi.nlm.nih.gov/articles/PMC8171582/)) | Systematic review, youth ≤18, 1990–2019 | **Core citation** for the exposure–outcome link |
| Finan et al., *Association Between Tobacco Outlet Density and Smoking Among Young People: A Systematic Methodological Review* | Nicotine & Tobacco Research 23(2):239 ([link](https://academic.oup.com/ntr/article/23/2/239/5552732)) | **Methodological** review of density measures | Directly relevant to §4.3 |
| *Tobacco retailer density and smoking behaviour: how are exposure and outcome measures classified?* (2023) | BMC Public Health ([PMC10585801](https://pmc.ncbi.nlm.nih.gov/articles/PMC10585801/)) | Classifies how density and smoking are operationalised; 10 databases | **Must read.** Nearest thing to the denominator question |
| *Tobacco retail availability and smoking — systematic review and meta-analysis* | Drug and Alcohol Review ([link](https://onlinelibrary.wiley.com/doi/full/10.1111/dar.13936)) | Meta-analysis; flags exposure misclassification as a primary bias | Supports framing incompleteness as a bias source |
| Shortt et al., Scotland | Soc Sci Med ([link](https://www.sciencedirect.com/science/article/abs/pii/S0277953617307190)) | Youth up to **53% more likely to initiate** where outlet density is higher | Strongest single effect size found |

**Consensus:** youth smoking is positively associated with outlet density near home and
school. **Contested:** effect sizes vary widely, and reviews repeatedly attribute this to
**heterogeneous exposure operationalisation** — buffer size, network vs Euclidean distance,
density vs proximity.

### 2.2 Indonesia and Southeast Asia ⚠️ *richer than expected*

| Paper | Venue | What it does | Relevance |
|---|---|---|---|
| *Density of cigarette retailers near schools and sales to minors in Banyuwangi, Indonesia: A GIS mapping* (2020) | Tobacco Induced Diseases ([PMC6987962](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6987962/)) | **GIS mapping of cigarette retailer density near schools in Indonesia** | ⚠️ **Direct prior art.** Must be cited and distinguished |
| *Exposure to outdoor cigarette advertisements and cigarette retailers near Indonesian schools* (2024) | Tobacco Prevention & Cessation ([PMC11580535](https://pmc.ncbi.nlm.nih.gov/articles/PMC11580535/)) | 4 districts, 6,715 students; **21,460 retailers enumerated, 30.4% selling cigarettes**; 13,660 outdoor ads; density rises as distance to school falls | ⚠️ **The benchmark.** Field enumeration at scale |
| Astuti et al. (2021), *Is Youth Smoking Related to the Density and Proximity of Outdoor Tobacco Advertising Near Schools? Evidence from Indonesia* | IJERPH 18(5):2556 ([doi](https://doi.org/10.3390/ijerph18052556)) | Links advertising density/proximity to youth smoking | Core Indonesian citation |
| *Tobacco Advertisements Near Schools and Smoking Behaviour, North Sumatera* (2025) | ([PubMed 40952298](https://pubmed.ncbi.nlm.nih.gov/40952298/)) | Recent replication | Shows the field is active |
| *Strengthening tobacco control in Indonesia: key advancements in PP 28/2024* | Tobacco Induced Diseases ([link](https://www.tobaccoinduceddiseases.org/Strengthening-tobacco-control-in-Indonesia-Key-advancements-in-government-regulation,206720,0,2.html)) | Commentary on the regulation | Cite when introducing PP 28/2024 |
| GYTS 2019 Indonesia | ([PMC10714413](https://pmc.ncbi.nlm.nih.gov/articles/PMC10714413/)) | Youth smoking **19.2%**; male youth current smokers **38.3%** | Prevalence figures for §1 |
| SKI 2023 | — | Ages 15–19 prevalence **16.7%** | Most recent national figure |

> **This is the most consequential result of the review.** The manuscript's introduction as
> drafted implies the outlet-level spatial question is unaddressed in Indonesia. It is not.

### 2.3 POI data completeness in food/retail environment research

| Paper | Venue | What it does | Relevance |
|---|---|---|---|
| Burgoine & Harrison (2013) | Int J Health Geogr 12:2 ([PMC3566929](https://pmc.ncbi.nlm.nih.gov/articles/PMC3566929/)) | POI PPV 74.9%; **convenience stores worst at 57.9%**; agreement differs urban 52.8% vs rural 43% **and by SES quintile** | **Confirms C1 and C2 are prior art.** Cite, do not claim |
| Chen et al. (2025), *Assessing the Validity of OpenStreetMap for Food Environment Research* | Geographical Analysis ([doi](https://onlinelibrary.wiley.com/doi/10.1111/gean.70014)) | Canada: OSM vs DMTI vs Can-FED; Spearman correlations plus categorical accuracy | **The paper that decides the framing.** From the abstract it is an *agreement* study and does **not** cover denominator direction |
| Wilkins et al., *Quality of OSM food-related POI data for epidemiological research* | ([RG](https://www.researchgate.net/publication/372411000)) | OSM-specific quality | Supporting |
| Lake et al., *Are secondary data sources on the neighbourhood food environment accurate? Glasgow* | Am J Prev Med ([link](https://www.sciencedirect.com/science/article/abs/pii/S0091743509004824)) | Street-audit validation | Supporting |
| *Validity and utility of two secondary sources against street audits in England* (2017) | Nutrition Journal ([PMC5738834](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5738834/)) | Street-audit validation | Supporting |
| Barrington-Leigh & Millard-Ball (2017) | PLOS One ([link](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0180698)) | OSM road network **>80% complete** globally, via two independent methods | Canonical completeness citation; methodologically close to capture–recapture |
| HeiGIT, *OSM completeness with Overture data* | ([link](https://heigit.org/osm-completeness-with-overture-maps-data/)) | Uses Overture to assess OSM completeness | Closest thing to this manuscript's provenance argument |

**Note:** Overture globally derives **~40% of records from OSM**. Semarang's **98.1% Meta**
composition is therefore unusual and worth reporting as such, not assumed typical.

### 2.4 Exposure measure choice

The 2023 BMC Public Health review finds density most often measured with **circular buffers**
(n=14) and recommends **network distance, travel time, or kernel density** instead. A separate
systematic review ([PMC5994245](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5994245/)) finds
**availability vs accessibility** measures yield different associations — 16 of 44 relationships
significant for availability against 8 for accessibility.

**Neither addresses the denominator direction studied here** (outlet-denominated vs
exposure-receptor-denominated response to the *same* data correction). Adjacent, not the same.

### 2.5 Capture–recapture for database completeness

Well established in epidemiology for registry completeness, and in official statistics for
administrative data coverage. **No study was found applying it to POI or geospatial database
completeness.** Barrington-Leigh & Millard-Ball's two-independent-method design is the nearest
analogue but is not framed as capture–recapture.

---

## 3. Synthesis

**Three literatures meet here and have not previously been joined.** Tobacco retail
environment research is mature but overwhelmingly UK/US/Canada/Australia. Indonesian work
exists and is growing, but relies on **field enumeration** — the 2024 four-district study
counted 21,460 retailers on foot. POI data-quality research is likewise mature but sits in
GIScience and health geography, and has barely been applied in Southeast Asia.

**The consensus is that outlet density near schools matters, and that measurement
heterogeneity is the field's main weakness.** Every methodological review reaches the second
conclusion; none resolves it. Reviews recommend better distance metrics — network, travel
time, kernel density — but treat the *underlying outlet layer* as given. That assumption is
exactly what fails in Semarang: the layer was 42% complete and unevenly so.

**The geographic bias is stark.** Validation studies of secondary POI data are almost entirely
Global North, where commercial POI vendors and administrative business registers exist. In
Indonesia neither is available to researchers, which is precisely why local studies enumerate
by hand. A study that measures how badly the available POI sources fail — and quantifies it —
addresses a real gap for anyone who cannot afford field enumeration.

**But the Indonesian precedent constrains the framing.** Banyuwangi (2020) already mapped
cigarette retailer density near schools with GIS. The 2024 study did it across four districts
with far better coverage than any POI source could achieve. The manuscript must therefore be
positioned as **(a)** the first measurement against PP 28/2024's specific radii, and **(b)** a
methodological contribution about POI completeness — not as the first spatial description of
the problem in Indonesia.

**One tension deserves attention.** The field-enumeration studies imply this manuscript's
outlet layer is badly incomplete, because ~30% of *all* retailers sell cigarettes and most are
informal. The honest response is that this is the manuscript's own finding, not an objection
to it — the completeness analysis quantifies exactly that gap, and the figures are stated as
lower bounds.

---

## 4. Gap analysis

Scored Novelty × 0.4 + Feasibility × 0.35 + Impact × 0.25, each out of 10.

| # | Gap | N | F | I | Score | Note |
|---|---|---:|---:|---:|---:|---|
| 1 | **Compliance measurement against PP 28/2024's radii** | 9 | 9 | 9 | **9.0** | Regulation is 18 months old; no prior work. Data already in hand |
| 2 | **Denominator direction under data correction** | 8 | 9 | 7 | **8.2** | Not found in any review. Already measured (+0.4 vs +16.2 pt) |
| 3 | **POI provenance as a pre-hoc completeness diagnostic** | 8 | 8 | 7 | **7.8** | Existing work validates post hoc against audits; provenance composition predicts coverage in advance |
| 4 | **POI completeness validation in Southeast Asia** | 6 | 9 | 7 | **7.1** | Literature is Global North; method transfers directly |
| 5 | **Capture–recapture for POI completeness** | 7 | 8 | 5 | **6.9** | Apparent gap, but low visibility; better as a Metode contribution than a headline |

**Recommended framing:** lead with **gap 1** (substantive, policy-relevant, uncontested), carry
**gap 2** as the methodological contribution, and use **gaps 3–5** to strengthen Metode.

---

## 5. What this changes in the manuscript

1. **Rewrite §1 point 4.** The draft treats Indonesian outlet-level spatial work as absent.
   It is not. Cite Banyuwangi (2020), the 2024 four-district study, and Astuti (2021), then
   state what is different here: PP 28/2024 had not been enacted when any of them was done.
2. **Add a paragraph justifying POI data over field enumeration.** The Indonesian precedent
   is field survey. The argument for POI is scale and repeatability — one city in days rather
   than four districts in months — with completeness measured rather than assumed. Say so
   explicitly; a reviewer familiar with the 2024 study will otherwise ask.
3. **Cite the 2024 enumeration as external support for the warung gap.** 30.4% of 21,460
   retailers selling cigarettes, mostly informal, is independent evidence that the 186
   toko_kelontong figure is a severe undercount.
4. **Position §4.3 against the 2023 BMC review**, which is the closest prior work on exposure
   measure classification and does not cover denominator direction.
5. **Add prevalence figures to §1**: GYTS 2019 youth 19.2% and male youth 38.3%; SKI 2023
   ages 15–19 at 16.7%.
6. **Note Overture's global ~40% OSM share** against Semarang's 98.1% Meta, so the provenance
   finding reads as an outlier rather than a generality.

---

## 6. Must read before submitting

Ranked by how much each could change the paper. **None has been read** — this review saw only
titles and abstracts.

1. **Chen et al. (2025), Geographical Analysis** — decides whether the methodological framing
   survives. Paywalled.
2. **BMC Public Health (2023), exposure/outcome classification** — open access, and the
   nearest prior work to the denominator claim.
3. **Tobacco Prevention & Cessation (2024), four-district Indonesian study** — open access,
   the benchmark this manuscript will be measured against.
4. **Tobacco Induced Diseases (2020), Banyuwangi** — open access, the direct precedent.
5. **Burgoine & Harrison (2013)** — open access; needed to position C1/C2 correctly.
6. **Nicotine & Tobacco Research methodological review** — for the §4.3 framing.

## 7. Not done

- No systematic database search (PubMed, Scopus, Web of Science) — this was web search only
- No citation counts, no forward/backward citation chasing
- No Indonesian-language literature searched (Jurnal Kesehatan Masyarakat and similar may hold
  relevant local work invisible to English search)
- No `references.bib` produced — no Zotero available
- Grey literature not searched (Komnas Pengendalian Tembakau, CISDI, Vital Strategies reports)
