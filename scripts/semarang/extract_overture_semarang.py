#!/usr/bin/env python3
"""
Extract every Overture Places POI inside Kota Semarang, Central Java, Indonesia.

Difference from the Japan version (scripts/extract_overture_full.sql)
  - **No category filter — take everything in the bounding box.** Which Overture categories
    Indonesian food retail actually falls into was unknown at the outset, so the categories
    are chosen after looking at real data rather than before. Semarang's bounding box is
    small enough that the whole extract stays in the tens of thousands.
  - Keeps `categories.alternate` as well as `primary`, for the same reason the Japan version
    did: the alternate list was what made grocery_store cleanable there.

Output: data/semarang/overture_semarang_all.parquet
Usage:  python3 scripts/semarang/extract_overture_semarang.py
"""
import os
import sys

import duckdb

# Bounding box of Kota Semarang, with margin. South reaches the Gunungpati/Mijen hills,
# north the coast.
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
    print("scanning S3 (row-group statistics on bbox keep this from being a global scan)...")

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
    print(f"\nextracted {n:,} -> {OUT}")

    print("\n=== country breakdown (bbox extract, so check for spillover) ===")
    for row in con.execute(
            f"select country, count(*) c from read_parquet('{OUT}') "
            "group by 1 order by c desc limit 10").fetchall():
        print(f"  {str(row[0]):6s} {row[1]:>8,}")

    print("\n=== top 40 categories ===")
    for row in con.execute(
            f"select category, count(*) c from read_parquet('{OUT}') "
            "group by 1 order by c desc limit 40").fetchall():
        print(f"  {str(row[0]):40s} {row[1]:>7,}")


if __name__ == "__main__":
    sys.exit(main())
