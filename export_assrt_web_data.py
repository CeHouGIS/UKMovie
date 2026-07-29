#!/usr/bin/env python3
"""Export a compact, public-safe ASSRT metadata file for the website."""

from __future__ import annotations

import json
from pathlib import Path

SOURCE = Path("subtitle_output/assrt/search_results_english.jsonl")
OUTPUT = Path("public/data/assrt_english_subtitles.json")


def main() -> None:
    works = []
    searched = 0
    api_success = 0
    invalid_imdb = 0
    with SOURCE.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            searched += 1
            if record.get("api_status") == 0:
                api_success += 1
            imdb_id = str(record.get("imdb_id") or "")
            if not (imdb_id.startswith("tt") and imdb_id[2:].isdigit()):
                invalid_imdb += 1
            candidates = []
            for candidate in record.get("candidates") or []:
                candidates.append(
                    {
                        "id": candidate.get("id"),
                        "name": candidate.get("native_name"),
                        "video": candidate.get("videoname"),
                        "format": candidate.get("subtype"),
                        "language": (candidate.get("lang") or {}).get("desc"),
                        "score": candidate.get("vote_score"),
                        "uploaded": candidate.get("upload_time"),
                        "files": [
                            item.get("f")
                            for item in (candidate.get("filelist") or [])
                            if item.get("f")
                        ][:20],
                    }
                )
            if candidates:
                works.append(
                    {
                        "wikidata_id": record.get("wikidata_id"),
                        "imdb_id": imdb_id,
                        "name": record.get("work_name"),
                        "type": record.get("work_type"),
                        "release_date": record.get("release_date"),
                        "candidates": candidates,
                    }
                )

    payload = {
        "generated_from": "ASSRT official API search metadata",
        "language_filter": "English or multilingual including English",
        "searched_records": searched,
        "api_success": api_success,
        "invalid_imdb_records": invalid_imdb,
        "matched_works": len(works),
        "candidate_count": sum(len(work["candidates"]) for work in works),
        "works": works,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(works)} works and {payload['candidate_count']} candidates "
        f"to {OUTPUT}"
    )


if __name__ == "__main__":
    main()
