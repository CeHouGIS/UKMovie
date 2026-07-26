#!/usr/bin/env python3
"""Export open-licensed English Wikipedia UK filming-category memberships."""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from collections import defaultdict, deque
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "UKFilmingResearch/1.0 (open Wikimedia category export)"
ROOTS = [
    "Category:Films shot in the United Kingdom",
    "Category:Television shows shot in the United Kingdom",
]
EXCLUDED_TERRITORIES = (
    "anguilla",
    "bermuda",
    "british virgin islands",
    "cayman islands",
    "dependent territories",
    "gibraltar",
    "music videos",
    "turks and caicos islands",
)
LOCATION_RE = re.compile(
    r"^Category:(?:Films|Television shows|Short films|Music videos) "
    r"(?:shot|filmed) (?:in|at|on) (.+)$",
    re.IGNORECASE,
)


def api(endpoint: str, params: dict, retries: int = 4) -> dict:
    url = endpoint + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if attempt == retries - 1:
                raise
            retry_after = error.headers.get("Retry-After")
            time.sleep(int(retry_after) if retry_after else 10 * (attempt + 1))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    return {}


def category_members(category: str) -> list[dict]:
    members: list[dict] = []
    continuation: dict = {}
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "500",
            "cmtype": "page|subcat",
            "format": "json",
            **continuation,
        }
        data = api(WIKI_API, params)
        members.extend(data["query"]["categorymembers"])
        if "continue" not in data:
            break
        continuation = data["continue"]
    return members


def category_location(category: str, inherited: str) -> str:
    match = LOCATION_RE.match(category)
    if not match:
        return inherited
    location = match.group(1)
    location = re.sub(r" by (?:city|studio|country)$", "", location)
    return location


def crawl() -> dict[str, set[tuple[str, str]]]:
    pages: dict[str, set[tuple[str, str]]] = defaultdict(set)
    queue = deque((root, "United Kingdom", 0) for root in ROOTS)
    visited: set[str] = set()
    while queue:
        category, inherited_location, depth = queue.popleft()
        if category in visited or depth > 6:
            continue
        visited.add(category)
        location = category_location(category, inherited_location)
        members = category_members(category)
        for member in members:
            title = member["title"]
            if member["ns"] == 0:
                pages[title].add((location, category))
            elif member["ns"] == 14:
                lower = title.lower()
                if (
                    (" shot " in lower or " filmed " in lower)
                    and " by year" not in lower
                    and " by decade" not in lower
                    and not any(term in lower for term in EXCLUDED_TERRITORIES)
                ):
                    queue.append((title, location, depth + 1))
        print(
            f"categories={len(visited)} pages={len(pages)} current={category}",
            flush=True,
        )
        time.sleep(2)
    return pages


def get_qids(titles: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for start in range(0, len(titles), 50):
        batch = titles[start : start + 50]
        data = api(
            WIKI_API,
            {
                "action": "query",
                "prop": "pageprops",
                "ppprop": "wikibase_item",
                "redirects": "1",
                "titles": "|".join(batch),
                "format": "json",
            },
        )
        for page in data["query"]["pages"].values():
            title = page.get("title", "")
            qid = page.get("pageprops", {}).get("wikibase_item", "")
            if title and qid:
                result[title] = qid
        normalized = {
            item["to"]: item["from"]
            for key in ("normalized", "redirects")
            for item in data["query"].get(key, [])
        }
        for canonical, original in normalized.items():
            if canonical in result:
                result[original] = result[canonical]
    return result


def get_work_metadata(qids: list[str]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for start in range(0, len(qids), 50):
        batch = qids[start : start + 50]
        data = api(
            WIKIDATA_API,
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "claims",
                "format": "json",
            },
        )
        for qid, entity in data["entities"].items():
            claims = entity.get("claims", {})
            dates = []
            for claim in claims.get("P577", []):
                datavalue = claim.get("mainsnak", {}).get("datavalue", {})
                time_value = datavalue.get("value", {}).get("time", "")
                if time_value:
                    dates.append(time_value.lstrip("+")[:10])
            imdb = ""
            if claims.get("P345"):
                imdb = (
                    claims["P345"][0]
                    .get("mainsnak", {})
                    .get("datavalue", {})
                    .get("value", "")
                )
            output[qid] = {
                "release_or_first_broadcast_date": min(dates) if dates else "",
                "imdb_id": imdb,
            }
    return output


def write(pages: dict[str, set[tuple[str, str]]]) -> None:
    titles = sorted(pages)
    rows = []
    for title in titles:
        year_match = re.search(r"\(((?:19|20)\d{2})[^)]*\)", title)
        for location, category in sorted(pages[title]):
            rows.append(
                {
                    "work_name_en": title,
                    "release_or_first_broadcast_date": (
                        year_match.group(1) if year_match else ""
                    ),
                    "location_text_from_category": location,
                    "source_category": category,
                    "work_wikidata_id": "",
                    "imdb_id": "",
                    "wikipedia_url": "https://en.wikipedia.org/wiki/"
                    + urllib.parse.quote(title.replace(" ", "_")),
                    "episode_timecode_start": "",
                    "episode_timecode_end": "",
                    "data_source": "English Wikipedia category membership",
                    "license": "CC BY-SA 4.0",
                }
            )
    path = OUT_DIR / "wikipedia_uk_filming_categories.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    stats = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "license": "CC BY-SA 4.0",
        "rows": len(rows),
        "unique_wikipedia_pages": len(pages),
        "rows_with_year_in_title": sum(
            bool(row["release_or_first_broadcast_date"]) for row in rows
        ),
        "note": (
            "Locations are inferred from Wikipedia category names and can be broad. "
            "This is a separate lower-precision supplement, not scene-level data. "
            "Wikidata/IMDb enrichment was left blank because the public API rate "
            "limited the large batch; years are retained when present in page titles."
        ),
    }
    (OUT_DIR / "wikipedia_category_metadata.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    write(crawl())
