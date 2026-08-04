#!/usr/bin/env python3
"""Overture の grocery_store / shopping の中身を実際に読んで、
インドネシア語の浄化ルール（残す語・落とす語）を実データから決めるための下見。

日本版は grocery_store が「街の商店 / スーパーチェーン誤分類 / カフェ・雑貨ノイズ」の
3種混在だった。インドネシアでは warung makan（食堂）系のノイズが桁違いに多いはずなので、
推測でキーワードを書かず現物を見る。
"""
import duckdb

D = "data/semarang"
con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute(f"create table kota as select geom::GEOMETRY geom from ST_Read('{D}/semarang_boundary_poly.geojson')")
con.execute(f"""create table ov as
  select name, category, category_alt, confidence, brand_name
  from read_parquet('{D}/overture_semarang_all.parquet')
  where exists (select 1 from kota k where ST_Contains(k.geom, ST_Point(lon, lat)))""")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("① grocery_store の名称サンプル 60 件（confidence 降順）")
for r in con.execute("""select name, round(confidence,2) from ov
    where category='grocery_store' and name is not null
    order by confidence desc limit 60""").fetchall():
    print(f"  {r[1]}  {r[0]}")

h("② grocery_store の名称 先頭語の頻度（語彙の当たりをつける）")
for r in con.execute("""
    select lower(split_part(trim(name), ' ', 1)) w, count(*) c from ov
    where category='grocery_store' and name is not null
    group by 1 having count(*) >= 2 order by c desc limit 30""").fetchall():
    print(f"  {str(r[0]):20s} {r[1]:>4,}")

h("③ 飲食系ノイズ語が grocery_store にどれだけ混ざっているか")
NOISE = ['warung', 'warteg', 'rumah makan', 'resto', 'cafe', 'kopi', 'kedai',
         'bakso', 'soto', 'sate', 'nasi', 'ayam', 'mie', 'mi ', 'es ', 'jus',
         'catering', 'depot', 'seafood', 'steak', 'pizza', 'roti', 'kue',
         'martabak', 'gorengan', 'juice', 'boba', 'dimsum']
for kw in NOISE:
    c, = con.execute(
        f"select count(*) from ov where category='grocery_store' and name ilike '%{kw}%'"
    ).fetchone()
    if c:
        print(f"  {kw:14s} {c:>4,}")

h("④ 非食品ノイズ語")
NONFOOD = ['konter', 'counter', 'pulsa', 'servis', 'service', 'bengkel', 'salon',
           'laundry', 'butik', 'fashion', 'aksesoris', 'optik', 'apotek', 'klinik',
           'bangunan', 'material', 'elektronik', 'komputer', 'hp ', 'motor']
for kw in NONFOOD:
    c, = con.execute(
        f"select count(*) from ov where category='grocery_store' and name ilike '%{kw}%'"
    ).fetchone()
    if c:
        print(f"  {kw:14s} {c:>4,}")

h("⑤ 食料品店を示す語（残すべきもの）")
KEEP = ['toko', 'sembako', 'kelontong', 'minimarket', 'swalayan', 'mart', 'pasar',
        'agen', 'grosir', 'jaya', 'berkah', 'barokah', 'makmur', 'sumber', 'buah',
        'sayur', 'daging', 'ikan', 'beras', 'telur']
for kw in KEEP:
    c, = con.execute(
        f"select count(*) from ov where category='grocery_store' and name ilike '%{kw}%'"
    ).fetchone()
    if c:
        print(f"  {kw:14s} {c:>4,}")

h("⑥ category='shopping'（851件・最大の未分類プール）の中身")
for r in con.execute("""select name, round(confidence,2) from ov
    where category='shopping' and name is not null
    order by confidence desc limit 30""").fetchall():
    print(f"  {r[1]}  {r[0]}")

h("⑦ convenience_store のうち Alfamart/Indomaret 以外は何か")
for r in con.execute("""select name, round(confidence,2) from ov
    where category='convenience_store' and name is not null
      and name not ilike '%alfamart%' and name not ilike '%indomaret%'
      and name not ilike '%alfamidi%'
    order by confidence desc limit 30""").fetchall():
    print(f"  {r[1]}  {r[0]}")
