#!/usr/bin/env python3
"""Geocode the Wikipedia filming-category supplement with open place data."""

from __future__ import annotations

import csv
import io
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "wikipedia_uk_filming_categories.csv"
GEONAMES_ZIP = ROOT / "data_sources/geonames/GB.zip"
LOCATION_OUTPUT = ROOT / "wikipedia_location_coordinates.csv"
RECORD_OUTPUT = ROOT / "wikipedia_uk_filming_categories_geocoded.csv"
GEOJSON_OUTPUT = ROOT / "wikipedia_uk_filming_categories_geocoded.geojson"
CACHE = ROOT / "data_sources/wikidata_location_cache.json"
USER_AGENT = "UKMovieData/1.0 (https://github.com/CeHouGIS/UKMovie)"

LOCATION_ALIASES = {
    "the United Kingdom": "United Kingdom",
    "the Scottish Borders": "Scottish Borders",
    "the East Riding of Yorkshire": "East Riding of Yorkshire",
    "the Outer Hebrides": "Outer Hebrides",
    "Highland (council area)": "Highland",
    "Stirling (council area)": "Stirling",
    "Scarborough, North Yorkshire": "Scarborough",
    "Elstree Film Studios": "Elstree Studios",
}


def normalize(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value).strip()


def load_geonames() -> dict[str, list[dict[str, str]]]:
    names: dict[str, list[dict[str, str]]] = defaultdict(list)
    with zipfile.ZipFile(GEONAMES_ZIP) as archive, archive.open("GB.txt") as raw:
        for line in io.TextIOWrapper(raw, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            record = {
                "id": parts[0],
                "name": parts[1],
                "ascii_name": parts[2],
                "latitude": parts[4],
                "longitude": parts[5],
                "feature_class": parts[6],
                "feature_code": parts[7],
                "population": parts[14] or "0",
            }
            for name in {parts[1], parts[2], *parts[3].split(",")}:
                key = normalize(name)
                if key:
                    names[key].append(record)
    return names


def best_geonames_match(name: str, index: dict[str, list[dict[str, str]]]):
    query = LOCATION_ALIASES.get(name, name)
    candidates = index.get(normalize(query), [])
    if not candidates:
        return None
    priority = {"A": 3, "P": 2, "S": 1}
    return max(
        candidates,
        key=lambda item: (
            priority.get(item["feature_class"], 0),
            int(item["population"]),
        ),
    )


def api_json(params: dict[str, str]) -> dict:
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def wikidata_coordinate(name: str, cache: dict[str, dict]) -> dict:
    if name in cache:
        return cache[name]

    query_name = LOCATION_ALIASES.get(name, name)
    search = api_json(
        {
            "action": "wbsearchentities",
            "search": query_name,
            "language": "en",
            "uselang": "en",
            "type": "item",
            "limit": "8",
            "format": "json",
        }
    )
    ids = [item["id"] for item in search.get("search", [])]
    result: dict[str, str] = {}
    if ids:
        entities = api_json(
            {
                "action": "wbgetentities",
                "ids": "|".join(ids),
                "props": "claims|labels",
                "languages": "en",
                "format": "json",
            }
        ).get("entities", {})
        for entity_id in ids:
            entity = entities.get(entity_id, {})
            matched_name = entity.get("labels", {}).get("en", {}).get("value", "")
            if normalize(matched_name) != normalize(query_name):
                continue
            statements = entity.get("claims", {}).get("P625", [])
            if not statements:
                continue
            value = statements[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
            lat, lon = value.get("latitude"), value.get("longitude")
            if lat is None or lon is None or not (49 <= lat <= 61 and -9 <= lon <= 3):
                continue
            result = {
                "latitude": str(lat),
                "longitude": str(lon),
                "wikidata_id": entity_id,
                "matched_name": matched_name,
            }
            break

    cache[name] = result
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    time.sleep(0.15)
    return result


def main() -> None:
    with INPUT.open(encoding="utf-8-sig", newline="") as source:
        records = list(csv.DictReader(source))
    locations = sorted({row["location_text_from_category"] for row in records})
    geonames = load_geonames()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    mappings: dict[str, dict[str, str]] = {}

    for location in locations:
        wikidata = wikidata_coordinate(location, cache)
        if wikidata:
            mappings[location] = {
                "location_text": location,
                **wikidata,
                "coordinate_source": "Wikidata P625",
                "coordinate_precision": "category place centroid",
                "geonames_id": "",
            }
            continue
        geoname = best_geonames_match(location, geonames)
        if geoname:
            mappings[location] = {
                "location_text": location,
                "latitude": geoname["latitude"],
                "longitude": geoname["longitude"],
                "wikidata_id": "",
                "matched_name": geoname["name"],
                "coordinate_source": "GeoNames GB",
                "coordinate_precision": "category place centroid",
                "geonames_id": geoname["id"],
            }
        else:
            mappings[location] = {
                "location_text": location,
                "latitude": "",
                "longitude": "",
                "wikidata_id": "",
                "matched_name": "",
                "coordinate_source": "",
                "coordinate_precision": "unmatched",
                "geonames_id": "",
            }

    location_fields = [
        "location_text",
        "latitude",
        "longitude",
        "matched_name",
        "wikidata_id",
        "geonames_id",
        "coordinate_source",
        "coordinate_precision",
    ]
    with LOCATION_OUTPUT.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=location_fields)
        writer.writeheader()
        writer.writerows(mappings.values())

    output_fields = list(records[0]) + [
        "latitude",
        "longitude",
        "coordinate_source",
        "coordinate_precision",
    ]
    with RECORD_OUTPUT.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=output_fields)
        writer.writeheader()
        for row in records:
            match = mappings[row["location_text_from_category"]]
            writer.writerow(
                {
                    **row,
                    "latitude": match["latitude"],
                    "longitude": match["longitude"],
                    "coordinate_source": match["coordinate_source"],
                    "coordinate_precision": match["coordinate_precision"],
                }
            )

    features = []
    for row in records:
        match = mappings[row["location_text_from_category"]]
        if not match["latitude"]:
            continue
        category = row["source_category"].lower()
        work_type = "television series" if "television" in category else "film"
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(match["longitude"]),
                        float(match["latitude"]),
                    ],
                },
                "properties": {
                    "work_wikidata_id": row["work_wikidata_id"],
                    "work_name": row["work_name_en"],
                    "work_type": work_type,
                    "release_or_first_broadcast_date": row[
                        "release_or_first_broadcast_date"
                    ],
                    "location_name": row["location_text_from_category"],
                    "address": "",
                    "imdb_id": row["imdb_id"],
                    "wikipedia_url": row["wikipedia_url"],
                    "source_category": row["source_category"],
                    "data_source": row["data_source"],
                    "record_source": "community",
                    "coordinate_precision": match["coordinate_precision"],
                },
            }
        )
    GEOJSON_OUTPUT.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    matched = sum(bool(row["latitude"]) for row in mappings.values())
    matched_records = sum(
        bool(mappings[row["location_text_from_category"]]["latitude"]) for row in records
    )
    print(f"Location categories matched: {matched}/{len(locations)}")
    print(f"Filming records geocoded: {matched_records}/{len(records)}")
    print(f"Wrote {LOCATION_OUTPUT.name}")
    print(f"Wrote {RECORD_OUTPUT.name}")
    print(f"Wrote {GEOJSON_OUTPUT.name}")


if __name__ == "__main__":
    main()
