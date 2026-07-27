#!/usr/bin/env python3
"""Export one row per film or television work from the location dataset."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "uk_filming_locations.csv"
OUTPUT = ROOT / "uk_filming_work_catalog.csv"
FILM_OUTPUT = ROOT / "uk_filming_film_catalog.csv"
TV_OUTPUT = ROOT / "uk_filming_tv_catalog.csv"

FILM_TYPES = {"film", "short film", "silent short film", "animated film"}

FIELDS = [
    "work_wikidata_id",
    "work_name",
    "work_type",
    "release_or_first_broadcast_date",
    "imdb_id",
    "tmdb_movie_id",
    "tmdb_tv_id",
    "wikidata_work_url",
]

def write_catalog(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    works = {}
    with SOURCE.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            key = row["work_wikidata_id"] or row["imdb_id"] or row["work_name"]
            current = works.get(key)
            candidate = {field: row.get(field, "") for field in FIELDS}
            if current is None:
                works[key] = candidate
                continue
            for field in FIELDS:
                if not current[field] and candidate[field]:
                    current[field] = candidate[field]

    rows = sorted(
        works.values(),
        key=lambda row: (
            row["release_or_first_broadcast_date"] or "9999",
            row["work_name"],
        ),
    )
    film_rows = [row for row in rows if row["work_type"] in FILM_TYPES]
    tv_rows = [row for row in rows if row["work_type"] not in FILM_TYPES]
    write_catalog(OUTPUT, rows)
    write_catalog(FILM_OUTPUT, film_rows)
    write_catalog(TV_OUTPUT, tv_rows)

    films = len(film_rows)
    television = len(tv_rows)
    with_imdb = sum(bool(row["imdb_id"]) for row in rows)
    with_date = sum(bool(row["release_or_first_broadcast_date"]) for row in rows)
    print(f"Unique works: {len(rows)}")
    print(f"Film-type works: {films}")
    print(f"Television/other works: {television}")
    print(f"Rows with IMDb ID: {with_imdb}")
    print(f"Rows with release/broadcast date: {with_date}")
    print(f"Wrote {OUTPUT.name}")
    print(f"Wrote {FILM_OUTPUT.name}")
    print(f"Wrote {TV_OUTPUT.name}")


if __name__ == "__main__":
    main()
