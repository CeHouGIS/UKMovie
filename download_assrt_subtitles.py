#!/usr/bin/env python3
"""Search Assrt's official API for catalog works, with caching and rate limiting."""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://api.assrt.net/v1/sub/search"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def existing_ids(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("imdb_id") and row.get("api_status") == 0:
            done.add(row["imdb_id"])
    return done


def search(token: str, query: str, count: int) -> dict:
    url = API_URL + "?" + urllib.parse.urlencode(
        {"q": query, "cnt": count, "filelist": 1}
    )
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "UKMovie academic metadata collector/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def includes_english(candidate: dict) -> bool:
    language = candidate.get("lang") or {}
    language_list = language.get("langlist") or {}
    if language_list.get("langeng") is True:
        return True
    return "英" in str(language.get("desc") or "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="uk_filming_work_catalog.csv")
    parser.add_argument("--output", default="subtitle_output/assrt/search_results.jsonl")
    parser.add_argument("--limit", type=int, default=20, help="0 means all works")
    parser.add_argument("--candidates", type=int, default=15)
    parser.add_argument("--interval", type=float, default=13.0)
    args = parser.parse_args()

    load_env(Path(".env"))
    load_env(Path(".env.subtitles"))
    token = os.environ.get("ASSRT_TOKEN") or os.environ.get("ASSRT_API_TOKEN")
    if not token:
        raise SystemExit("ASSRT_TOKEN is missing from .env or the environment")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    done = existing_ids(output)
    selected: list[dict[str, str]] = []
    queued = set(done)
    with open(args.catalog, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("imdb_id") or row["imdb_id"] in queued:
                continue
            selected.append(row)
            queued.add(row["imdb_id"])
            if args.limit > 0 and len(selected) >= args.limit:
                break

    print(f"Queued {len(selected)} works; cached {len(done)}; interval {args.interval:.1f}s")
    for index, row in enumerate(selected, 1):
        year = (row.get("release_or_first_broadcast_date") or "")[:4]
        query = " ".join(part for part in (row["work_name"], year) if part)
        started = time.monotonic()
        record = {
            "wikidata_id": row.get("work_wikidata_id"),
            "imdb_id": row["imdb_id"],
            "work_name": row["work_name"],
            "work_type": row.get("work_type"),
            "release_date": row.get("release_or_first_broadcast_date"),
            "query": query,
        }
        try:
            payload = search(token, query, args.candidates)
            record["api_status"] = payload.get("status")
            record["api_message"] = payload.get("errmsg") or payload.get("message")
            all_candidates = (payload.get("sub") or {}).get("subs") or []
            record["candidate_count_before_language_filter"] = len(all_candidates)
            record["candidates"] = [
                candidate for candidate in all_candidates if includes_english(candidate)
            ]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"

        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        count = len(record.get("candidates", []))
        print(f"[{index}/{len(selected)}] {row['imdb_id']} {row['work_name']}: {count}")

        if index < len(selected):
            elapsed = time.monotonic() - started
            time.sleep(max(0.0, args.interval - elapsed))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
