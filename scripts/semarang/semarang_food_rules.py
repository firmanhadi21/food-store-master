#!/usr/bin/env python3
"""Classification rules for the Semarang master. **Imported by both the builder and the
verifier** (same reason as the Japan-side scripts/food_store_rules.py: if only one side is
changed, the verifier keeps counting as false positives things the builder already removed).

How this differs fundamentally from the Japan version
-----------------------------------------------------
The Japan pipeline trusts Overture's `category` and uses name matching only to separate
dispensing-only pharmacies. In Semarang the opposite holds: **`category` is not reliable.**
Measured (see inspect_grocery_names.py):

  - Overture records in Semarang are **98.1% Meta-derived** (Japan: meta 39.8%,
    AllThePlaces 25.7%). Meta-derived means self-declared Facebook page categories, so the
    business classification is coarse.
  - `convenience_store` (414 records) contains The Backyard Cafe, Victory Cell (a phone shop),
    Art'Classico Vespa, and a computer repair shop.
  - `shopping` (851) is a junk bucket, yet real food retail is buried in it —
    Ada Swalayan (a local supermarket chain), Harmony Mart, Java Frozen Food.
  - Brand fill rate: **Overture 27.8% vs OSM 83.8%.**

=> Design: **name is primary, category is a weak prior.** The inverse of the Japan version.

Failures in the first version, and the fixes (do not delete this record)
-----------------------------------------------------------------------
The same work the Japan version did by eyeballing drugstore chain names was needed here in
Indonesian. **Naive substring matching misfires badly on common Indonesian words.** What
actually happened:

| token      | intent                | what it caught                                     | hits | fix |
|------------|-----------------------|----------------------------------------------------|------|-----|
| `griya`    | ADA/Griya supermarkets| Kost Harian Griya (boarding house), Perumahan griya |  136 | removed |
|            |                       | asri (housing estate), Laundry Ngaliyan Griya       |      |         |
| `matahari` | Matahari dept. store  | Nasi Ayam Pojok Matahari (a food stall)             |   25 | removed |
| `yogya`    | Yogya supermarket     | **Yogyakarta International Airport**                |   10 | removed |
| `mart`     | Harmony Mart etc.     | **S**mart id collection, Phone Mart                 |    — | word boundary `\bmart\b` |
| `toko`     | shop                  | Toko Emas (gold), Toko Sepeda (bicycles),           | many | require co-occurrence |
|            |                       | Toko Listrik (electrical), Toko Griya Springbed     |      | with a food word |
| `pasar`    | traditional market    | BPR Bank Pasar (a bank), Mie Pasar Baru (noodle     | many | anchor to start |
|            |                       | shop), Lontong Tahu Blora Pasar Johar (food stall)  |      | `^pasar\b` |

The lesson is the same shape as the Japan version: **a brand list containing common words must
be confirmed against the actual data before it is trusted.**
"""

# ---- Chain dictionaries ----
# Only strings that are unambiguous proper nouns. Adding a common word to "catch local
# chains" is exactly how the `griya` incident above happened.
CHAINS = {
    "minimarket": ["alfamart", "alfa mart", "indomaret", "indomart", "alfamidi",
                   "circle k", "lawson", "familymart", "family mart", "basmalah"],
    "supermarket": ["superindo", "super indo", "hypermart", "transmart", "carrefour",
                    "lottemart", "lotte mart", "gelael", "indogrosir", "aneka jaya",
                    "sri ratu", "clandys", "rita supermarket", "hero supermarket",
                    "ranch market", "the food hall", "foodhall"],
}

# ---- Words naming the retail format itself ----
# Used with word boundaries. Only signals strong enough to settle the format on their own,
# so a chain name is not required.
FORMAT_SUPERMARKET = ["swalayan", "toserba", "supermarket", "hypermarket", "serba ada"]
FORMAT_MINIMARKET = ["minimarket", "mini market", "mart"]

# ---- Definitely not food retail (excluded) ----
NON_FOOD = [
    # services
    "optik", "konveksi", "laundry", "bengkel", "servis", "service", "reparation",
    "reparasi", "salon", "barbershop", "pangkas", "klinik", "apotek", "apotik",
    "dokter", "rumah sakit", "puskesmas", "notaris", "asuransi", "travel", "tour",
    "percetakan", "printing", "fotocopy", "photocopy", "sablon", "bordir",
    "advertising", "studio", "gym", "fitness", "rental", "workshop", "garage",
    # finance — catches "Bank Pasar"
    "bank", "bpr", "pegadaian", "koperasi", "leasing", "kredit",
    # lodging and property — prevents the `griya` / `kost` failure recurring
    "hotel", "wisma", "kost", "kos ", "penginapan", "villa", "perumahan",
    "properti", "real estate", "residence", "apartemen", "guest house", "homestay",
    # non-food goods
    "toko emas", "toko mas", "emas ", "perhiasan", "sepeda", "listrik", "elektronik",
    "electronic", "komputer", "computer", "handphone", "ponsel", "konter", "counter",
    "pulsa", "springbed", "kasur", "furniture", "mebel", "meubel", "bangunan",
    "material", "besi", "baja", "steel", "keramik", "kaca", "cat tembok", "toko cat",
    "onderdil", "sparepart", "spare part", "ban ", "oli ", "aki ", "helm",
    "sepatu", "sandal", "butik", "boutique", "fashion", "aksesoris", "kain",
    "tekstil", "batik", "buku", "stationery", "mainan", "tamiya", "sticker",
    "packaging", "plastik", "kimia", "pupuk", "pakan", "pet shop", "petshop",
    "aquarium", "burung", "tanaman", "bunga", "florist", "obat ",
    # education and other
    "les privat", "bimbel", "kursus", "sekolah", "kampus", "universitas",
    "airport", "bandara", "stasiun", "terminal", "agen bus", "ekspedisi",
    "cargo", "logistik", "gudang",
    # religious goods and clothing — "Grosir Sajadah" (prayer mats) had landed in kelontong
    "sajadah", "mukena", "umroh", "umrah", "hajj", "haji", "pakaian", "baju",
    "jilbab", "hijab", "songkok", "peci",
]

# ---- Corporate entities (wholesale / manufacturing / trading, not retail outlets) ----
# "PT. Java Agritech", "Jawa Muna Agro PT", "Slamet Widodo. CV" had landed in
# toko_kelontong. These are not premises a consumer walks into, so they leave the master.
# Must be matched on word boundaries or "PT" hits mid-word.
B2B_ENTITY = ["pt", "cv", "ud", "tbk", "persero", "distributor", "importir",
              "eksportir", "manufaktur", "pabrik", "industri"]

# ---- Prepared food (not food *retail*) ----
# Indonesia has warung makan / warteg / rumah makan in enormous numbers; without this the
# master fills up with eateries.
EATERY = [
    "warung makan", "warteg", "warmindo", "rumah makan", "restoran", "restaurant",
    "resto", "cafe", "kafe", "coffee", "kopi", "ngopi", "kedai", "burjo",
    "bakso", "soto", "sate", "satay", "nasi goreng", "nasi padang", "nasi ayam",
    "ayam goreng", "ayam bakar", "ayam geprek", "mie ayam", "mi ayam", "bakmi",
    "mie ", "lontong", "pecel", "gudeg", "rawon", "pempek", "seblak", "dimsum",
    "sushi", "ramen", "pizza", "burger", "steak", "fried chicken", "kfc",
    "es teh", "es krim", "ice cream", "juice", "jus ", "boba", "milk tea",
    "martabak", "gorengan", "catering", "katering", "depot", "angkringan",
    "lesehan", "food court", "foodcourt", "kantin", "bistro", "lounge", "canteen",
    "geblek", "popcorn", "snack &", "eatery",
]

# ---- Words indicating food retail ----
# Generic words like `toko` / `warung` / `agen` require co-occurrence with one of these.
FOOD_SIGNAL = [
    "sembako", "kelontong", "grosir", "beras", "sayur", "buah", "daging", "ikan",
    "telur", "minuman", "makanan", "frozen food", "frozen", "bahan kue",
    "bahan roti", "oleh-oleh", "oleh oleh", "madu", "susu", "kue", "roti",
    "bumbu", "rempah", "gula", "minyak goreng", "mracang", "pracangan",
]

FRESH = ["buah", "sayur", "daging", "ikan", "seafood", "rumah potong", "jagal",
         "fruit", "vegetable", "butcher", "unggas", "ayam potong"]


def _like(col, words):
    """Substring match; NULL becomes false.

    `coalesce` is mandatory. From the Japan-side CLAUDE.md: writing exclusions as
    `where not (...)` silently drops NULL rows, because `ilike` returns NULL and
    `not(NULL)` is not true — so every record with a missing name disappears.
    """
    if not words:
        return "false"
    inner = " or ".join(f"{col} ilike '%{w}%'" for w in words)
    return f"coalesce({inner}, false)"


def _word(col, words):
    """Word-boundary match. Prevents the class of bug where `mart` matches `Smart`.

    DuckDB uses RE2, so `\\b` is available; `(?i)` makes it case-insensitive.
    """
    if not words:
        return "false"
    alt = "|".join(w.replace(" ", r"\s+") for w in words)
    return f"coalesce(regexp_matches({col}, '(?i)\\b({alt})\\b'), false)"


def _starts(col, words):
    """Match anchored to the start of the name. This is what makes `pasar` usable."""
    alt = "|".join(w.replace(" ", r"\s+") for w in words)
    return f"coalesce(regexp_matches(trim({col}), '(?i)^({alt})\\b'), false)"


def classify_overture_sql(name_col="name", cat_col="category"):
    """CASE expression assigning an Overture record to a shared category; NULL means drop.

    Ordered most-trustworthy signal first:
      1. chain name (only unambiguous proper nouns)
      2. exclusions (non-food, eateries, corporate entities)
      3. format words, then other name-based rules
      4. category, as a weak prior
    """
    mini_chain = _like(name_col, CHAINS["minimarket"])
    sup_chain = _like(name_col, CHAINS["supermarket"])
    nonfood = _like(name_col, NON_FOOD)
    eatery = _like(name_col, EATERY)
    b2b = _word(name_col, B2B_ENTITY)
    sup_fmt = _word(name_col, FORMAT_SUPERMARKET)
    mini_fmt = _word(name_col, FORMAT_MINIMARKET)
    pasar = _starts(name_col, ["pasar"])
    fresh = _word(name_col, FRESH)
    food_sig = _like(name_col, FOOD_SIGNAL)
    generic_shop = _word(name_col, ["toko", "warung", "agen", "kios", "depo"])

    return f"""
    case
      -- 1. Chain names win. "Indomaret Point Pemuda" is filed under category='shopping',
      --    so the chain check has to run before any category logic.
      when {mini_chain} then 'minimarket'
      when {sup_chain}  then 'supermarket'
      -- 2. Exclusions. Without these the Semarang master fills with warung makan
      --    and wholesale companies.
      when {nonfood} then null
      when {eatery}  then null
      when {b2b}     then null
      -- 3. Format words. Placed before the pasar rule so that
      --    "ADA Fatmawati Pasar Swalayan" is classed as supermarket, not pasar.
      when {sup_fmt}  then 'supermarket'
      when {mini_fmt} then 'minimarket'
      when {pasar}    then 'pasar'
      -- 4. Fresh produce needs a generic shop word AND a fresh word ("Toko Buah").
      when {generic_shop} and {fresh} then 'fresh_food'
      -- 5. **Generic word + food word beats category.** "Toko Sembako Bu Ratmi" carries
      --    Overture category='supermarket'; checking category first turned a corner shop
      --    into a supermarket (this actually happened in v2).
      when {generic_shop} and {food_sig} then 'toko_kelontong'
      -- 6. Category as a weak prior, only where the name offers nothing. A generic word
      --    with no food word ("Toko Renata") is dropped rather than trusted to category,
      --    because Overture's category is 98% Meta-derived and unreliable.
      when {generic_shop} then null
      when {cat_col} = 'convenience_store' then 'minimarket'
      when {cat_col} = 'supermarket' then 'supermarket'
      when {cat_col} in ('farmers_market','market','public_market') then 'pasar'
      when {cat_col} in ('butcher_shop','seafood_market','fruits_and_vegetables')
        then 'fresh_food'
      when {cat_col} = 'grocery_store' then 'toko_kelontong'
      else null
    end"""


def classify_osm_sql(shop_col="shop", amenity_col="amenity", name_col="name"):
    """OSM tags are hand-placed, so **trust the tags** — the opposite of Overture.

    Measured: brand fill rate on convenience stores is OSM 83.8% vs Overture 27.8%.
    OSM Indonesia is largely HOT and local-mapper survey work, so tag quality is high.
    Only a minimal name-based noise filter is applied.
    """
    nonfood = _like(name_col, NON_FOOD)
    eatery = _like(name_col, EATERY)
    bad = f"({nonfood} or {eatery})"
    return f"""
    case
      when {amenity_col} = 'marketplace' then 'pasar'
      when {shop_col} = 'supermarket' then 'supermarket'
      when {shop_col} = 'convenience' then case when {bad} then null else 'minimarket' end
      when {shop_col} in ('greengrocer','butcher','seafood','fishmonger','dairy','farm',
                          'frozen_food','spices') then 'fresh_food'
      when {shop_col} in ('general','kiosk','grocery') then
        case when {bad} then null else 'toko_kelontong' end
      else null
    end"""


CATEGORIES = ["minimarket", "supermarket", "pasar", "toko_kelontong", "fresh_food"]
