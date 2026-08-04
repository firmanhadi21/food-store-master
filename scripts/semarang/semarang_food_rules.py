#!/usr/bin/env python3
"""Semarang 版マスターの判定ルール。構築と検証の**両方から import する**
（日本版 scripts/food_store_rules.py と同じ理由: 片方だけ直すとズレる）。

日本版との根本的な違い
----------------------
日本版は「Overture の category は信頼でき、名称判定は調剤薬局の切り分けだけ」だった。
Semarang は逆で、**category が信頼できない**。実測（inspect_grocery_names.py）:

  - Overture Semarang の原典は **98.1% が meta**（日本は meta 39.8% / AllThePlaces 25.7%）。
    Meta 由来＝Facebook ページの自己申告カテゴリなので業種分類が粗い。
  - `convenience_store` 414 件に The Backyard Cafe / Victory Cell（携帯屋）が混入。
  - `shopping` 851 件はゴミ箱だが、その中に Ada Swalayan（地場スーパー）等が埋もれている。

→ **名称を主・category を弱い事前分布として使う**設計。日本版と正反対。

★ 第1版の失敗と対策（verify_semarang_master.py で検出。この記録を消さないこと）
------------------------------------------------------------------------------
素朴に `ilike '%語%'` で書いたところ、インドネシア語の一般語が大量に誤爆した:

  - **griya**（＝家）を ADA/Griya 系スーパーのつもりで入れたら **136 件誤爆**。
    実体は "Kost Harian Griya Tegalsari"（下宿）"Perumahan griya asri"（住宅地）
    "Laundry Ngaliyan Griya Lestari"（洗濯屋）。**削除**。
  - **matahari**（＝太陽）25 件。"Nasi Ayam Pojok Matahari"（飯屋）。**削除**。
  - **yogya** 10 件。"Yogyakarta International Airport" が supermarket になった。**削除**。
  - **mart** は部分一致で "**S**mart id collection" "Phone Mart" を拾う。→ 語境界 `\bmart\b` に変更。
  - **toko**（＝店）だけでは食料品店に絞れない。"Toko Emas"（金）"Toko Sepeda"（自転車）
    "Toko Listrik"（電気）"Toko Griya Springbed"（寝具）。→ **食料品を示す語との共起を必須化**。
  - **pasar** を部分一致にすると "BPR Bank Pasar"（銀行）"Mie Pasar Baru"（麺屋）
    "Lontong Tahu Blora Pasar Johar"（屋台）を拾う。→ **名称の先頭に限定** `^pasar\\b`。

教訓は日本版と同型: **一般語を含むブランド名リストは、必ず現物を目視してから確定する。**
"""

# ---- チェーン辞書 ----
# 一般語と衝突しない、固有名詞として一意な文字列だけを置く。
# 「地場チェーンを拾いたい」欲で一般語を足すと上記の griya 事故が再発する。
CHAINS = {
    "minimarket": ["alfamart", "alfa mart", "indomaret", "indomart", "alfamidi",
                   "circle k", "lawson", "familymart", "family mart", "basmalah"],
    "supermarket": ["superindo", "super indo", "hypermart", "transmart", "carrefour",
                    "lottemart", "lotte mart", "gelael", "indogrosir", "aneka jaya",
                    "sri ratu", "clandys", "rita supermarket", "hero supermarket",
                    "ranch market", "the food hall", "foodhall"],
}

# ---- 業態を名乗る語（チェーン名を知らなくても救える）----
# 語境界付きで使う。単独で業態を確定できる強いシグナルのみ。
FORMAT_SUPERMARKET = ["swalayan", "toserba", "supermarket", "hypermarket", "serba ada"]
FORMAT_MINIMARKET = ["minimarket", "mini market", "mart"]

# ---- 明確に食料品店でないもの（除外）----
NON_FOOD = [
    # サービス業
    "optik", "konveksi", "laundry", "bengkel", "servis", "service", "reparation",
    "reparasi", "salon", "barbershop", "pangkas", "klinik", "apotek", "apotik",
    "dokter", "rumah sakit", "puskesmas", "notaris", "asuransi", "travel", "tour",
    "percetakan", "printing", "fotocopy", "photocopy", "sablon", "bordir",
    "advertising", "studio", "gym", "fitness", "rental", "workshop", "garage",
    # 金融（"Bank Pasar" 対策）
    "bank", "bpr", "pegadaian", "koperasi", "leasing", "kredit",
    # 宿泊・不動産（"Griya"/"Kost" 事故の再発防止）
    "hotel", "wisma", "kost", "kos ", "penginapan", "villa", "perumahan",
    "properti", "real estate", "residence", "apartemen", "guest house", "homestay",
    # 非食品の物販
    "toko emas", "toko mas", "emas ", "perhiasan", "sepeda", "listrik", "elektronik",
    "electronic", "komputer", "computer", "handphone", "ponsel", "konter", "counter",
    "pulsa", "springbed", "kasur", "furniture", "mebel", "meubel", "bangunan",
    "material", "besi", "baja", "steel", "keramik", "kaca", "cat tembok", "toko cat",
    "onderdil", "sparepart", "spare part", "ban ", "oli ", "aki ", "helm",
    "sepatu", "sandal", "butik", "boutique", "fashion", "aksesoris", "kain",
    "tekstil", "batik", "buku", "stationery", "mainan", "tamiya", "sticker",
    "packaging", "plastik", "kimia", "pupuk", "pakan", "pet shop", "petshop",
    "aquarium", "burung", "tanaman", "bunga", "florist", "obat ",
    # 教育・その他
    "les privat", "bimbel", "kursus", "sekolah", "kampus", "universitas",
    "airport", "bandara", "stasiun", "terminal", "agen bus", "ekspedisi",
    "cargo", "logistik", "gudang",
    # 宗教用品・衣料（"Grosir Sajadah"＝礼拝マット卸 が toko_kelontong に入った）
    "sajadah", "mukena", "umroh", "umrah", "hajj", "haji", "pakaian", "baju",
    "jilbab", "hijab", "songkok", "peci",
]

# ---- 法人格を名乗る事業体（卸・製造・商社であって小売店舗ではない）----
# "PT. Java Agritech" "Jawa Muna Agro PT" "Slamet Widodo. CV" が toko_kelontong に
# 入っていた。消費者がアクセスする「店舗」ではないのでマスターから外す。
# 語境界で判定しないと "PT" が語中に紛れる。
B2B_ENTITY = ["pt", "cv", "ud", "tbk", "persero", "distributor", "importir",
              "eksportir", "manufaktur", "pabrik", "industri"]

# ---- 飲食店（食料品「小売」ではない）----
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

# ---- 食料品小売であることを示す語 ----
# `toko`/`warung`/`agen` のような一般語は、これらとの**共起**を必須にする。
FOOD_SIGNAL = [
    "sembako", "kelontong", "grosir", "beras", "sayur", "buah", "daging", "ikan",
    "telur", "minuman", "makanan", "frozen food", "frozen", "bahan kue",
    "bahan roti", "oleh-oleh", "oleh oleh", "madu", "susu", "kue", "roti",
    "bumbu", "rempah", "gula", "minyak goreng", "mracang", "pracangan",
]

FRESH = ["buah", "sayur", "daging", "ikan", "seafood", "rumah potong", "jagal",
         "fruit", "vegetable", "butcher", "unggas", "ayam potong"]


def _like(col, words):
    """部分一致（NULL は false）。日本版の教訓どおり coalesce で包む。

    CLAUDE.md の落とし穴: `where not (…)` で NULL 行が黙って消える。
    ilike が NULL を返すと not(NULL) が真にならず、名称欠損レコードが全部落ちる。
    """
    if not words:
        return "false"
    inner = " or ".join(f"{col} ilike '%{w}%'" for w in words)
    return f"coalesce({inner}, false)"


def _word(col, words):
    """語境界つき一致。`mart` が `Smart` を拾う類の事故を防ぐ。

    DuckDB は RE2 なので `\\b` が使える。`(?i)` で大文字小文字を無視。
    """
    if not words:
        return "false"
    alt = "|".join(w.replace(" ", r"\s+") for w in words)
    return f"coalesce(regexp_matches({col}, '(?i)\\b({alt})\\b'), false)"


def _starts(col, words):
    """名称の先頭に限定した一致。`pasar` の誤爆対策。"""
    alt = "|".join(w.replace(" ", r"\s+") for w in words)
    return f"coalesce(regexp_matches(trim({col}), '(?i)^({alt})\\b'), false)"


def classify_overture_sql(name_col="name", cat_col="category"):
    """Overture レコードを共通カテゴリへ振る CASE 式。該当なしは NULL（＝除外）。

    優先順は「信頼できるシグナルから先に」:
      1. チェーン名（最強・一般語と衝突しないものだけ）
      2. 除外語（非食品・飲食店）
      3. 業態名 → 名称による分類
      4. category の弱い事前分布
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
      -- 1. チェーン名が最優先（"Indomaret Point Pemuda" が category='shopping' に
      --    落ちている実例があるため、category より先に見る）
      when {mini_chain} then 'minimarket'
      when {sup_chain}  then 'supermarket'
      -- 2. 非食品・飲食店・法人格事業体は除外。
      --    ここを通さないと Semarang は warung makan と卸売会社だらけになる
      when {nonfood} then null
      when {eatery}  then null
      when {b2b}     then null
      -- 3. 業態名。"ADA Fatmawati Pasar Swalayan" を pasar でなく supermarket にするため
      --    pasar 判定より前に置く
      when {sup_fmt}  then 'supermarket'
      when {mini_fmt} then 'minimarket'
      when {pasar}    then 'pasar'
      -- 4. 生鮮は「一般語＋生鮮語」の共起で判定（"Toko Buah" 等）
      when {generic_shop} and {fresh} then 'fresh_food'
      -- 5. **一般語＋食料品語は category より優先**する。
      --    "Toko Sembako Bu Ratmi" が Overture category='supermarket' に入っており、
      --    category を先に見ると個人商店がスーパーに化ける（第2版で実際に起きた）。
      when {generic_shop} and {food_sig} then 'toko_kelontong'
      -- 6. category を弱い事前分布として使う（名称に手がかりが無い場合のみ）。
      --    一般語だけで食料品語を伴わない名称（"Toko Renata"）は category を信用しない
      --    ＝ Overture の category は meta 由来 98% で信頼できないため。
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
    """OSM は人手タグなので**タグを信頼する**（Overture と逆）。

    実測: shop=convenience のブランド付与率は OSM 83.8% / Overture 27.8%。
    OSM Indonesia は HOT・地元マッパーの現地調査由来でタグ品質が高い。
    名称ノイズ判定だけ最小限かける。
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
