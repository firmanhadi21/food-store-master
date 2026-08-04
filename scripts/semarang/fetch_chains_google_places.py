#!/usr/bin/env python3
"""
Google Places API (New) で Alfamart / Indomaret の実店舗数を数え、マスターを外部検証する。

なぜ必要か
----------
マスターのチェーン店数（Alfamart 182 / Indomaret 216）が実数に対して何割なのかが未検証。
日本版が商業動態統計・JFA で行った「数量の裏取り」に相当する工程で、これが無いと
「マスターは信用してよいか」に答えられない。

公式店舗ロケーターは使えない（実測）:
  - Alfagift  webcommerce-gw.alfagift.id/v2/stores/coordinate/candidate-list → **401**（要ログイン）
  - klikindomaret www.klikindomaret.com/webapi/api/store/*                   → **403**（WAF）
  認証やWAFの回避は各社の利用規約に反するため行わない。
  → 第三者かつ規約上正当な Google Places API を独立ソースとして使う。

設計
----
- Text Search は 1 リクエストあたり最大 20 件・ページング上限 60 件。市域全体を1回では
  取り切れないので**グリッドに分割**し、セルごとに検索して place id で名寄せする。
- **60 件返ってきたセルは切り捨てられている疑い**があるので警告し、細分化を促す。
- 課金が発生するので **既定は dry-run**。件数と概算コストを表示するだけで API は叩かない。
  実行するには `--run` を明示する。レスポンスはキャッシュし再実行で二重課金しない。

使い方
------
  # 1. まず見積もり（課金なし）
  python3 scripts/semarang/fetch_chains_google_places.py

  # 2. キーを環境変数で渡して実行（キーを引数に書かない＝履歴に残さない）
  export GOOGLE_MAPS_API_KEY='...'      # または直前に読み込む
  python3 scripts/semarang/fetch_chains_google_places.py --run

出力: data/semarang/google_chains_semarang.parquet
      docs/semarang/検証_チェーン実数_Google突合.csv
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

import duckdb

D = "data/semarang"
POLY = f"{D}/semarang_boundary_poly.geojson"
CACHE = f"{D}/google_cache"
OUT = f"{D}/google_chains_semarang.parquet"
OUT_CSV = "docs/semarang/検証_チェーン実数_Google突合.csv"

def h(t):
    print(f"\n{chr(61)*72}\n{t}\n{chr(61)*72}")


ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
# Pro ティアの最小構成。rating 等の Enterprise フィールドは要求しない（課金が上がる）
FIELD_MASK = ("places.id,places.displayName,places.location,"
              "places.formattedAddress,places.primaryType")

CHAINS = ["Alfamart", "Indomaret"]
CELL_KM = 2.0          # グリッド間隔。1セル内の店舗数が 60 を超えない粒度
PAGE_LIMIT = 3         # Text Search のページング上限（20×3=60）
COST_PER_1K = 32.0     # Text Search Pro の概算単価(USD)。実際の請求は契約による


def grid_cells():
    """市域ポリゴンに掛かる CELL_KM 格子のセル（矩形）を返す。"""
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    xmin, xmax, ymin, ymax = con.execute(
        "select ST_XMin(geom), ST_XMax(geom), ST_YMin(geom), ST_YMax(geom) from kota"
    ).fetchone()
    dlat = CELL_KM / 111.320
    dlon = CELL_KM / (111.320 * 0.99255)
    cells = []
    y = ymin
    while y < ymax:
        x = xmin
        while x < xmax:
            # セル矩形が市域と交差するものだけ残す（無駄な課金を避ける）
            hit, = con.execute(
                "select count(*) from kota where ST_Intersects(geom, "
                f"ST_MakeEnvelope({x}, {y}, {x + dlon}, {y + dlat}))").fetchone()
            if hit:
                cells.append((y, x, y + dlat, x + dlon))
            x += dlon
        y += dlat
    return cells


def search(chain, cell, key):
    """1セル分を検索。ページングして最大 60 件返す。キャッシュがあれば使う。"""
    os.makedirs(CACHE, exist_ok=True)
    tag = f"{chain}_{cell[0]:.4f}_{cell[1]:.4f}".replace("-", "m").replace(".", "_")
    cpath = os.path.join(CACHE, f"{tag}.json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f), True

    out, token = [], None
    for _ in range(PAGE_LIMIT):
        body = {
            "textQuery": chain,
            "locationRestriction": {"rectangle": {
                "low": {"latitude": cell[0], "longitude": cell[1]},
                "high": {"latitude": cell[2], "longitude": cell[3]}}},
        }
        if token:
            body["pageToken"] = token
        req = urllib.request.Request(
            ENDPOINT, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "X-Goog-Api-Key": key,
                     "X-Goog-FieldMask": FIELD_MASK})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            sys.exit(f"\nAPI エラー {e.code}: {msg}\n"
                     "（401/403 ならキー未設定・Places API (New) 未有効化・"
                     "キーの API 制限を確認）")
        out.extend(data.get("places", []))
        token = data.get("nextPageToken")
        if not token:
            break
        time.sleep(2)  # pageToken は発行直後だと無効なことがある
    with open(cpath, "w") as f:
        json.dump(out, f)
    return out, False


def main():
    run = "--run" in sys.argv
    cells = grid_cells()
    n_req = len(cells) * len(CHAINS)
    print(f"市域に掛かる {CELL_KM}km セル: {len(cells)} 個")
    print(f"チェーン {len(CHAINS)} 件 × セル = **最小 {n_req} リクエスト**"
          f"（ページングで最大 {n_req * PAGE_LIMIT}）")
    print(f"概算コスト: ${n_req * COST_PER_1K / 1000:.2f} 〜 "
          f"${n_req * PAGE_LIMIT * COST_PER_1K / 1000:.2f} "
          f"(Text Search Pro ${COST_PER_1K}/1000 と仮定)")

    if not run:
        print("\n※ dry-run です。API は叩いていません。")
        print("  実行するには GOOGLE_MAPS_API_KEY を設定して --run を付けてください。")
        return

    key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("GOOGLE_MAPS_API_KEY が未設定。キーは引数でなく環境変数で渡すこと。")

    rows, saturated = {}, []
    for chain in CHAINS:
        hit_cache = 0
        for i, cell in enumerate(cells, 1):
            places, cached = search(chain, cell, key)
            hit_cache += cached
            if len(places) >= 20 * PAGE_LIMIT:
                saturated.append((chain, cell))
            for p in places:
                loc = p.get("location") or {}
                rows[p["id"]] = {
                    "place_id": p["id"],
                    "chain": chain,
                    "name": (p.get("displayName") or {}).get("text"),
                    "address": p.get("formattedAddress"),
                    "primary_type": p.get("primaryType"),
                    "lat": loc.get("latitude"), "lon": loc.get("longitude"),
                }
            if i % 20 == 0:
                print(f"  {chain}: {i}/{len(cells)} セル "
                      f"(キャッシュ {hit_cache}) 累計 {len(rows):,} 件")
        print(f"  {chain}: 完了。キャッシュ利用 {hit_cache}/{len(cells)}")

    if saturated:
        print(f"\n⚠ 60件上限に達したセルが {len(saturated)} 個。"
              "取りこぼしの可能性があるので CELL_KM を小さくして再実行を検討。")

    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    con.register("r", __import__("pandas").DataFrame(list(rows.values())))
    con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{POLY}')")
    # ★ Text Search は矩形の外の店も返すことがある（locationRestriction は厳密でない場合が
    #   ある）ので、市域ポリゴンで必ずクリップする。
    con.execute("""create table g as select * from r
      where lat is not null and exists (
        select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")
    # ブランド名を含まないものを除外（"Alfamart" 検索で無関係な店が混ざる）
    con.execute("""create or replace table g as select * from g
      where lower(name) like '%' || lower(chain) || '%'""")
    con.execute(f"copy g to '{OUT}' (FORMAT parquet)")
    n, = con.execute("select count(*) from g").fetchone()
    print(f"\n市域内・ブランド名一致 {n:,} 件 -> {OUT}")

    # ---- Google 側の重複診断 ----
    # 比が 0.5 前後に出たとき、「マスターが半分取りこぼしている」のか
    # 「Google が二重計上している」のかを分離しないと解釈できない。
    # Google Places は同一店舗を別 place_id で持つことがある（Point/Fresh 等の派生業態、
    # ATM・宅配受取地点、閉店済みの残存）。
    h("Google 側の内部重複（同一チェーンが 50m 以内）")
    for chain in CHAINS:
        dup, = con.execute(f"""
          select count(*) from g a where a.chain='{chain}' and exists (
            select 1 from g b where b.chain='{chain}' and b.place_id != a.place_id
              and 111320*sqrt(power(a.lat-b.lat,2)
                + power((a.lon-b.lon)*cos(radians(a.lat)),2)) <= 50)""").fetchone()
        tot, = con.execute(f"select count(*) from g where chain='{chain}'").fetchone()
        print(f"  {chain:12s} {dup:>4,}/{tot:<5,} = {dup/tot*100:5.1f}% が 50m 以内に同チェーン他店")
    print("  ※ 高いほど Google 側の二重計上が疑わしい（実店舗が 50m 以内に並ぶことは稀）")

    h("Google 側の名称バリエーション（派生業態・非店舗の混入確認）")
    for row in con.execute("""
        select chain, name, count(*) c from g
        where lower(name) not in (lower(chain))
        group by 1,2 order by c desc limit 15""").fetchall():
        print(f"  {row[0]:11s} {str(row[1])[:44]:46s} {row[2]:>3,}")

    h("マスターとの突合")
    con.execute(f"""create table m as
      select * from read_parquet('{D}/semarang_food_master.parquet')""")
    out_rows = []
    print(f"  {'チェーン':12s} {'Google':>7s} {'マスター':>8s} {'比':>6s} "
          f"{'100m一致':>9s} {'Google独自':>10s}")
    for chain in CHAINS:
        gc, = con.execute(f"select count(*) from g where chain='{chain}'").fetchone()
        mc, = con.execute(
            f"select count(*) from m where name ilike '%{chain}%'").fetchone()
        match, = con.execute(f"""
          select count(*) from g where chain='{chain}' and exists (
            select 1 from m where m.name ilike '%{chain}%'
              and 111320*sqrt(power(m.lat-g.lat,2)
                + power((m.lng-g.lon)*cos(radians(g.lat)),2)) <= 100)""").fetchone()
        ratio = mc / gc if gc else 0
        print(f"  {chain:12s} {gc:>7,} {mc:>8,} {ratio:>6.2f} {match:>9,} {gc - match:>10,}")
        out_rows.append((chain, gc, mc, round(ratio, 3), match, gc - match))

    os.makedirs("docs/semarang", exist_ok=True)
    # ★ DuckDB は識別子を数字で始められない。"100m一致" は Parser Error になるので
    #   列名を英字始まりにする（実際に踏んだ）。
    con.execute('create table res(chain varchar, google_n bigint, master_n bigint, '
                'master_ratio double, match_100m bigint, google_only bigint)')
    con.executemany("insert into res values (?,?,?,?,?,?)", out_rows)
    con.execute(f"copy res to '{OUT_CSV}' (header, delimiter ',')")
    print(f"\n出力: {OUT_CSV}")
    print("\n※ Google Places も悉皆ではない（第三者データ）。3ソース目として扱い、"
          "\n  「マスター比が 1 に近いか」ではなく「桁が合うか・大きな穴が無いか」を見る。")


if __name__ == "__main__":
    main()
