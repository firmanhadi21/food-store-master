#!/usr/bin/env python3
"""Semarang マスターの品質検証。**偽陽性を名指しで洗い出す**のが主目的。

日本版 verify_master_quality.py と同じ思想だが、日本は「統計実数と突合して不足を測る」
のが主眼だったのに対し、Semarang は分類が名称ベースで偽陽性リスクが高いため
**過剰計上の検出を先に置く**。

アクセス解析の非対称性（日本版の教訓）:
  - 過剰（実在しない店を足す）→ 圏外の住民を誤って「圏内」にする＝**困難人口を過小評価**
  - 欠落 → 過大評価
Semarang では偽陽性の方が危険。名称ルールが緩いと空の地域に店を生やしてしまう。
"""
import os
import sys

import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semarang_food_rules import CATEGORIES  # noqa: E402

D = "data/semarang"
M = f"read_parquet('{D}/semarang_food_master.parquet')"

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")


def h(t):
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


h("① supermarket の中身を全件確認（309 件は Semarang の実感より明らかに多い）")
print("  Overture 由来 supermarket の名称 40 件:")
for r in con.execute(f"""select name, round(confidence,2) from {M}
    where cat='supermarket' and src='overture' order by confidence desc limit 40""").fetchall():
    print(f"    {r[1]}  {r[0]}")

h("② supermarket に振られた原因語の内訳")
for kw in ["superindo", "hypermart", "transmart", "carrefour", "giant ", "lotte",
           "ada swalayan", "gelael", "griya", "yogya", "luwes", "sri ratu",
           "matahari", "toserba", "swalayan", "supermarket", "aeon", "ranch"]:
    c, = con.execute(f"select count(*) from {M} where cat='supermarket' "
                     f"and name ilike '%{kw}%'").fetchone()
    if c:
        print(f"  {kw:16s} {c:>4,}")
none_kw, = con.execute(f"""select count(*) from {M} where cat='supermarket'
    and not (name ilike '%superindo%' or name ilike '%hypermart%' or name ilike '%transmart%'
      or name ilike '%carrefour%' or name ilike '%giant %' or name ilike '%lotte%'
      or name ilike '%ada swalayan%' or name ilike '%gelael%' or name ilike '%griya%'
      or name ilike '%yogya%' or name ilike '%luwes%' or name ilike '%sri ratu%'
      or name ilike '%matahari%' or name ilike '%toserba%' or name ilike '%swalayan%'
      or name ilike '%supermarket%' or name ilike '%aeon%' or name ilike '%ranch%')""").fetchone()
print(f"  (どの語にも当たらない＝OSM tag 由来) {none_kw:,}")

h("③ pasar の中身（'pasar ' 名称ルールの誤爆確認）")
print("  Overture 由来 pasar の名称 30 件:")
for r in con.execute(f"""select name from {M}
    where cat='pasar' and src='overture' limit 30""").fetchall():
    print(f"    {r[0]}")

h("④ toko_kelontong の中身（724 件・最大カテゴリ）")
for r in con.execute(f"""select name, round(confidence,2) from {M}
    where cat='toko_kelontong' and src='overture' order by random() limit 40""").fetchall():
    print(f"    {r[1]}  {r[0]}")

h("⑤ 空間重複（同カテゴリ 50m 以内に別レコード）＝ 名寄せ漏れ")
con.execute(f"create table m as select *, ST_Point(lng, lat) geom from {M}")
con.execute("create index m_ix on m using rtree(geom)")
for cat in CATEGORIES:
    r = con.execute(f"""select count(*) from m a
        where a.cat='{cat}' and exists (
          select 1 from m b where b.cat='{cat}' and b.store_id != a.store_id
            and ST_DWithin(a.geom, b.geom, 0.00045))""").fetchone()
    tot, = con.execute(f"select count(*) from m where cat='{cat}'").fetchone()
    print(f"  {cat:16s} {r[0]:>5,} / {tot:<5,} = {r[0]/tot*100:5.1f}% が50m以内に同カテゴリ他店あり")

h("⑥ 同一名称・近接（明確な重複）")
for r in con.execute("""select a.cat, a.name, count(*) c from m a
    join m b on a.cat=b.cat and a.store_id < b.store_id
      and lower(a.name)=lower(b.name)
      and ST_DWithin(a.geom, b.geom, 0.0018)
    where a.name is not null group by 1,2 order by c desc limit 15""").fetchall():
    print(f"  {r[0]:16s} {str(r[1])[:36]:38s} {r[2]}")

h("⑦ 座標品質（同一座標への集積＝ジオコーディング代表点の疑い）")
for r in con.execute("""select lat, lng, count(*) c from m
    group by 1,2 having count(*) > 1 order by c desc limit 10""").fetchall():
    print(f"  ({r[0]:.5f}, {r[1]:.5f}) に {r[2]} 件")
dup, = con.execute("""select count(*) from (
    select lat, lng from m group by 1,2 having count(*) > 1)""").fetchone()
print(f"  同一座標に複数レコードがある地点: {dup} か所")

h("⑧ 名称欠損（日本版で 495 件が NULL 起因で消えた事故があった箇所）")
for cat in CATEGORIES:
    r = con.execute(f"select count(*) filter (where name is null), count(*) "
                    f"from m where cat='{cat}'").fetchone()
    print(f"  {cat:16s} 名称なし {r[0]:>4,} / {r[1]:<5,}")
