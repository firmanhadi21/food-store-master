# Plan — Mapping warung / toko kelontong by bicycle photo survey

> Workflow plan for building a warung POI layer from geotagged photos captured by bicycle,
> to close the informal-retail gap that POI datasets (Overture, OSM) structurally cannot cover.
>
> Created: 2026-08-04 · Status: **plan only, not started**
> Target area: Kota Semarang (pilot), method intended to generalise
>
> **Written in English** rather than the repository's usual Japanese, because the working team
> (riders, classifiers) is Semarang-based. Code comments under `scripts/semarang/` follow the
> repository's Japanese convention.
>
> Supersedes the earlier video + object-detection plan. That approach was abandoned because
> stopping to photograph removes the need for detection, triangulation, and time-sync entirely
> (§3).

---

## 1. Why this exists

The Semarang master (`data/semarang/semarang_food_master.parquet`, 987 stores) holds only
**186 toko_kelontong**, which is off by orders of magnitude. Measured causes:

- **Overture Places in Semarang is 98.1% Meta-derived** (Japan: 39.8%, with AllThePlaces at
  25.7%). The store-locator scraping that makes Overture near-complete for Japanese chains has
  effectively no Indonesian equivalent — AllThePlaces contributes 0.2% here.
- Small warung have no web presence, no Facebook page, and no chain locator. **No amount of
  pipeline work on existing POI sources will surface them.**

Field capture is the only practical route, and bicycle survey reaches the *gang* — the kampung
alleys where the densest warung are, and which no vehicle-based imagery covers.

### The question the pilot must answer

> **Does warung density vary meaningfully across the urban–peripheral gradient?**

- **Yes** → the layer discriminates; scaling up is justified.
- **No** → warung are uniformly ubiquitous. That is itself a publishable finding, and the correct
  action is to *stop*, not to survey the whole city.

Binary proximity ("warung within 500m") saturates to ~100% everywhere and stops discriminating.
**Density** — outlets per km² or per capita — is continuous and does not saturate. That is the
target variable.

---

## 2. Method

**Field:** bicycle. Insta360 **bike-mounted, flat (non-360) photos, remote-triggered**. Rider
angles the bicycle to frame the shop and triggers from a pocket remote. Phone in pocket runs a
continuous GPX logger. No interaction, no form filling, no dismounting.

**Desk:** photos geotagged from the GPX track by timestamp, faces blurred, then classified from
the images by two people.

### Why this shape

**Discretion is an operational requirement, not a preference.** Holding up a phone to photograph
someone's warung draws attention, questions, and refusals, and slows the survey to a crawl in a
residential kampung. Bike-mounted and remote-triggered is unobtrusive and fast.

**Consequence — attributes move to desk work.** Since the rider cannot fill a form per shop, the
photo becomes the primary record and classification happens later. This is an improvement:

- Classification is **reviewable and auditable** — calls can be revisited months later
- **Two people classify the same photos independently**, so inter-annotator agreement is a natural
  byproduct rather than a special exercise
- No tired-rider judgment baked in irreversibly
- Field time reduces to riding and shooting

---

## 3. What this approach eliminates

Relative to continuous video with automated detection:

| Problem | Status |
|---|---|
| Time sync (video↔GPS) | **Trivial** — stationary at capture, seconds of error move you nowhere |
| Bearing / azimuth estimation | **Gone** — position is the shop's position |
| Multi-frame triangulation | **Gone** |
| Cross-frame tracking | **Gone** |
| Object detection / model training | **Gone** — the rider does the detecting by choosing to shoot |
| Detector labeling burden | **Gone** — only classification remains, done at the desk |
| Occlusion | **Much reduced** — rider positions to get a clear view |

GPS also improves: a brief stationary pause yields several fixes to average, far better than a
moving fix.

**Cost:** speed. Stopping at each shop means a city-wide census is off the table. This is a
**sample-based** survey by design (§6).

---

## 4. Phases

### Phase 0 — Define output and ontology · ½–1 day

- **Purpose of the layer** — density per area? presence per kelurahan? This sets required
  positional accuracy and sample design.
- **Class definitions** — warung kelontong / warung makan / toko / gerobak / not-a-shop.
- **Output schema** — `id, lat, lon, gps_accuracy_m, class, confidence, photo_ids, capture_date, classifier`.

**Gate:** the accuracy requirement is stated *in meters*. Without it nothing downstream is evaluable.

---

### Phase 1 — Shakedown ride ⚠️ **gate** · 1 day

Validates the entire chain on one block before any real survey. Choose a street containing
**known Indomaret/Alfamart** — their coordinates are already in OSM, giving free ground truth.

1. Mount the rig. Check the remote reaches from pocket, and the mount holds the intended angle.
2. Clock-sync shot: photograph the phone's GPS clock screen.
3. Ride the block, shooting every candidate shop plus the known chain stores.
4. Closing clock-sync shot.
5. Geotag photos from the GPX track; compare chain-store positions against OSM.

**Measures:** positional error against known stores · GPS accuracy distribution · **photo
legibility — can signage actually be read at the framing you used?**

**Gate — all three must pass:**
- positional error within the Phase 0 requirement
- signage legible enough to classify
- **a second person can classify the photos without having been there**

If the third fails, the desk-classification design is broken and must be fixed before scaling —
usually by changing framing or adding the second wider shot.

---

### Phase 2 — Classification guideline and agreement · 2–3 days

Written against the real Phase 1 photos, not in the abstract.

1. Draft the decision tree with worked examples and edge cases.
2. Two people classify ~100 photos independently.
3. Measure inter-annotator agreement.
4. Revise the guideline against the disagreements; repeat if needed.

**Gate:** agreement ≥ ~80% (or Cohen's κ ≥ 0.7).

> **This is the project's accuracy ceiling.** If two classifiers disagree on 30% of cases, the
> layer cannot be more than 70% right regardless of anything else. Fix the guideline, not the
> classifiers.

Edge cases that must be resolved explicitly:

| Case | Question |
|---|---|
| House with window counter selling sachets | warung — baseline case |
| Same house, shutter closed | still a warung, but unidentifiable from the photo — how recorded? |
| Table on sidewalk with cigarettes and snacks | warung or not? |
| *Gerobak* (cart) | mobile — belongs in a fixed POI layer at all? |
| Warung makan vs warung kelontong | near-identical frontage, different categories |
| Pulsa counter with three snacks by the till | threshold for "sells food" |
| Frontage with no visible goods | unclassifiable — needs an explicit "unknown" class |

**An `unknown` class is mandatory.** Forcing a binary call on ambiguous frontage is how
agreement collapses.

---

### Phase 3 — Survey design · 1 day

- **Stratification** — select 3–5 kelurahan spanning the density gradient: dense urban core,
  peripheral, semi-rural (Gunungpati / Mijen). Chosen deliberately to test spatial variation.
- **Coverage rule** — which streets and *gang* count as in-scope. Without a written rule,
  "density per km²" has no denominator.
- **Route plan** — traceable so the surveyed extent is known, not guessed.

---

### Phase 4 — Main survey · 1–2 weeks

Ride the sample areas per the coverage rule.

**Include a capture–recapture subsample.** Re-ride 1–2 blocks on a different day, ideally with a
different rider. The overlap between passes gives a **recall estimate** — how many warung were
missed on a single pass. Without this there is no way to know whether the survey found 60% or 95%
of what is there, and the density figures are uninterpretable.

**Daily:** verify GPX logged, clock-sync shots present, photos offloaded and backed up.

---

### Phase 5 — Processing · 2–3 days

```
photos + GPX track
  → clock offset from sync shots
  → geotag by timestamp (exiftool)
  → face / licence-plate blur
  → desk classification (two classifiers, guideline-driven)
  → dedup repeat passes
  → GeoJSON / PostGIS → merge into semarang_food_master
```

Dedup and category schema reuse what already exists in `scripts/semarang/`.

---

### Phase 6 — Analysis and decision · 2–3 days

**Deliverables:** warung layer for the surveyed areas · density per km² and per capita ·
recall estimate from capture–recapture · measured gap versus what Overture and OSM hold for the
same areas.

**Gate — the §1 question:** does density vary meaningfully across the gradient?
**Yes** → scale up. **No** → stop and publish the saturation finding.

---

## 5. Timeline

Roughly **3–4 weeks part-time** to a pilot result. Critical path is Phase 1 → 2 → 4 → 6;
Phase 3 runs alongside Phase 2.

---

## 6. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| **Discovery recall** | Riding past, you must *notice* each warung. Missed shops bias density downward invisibly | Capture–recapture subsample (Phase 4) quantifies it |
| **Classifier disagreement** | Caps achievable accuracy regardless of anything else | Phase 2 gate before scaling |
| **Photo illegibility** | A photo you cannot classify is a wasted stop | Phase 1 gate; two shots per shop |
| **GPS in narrow gang** | Multipath from close buildings degrades fixes | Pause 3–5s per shot; log accuracy per point; discard or revisit bad fixes |
| **Coverage denominator** | "Density" is meaningless without a defined surveyed extent | Written coverage rule (Phase 3); log the actual route |
| **Survey fatigue** | Recall drops over a long day; late blocks under-sampled | Cap daily riding hours; randomise block order within a kelurahan |

---

## 7. Field protocol

- GPX logger running continuously at 1s interval, phone in pocket
- **Clock-sync shot at session start and end** — photograph the phone's GPS clock screen. This
  single frame establishes the camera↔GPS offset; the closing shot catches drift
- Angle the bicycle, **pause 3–5 seconds**, trigger from the pocket remote
- **Two shots per shop** — one tighter on signage, one wider for context. Storage is free;
  ambiguity at the desk is not
- Note session boundaries so photo↔track matching stays unambiguous
- Carry a *surat izin* / institutional letter with a one-sentence explanation ready

---

## 8. Legal, ethics, and conduct

- **UU PDP No. 27/2022** applies to people captured in frame. Blur faces and licence plates
  **at ingest**, as a non-optional pipeline step.
- Commercial frontage on a public street is generally permissible to photograph; *data handling*
  is the regulated part. Decide raw-photo retention policy before collection begins.
- **If academic, confirm whether ethics clearance is required before collection**, not after.
- Being unobtrusive is fine; being **unidentifiable if questioned** is not. A visible
  institutional sticker on the bicycle makes low-key work safer, not more conspicuous.

---

## Appendix A — Geotagging

Insta360 photos carry EXIF timestamps; position comes from the phone's GPX track.

```bash
# offset N measured from the clock-sync shots (camera clock vs GPS clock)
exiftool -geotag track.gpx "-geosync=+Ns" photos/

# verify, and export a table for review
exiftool -filename -gpslatitude -gpslongitude -gpsdop -createdate \
         -T -n photos/ > geotagged.tsv
```

Because every shot is stationary, timestamp matching is forgiving — a few seconds of error moves
the point negligibly. This is the one respect in which stop-and-shoot is materially easier than
continuous capture.

---

## Appendix B — Desk classification tooling

Classification only — no bounding boxes, no detection — so the tooling is light:

- **Label Studio** — image classification projects, multi-annotator, agreement metrics built in.
  Best fit for the Phase 2 agreement measurement.
- **QGIS** with photo-attachment attribute forms — good if classifiers want map context while
  deciding.
- A spreadsheet plus a photo viewer is a legitimate starting point for Phase 1–2 volumes.

**On classifiers:** local knowledge outweighs annotation experience. Someone who lives in Semarang
reads cues — banner brands, sachet strips, residential vs commercial frontage — that an outside
classifier cannot. Semarang-based students will produce better labels than an outsourced service.

---

## Appendix C — Open decisions

Not yet made; each affects the plan:

1. **Fixed POI layer only, or mobile vendors too?** *Sayur keliling* (mobile vegetable vendors)
   are a genuine fresh-food channel that no fixed-point survey can capture. This is a structural
   ceiling on the method and should be stated explicitly in any publication.
2. **Positional accuracy requirement** — Phase 0 output; drives the Phase 1 gate.
3. **Coverage rule for *gang*** — which alleys are in scope. Directly determines the density
   denominator and therefore comparability between kelurahan.
4. **Retention and licensing of the raw photos** — the derived POI layer and the photo archive
   need separate decisions.
