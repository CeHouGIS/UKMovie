#!/usr/bin/env python3
"""Download UK film/TV filming locations from Wikidata into CSV and GeoJSON."""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


ENDPOINT = "https://query.wikidata.org/sparql"
OUT_DIR = Path(__file__).resolve().parent
PAGE_SIZE = 500
WORK_TYPES = {
    "Q11424": "film",
    "Q5398426": "television series",
    "Q24862": "short film",
    "Q21191270": "television series episode",
    "Q506240": "television film",
    "Q1259759": "miniseries",
    "Q15416": "television program",
    "Q1983062": "television episode",
    "Q3464665": "television season",
    "Q202866": "animated film",
    "Q526877": "web series",
    "Q1261214": "television special",
    "Q98701476": "two-part television film",
    "Q28225717": "Doctor Who serial",
    "Q79766755": "Christmas episode",
    "Q20667187": "silent short film",
}
POINT_RE = re.compile(r"Point\(([-+0-9.eE]+) ([-+0-9.eE]+)\)")


def qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1] if uri else ""


def value(binding: dict, key: str) -> str:
    return binding.get(key, {}).get("value", "")


def run_query(query: str, retries: int = 5) -> list[dict]:
    params = urllib.parse.urlencode({"query": query, "format": "json"})
    request = urllib.request.Request(
        f"{ENDPOINT}?{params}",
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "UKFilmingLocationsDataset/1.0 (Wikidata CC0 research export)",
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)["results"]["bindings"]
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))
    return []


def download() -> list[dict]:
    raw_rows: list[dict] = []
    for type_qid, type_en in WORK_TYPES.items():
        offset = 0
        while True:
            query = f"""
SELECT DISTINCT ?work ?workLabel ?location ?locationLabel
                ?coord ?address ?release ?imdb ?tmdbMovie ?tmdbTV
WHERE {{
  ?work wdt:P31 wd:{type_qid};
        wdt:P915 ?location.
  ?location wdt:P17 wd:Q145.
  OPTIONAL {{ ?location wdt:P625 ?coord. }}
  OPTIONAL {{ ?location wdt:P6375 ?address. }}
  FILTER(BOUND(?coord) || BOUND(?address))
  OPTIONAL {{ ?work wdt:P577 ?release. }}
  OPTIONAL {{ ?work wdt:P345 ?imdb. }}
  OPTIONAL {{ ?work wdt:P4947 ?tmdbMovie. }}
  OPTIONAL {{ ?work wdt:P4983 ?tmdbTV. }}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "zh-hans,zh,en".
  }}
}}
ORDER BY ?work ?location ?release
LIMIT {PAGE_SIZE}
OFFSET {offset}
"""
            page = run_query(query)
            for row in page:
                row["_type_qid"] = type_qid
                row["_type_en"] = type_en
            raw_rows.extend(page)
            print(f"{type_en}: fetched {len(page)} rows at offset {offset}", flush=True)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            time.sleep(1)
    return raw_rows


def normalize(raw_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for item in raw_rows:
        key = (
            qid(value(item, "work")),
            qid(value(item, "location")),
            item["_type_qid"],
        )
        fields = {
            "work_name": value(item, "workLabel"),
            "location_name": value(item, "locationLabel"),
            "coordinate": value(item, "coord"),
            "address": value(item, "address"),
            "release": value(item, "release"),
            "imdb_id": value(item, "imdb"),
            "tmdb_movie_id": value(item, "tmdbMovie"),
            "tmdb_tv_id": value(item, "tmdbTV"),
            "work_type": item["_type_en"],
        }
        for field, field_value in fields.items():
            if field_value:
                grouped[key][field].add(field_value)

    rows: list[dict] = []
    for (work_id, location_id, type_id), fields in grouped.items():
        coordinates = sorted(fields["coordinate"])
        longitude = latitude = ""
        if coordinates:
            match = POINT_RE.fullmatch(coordinates[0])
            if match:
                longitude, latitude = match.groups()
        releases = sorted(fields["release"])
        release_date = releases[0][:10] if releases else ""
        rows.append(
            {
                "work_wikidata_id": work_id,
                "work_name": " | ".join(sorted(fields["work_name"])),
                "work_type": next(iter(fields["work_type"]), ""),
                "release_or_first_broadcast_date": release_date,
                "location_wikidata_id": location_id,
                "location_name": " | ".join(sorted(fields["location_name"])),
                "latitude": latitude,
                "longitude": longitude,
                "address": " | ".join(sorted(fields["address"])),
                "episode_timecode_start": "",
                "episode_timecode_end": "",
                "imdb_id": " | ".join(sorted(fields["imdb_id"])),
                "tmdb_movie_id": " | ".join(sorted(fields["tmdb_movie_id"])),
                "tmdb_tv_id": " | ".join(sorted(fields["tmdb_tv_id"])),
                "wikidata_work_url": f"https://www.wikidata.org/wiki/{work_id}",
                "wikidata_location_url": f"https://www.wikidata.org/wiki/{location_id}",
                "data_source": "Wikidata P915/P625/P6375/P577",
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["work_type"],
            row["work_name"],
            row["location_name"],
            row["work_wikidata_id"],
        ),
    )


def write_outputs(rows: list[dict]) -> None:
    csv_path = OUT_DIR / "uk_filming_locations.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    features = []
    for row in rows:
        if not row["latitude"] or not row["longitude"]:
            continue
        properties = {
            key: val
            for key, val in row.items()
            if key not in {"latitude", "longitude"}
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(row["longitude"]),
                        float(row["latitude"]),
                    ],
                },
                "properties": properties,
            }
        )
    geojson_path = OUT_DIR / "uk_filming_locations.geojson"
    geojson_path.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    metadata = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "license": "Wikidata structured data: CC0",
        "rows": len(rows),
        "unique_works": len({row["work_wikidata_id"] for row in rows}),
        "rows_with_coordinates": len(features),
        "rows_with_address": sum(bool(row["address"]) for row in rows),
        "rows_with_release_date": sum(
            bool(row["release_or_first_broadcast_date"]) for row in rows
        ),
        "note": (
            "Timecode columns are intentionally blank because Wikidata does not "
            "provide reliable scene-level timestamps. Coordinates can represent "
            "a city/region centroid when the source location is not a precise site."
        ),
    }
    (OUT_DIR / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    downloaded = download()
    normalized = normalize(downloaded)
    if not normalized:
        raise SystemExit("No records downloaded")
    write_outputs(normalized)
    print(f"Wrote {len(normalized)} normalized records to {OUT_DIR}", flush=True)
