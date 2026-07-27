#!/usr/bin/env python3
"""Match the film catalog to licensed Internet Archive subtitle files."""

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "uk_filming_film_catalog.csv"
OUTPUT = ROOT / "internet_archive_subtitle_matches.csv"
DOWNLOAD_DIR = ROOT / "subtitle_output/internet_archive"
USER_AGENT = "UKMovieResearch/1.0 (https://github.com/CeHouGIS/UKMovie)"


def get_json(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def normalize(value):
    if isinstance(value, list):
        value = " ".join(map(str, value))
    value = str(value or "")
    value = re.sub(r"\(\s*(?:18|19|20)\d{2}\s*\)", "", value)
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def english_labels(rows):
    labels = {}
    ids = [row["work_wikidata_id"] for row in rows if row["work_wikidata_id"]]
    for start in range(0, len(ids), 50):
        batch = ids[start : start + 50]
        data = get_json(
            "https://www.wikidata.org/w/api.php",
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels",
                "languages": "en",
                "format": "json",
            },
        )
        for qid, entity in data.get("entities", {}).items():
            labels[qid] = entity.get("labels", {}).get("en", {}).get("value", "")
        time.sleep(0.1)
    return labels


def main():
    with CATALOG.open(encoding="utf-8-sig", newline="") as source:
        catalog = list(csv.DictReader(source))
    labels = english_labels(catalog)

    archive = get_json(
        "https://archive.org/advancedsearch.php",
        [
            (
                "q",
                'collection:feature_films AND mediatype:movies AND format:"SubRip"',
            ),
            ("fl[]", "identifier"),
            ("fl[]", "title"),
            ("fl[]", "year"),
            ("fl[]", "date"),
            ("fl[]", "licenseurl"),
            ("rows", "3000"),
            ("output", "json"),
        ],
    )["response"]["docs"]
    licensed = [
        item
        for item in archive
        if "creativecommons.org/" in item.get("licenseurl", "")
    ]
    by_title = defaultdict(list)
    for item in licensed:
        by_title[normalize(item.get("title", ""))].append(item)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    matches = []
    for work in catalog:
        title = labels.get(work["work_wikidata_id"], "")
        if not title:
            continue
        work_year = work["release_or_first_broadcast_date"][:4]
        for item in by_title.get(normalize(title), []):
            item_year = str(item.get("year") or item.get("date", ""))[:4]
            if work_year and item_year and work_year != item_year:
                continue
            metadata = get_json(f"https://archive.org/metadata/{item['identifier']}")
            files = [
                f["name"]
                for f in metadata.get("files", [])
                if f.get("name", "").lower().endswith((".srt", ".vtt"))
            ]
            for name in files:
                url = "https://archive.org/download/{}/{}".format(
                    item["identifier"], urllib.parse.quote(name)
                )
                destination = DOWNLOAD_DIR / (
                    work["imdb_id"] + "_" + Path(name).name.replace("/", "_")
                )
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=90) as response:
                    destination.write_bytes(response.read())
                matches.append(
                    {
                        "imdb_id": work["imdb_id"],
                        "work_name": work["work_name"],
                        "work_name_en": title,
                        "release_date": work["release_or_first_broadcast_date"],
                        "archive_identifier": item["identifier"],
                        "archive_title": item.get("title", ""),
                        "license_url": item["licenseurl"],
                        "subtitle_file": str(destination.relative_to(ROOT)),
                        "download_url": url,
                    }
                )
            time.sleep(0.1)

    fields = [
        "imdb_id",
        "work_name",
        "work_name_en",
        "release_date",
        "archive_identifier",
        "archive_title",
        "license_url",
        "subtitle_file",
        "download_url",
    ]
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(matches)
    print(f"Licensed Archive items indexed: {len(licensed)}")
    print(f"Subtitle files downloaded: {len(matches)}")
    print(f"Wrote {OUTPUT.name}")


if __name__ == "__main__":
    main()
