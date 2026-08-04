#!/usr/bin/env python3
"""
Overture Places から Kota Semarang（インドネシア・中部ジャワ州）の POI を全件抽出する。

日本版（scripts/extract_overture_full.sql）との違い:
  - カテゴリで絞らず **bbox 内を全件取る**。インドネシアの食料品小売がどの Overture
    カテゴリに落ちているかが未知のため、先に実データを見てからカテゴリを決める。
    Semarang の bbox は小さいので全件でも数万件に収まる。
  - 出力に `categories.primary` だけでなく `alternate` も残す（日本版で grocery_store の
    浄化に alternate が効いたのと同じ理由）。

出力: data/semarang/overture_semarang_all.parquet
使い方: python3 scripts/semarang/extract_overture_semarang.py
"""
import os
import sys

import duckdb

# Kota Semarang の外接矩形（やや余裕を持たせる。南は Gunungpati/Mijen の丘陵、北は海岸）
BBOX = dict(xmin=110.20, xmax=110.56, ymin=-7.25, ymax=-6.90)

RELEASE = os.environ.get("OVERTURE_RELEASE", "2026-06-17.0")
S3 = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*.parquet"
OUT = "data/semarang/overture_semarang_all.parquet"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute("SET s3_region='us-west-2';")

    print(f"release = {RELEASE}")
    print(f"bbox    = {BBOX}")
    print("S3 スキャン中（bbox の row-group 統計で絞られるので全球スキャンにはならない）...")

    con.execute(f"""
      COPY (
        SELECT
          id,
          names.primary                            AS name,
          categories.primary                       AS category,
          categories.alternate                     AS category_alt,
          confidence,
          brand.wikidata                           AS brand_wikidata,
          brand.names.primary                      AS brand_name,
          operating_status,
          addresses[1].country                     AS country,
          addresses[1].region                      AS region,
          addresses[1].locality                    AS locality,
          addresses[1].freeform                    AS address,
          list_transform(sources, s -> s.dataset)  AS datasets,
          bbox.xmin                                AS lon,
          bbox.ymin                                AS lat
        FROM read_parquet('{S3}')
        WHERE bbox.xmin BETWEEN {BBOX['xmin']} AND {BBOX['xmax']}
          AND bbox.ymin BETWEEN {BBOX['ymin']} AND {BBOX['ymax']}
      ) TO '{OUT}' (FORMAT parquet, COMPRESSION zstd);
    """)

    n, = con.execute(f"select count(*) from read_parquet('{OUT}')").fetchone()
    print(f"\n抽出 {n:,} 件 -> {OUT}")

    print("\n=== country 内訳（bbox なので国外混入を確認）===")
    for row in con.execute(
            f"select country, count(*) c from read_parquet('{OUT}') "
            "group by 1 order by c desc limit 10").fetchall():
        print(f"  {str(row[0]):6s} {row[1]:>8,}")

    print("\n=== category top 40 ===")
    for row in con.execute(
            f"select category, count(*) c from read_parquet('{OUT}') "
            "group by 1 order by c desc limit 40").fetchall():
        print(f"  {str(row[0]):40s} {row[1]:>7,}")


if __name__ == "__main__":
    sys.exit(main())
