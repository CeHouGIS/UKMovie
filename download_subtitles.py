#!/usr/bin/env python3
"""Download authorised subtitles through the official OpenSubtitles API.

The script defaults to a dry run. Subtitle files, API response caches and cue
text stay in the git-ignored ``subtitle_output`` directory.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import re
import shlex
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "uk_filming_locations.csv"
ENV_FILE = ROOT / ".env.subtitles"
OUTPUT = ROOT / "subtitle_output"
API_ROOT = "https://api.opensubtitles.com/api/v1"
USER_AGENT = "UKMovieResearch v1.0"


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key not in os.environ:
            parsed = shlex.split(value)
            os.environ[key] = parsed[0] if parsed else ""


def api_request(
    path: str,
    api_key: str,
    token: str = "",
    params: dict[str, str] | None = None,
    payload: dict | None = None,
) -> dict:
    url = f"{API_ROOT}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(sorted(params.items()))
    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"OpenSubtitles HTTP {error.code}: {detail[:500]}") from error


def login(api_key: str) -> tuple[str, int | None]:
    username = os.getenv("OPENSUBTITLES_USERNAME", "")
    password = os.getenv("OPENSUBTITLES_PASSWORD", "")
    if not username or not password:
        return "", None
    result = api_request(
        "/login",
        api_key,
        payload={"username": username, "password": password},
    )
    return result.get("token", ""), result.get("user", {}).get("allowed_downloads")


def load_works() -> list[dict[str, str]]:
    works: dict[str, dict[str, str]] = {}
    with INPUT.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            imdb_id = row["imdb_id"].strip()
            if not re.fullmatch(r"tt\d+", imdb_id):
                continue
            works.setdefault(
                imdb_id,
                {
                    "imdb_id": imdb_id,
                    "work_name": row["work_name"],
                    "work_type": row["work_type"],
                    "release_date": row["release_or_first_broadcast_date"],
                },
            )
    return sorted(works.values(), key=lambda row: row["imdb_id"])


def select_file(search_result: dict) -> dict | None:
    for item in search_result.get("data", []):
        attributes = item.get("attributes", {})
        files = attributes.get("files", [])
        if not files:
            continue
        return {
            "file_id": files[0].get("file_id"),
            "file_name": files[0].get("file_name", ""),
            "language": attributes.get("language", ""),
            "release": attributes.get("release", ""),
            "download_count": attributes.get("download_count", 0),
        }
    return None


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        content = response.read()
    if content.startswith(b"\x1f\x8b"):
        content = gzip.decompress(content)
    elif content.startswith(b"PK"):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            candidates = [
                name
                for name in archive.namelist()
                if name.lower().endswith((".srt", ".vtt"))
            ]
            if not candidates:
                raise RuntimeError("Downloaded ZIP contains no SRT or VTT file")
            content = archive.read(candidates[0])
    destination.write_bytes(content)


def timestamp_ms(value: str) -> int:
    match = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{2,3})", value.strip())
    if not match:
        raise ValueError(value)
    hours, minutes, seconds = map(int, match.groups()[:3])
    fraction = match.group(4)
    millis = int(fraction) * (10 if len(fraction) == 2 else 1)
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def parse_cues(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    pattern = re.compile(
        r"(?m)^(?:\d+\n)?"
        r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{2,3})\s+-->\s+"
        r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{2,3})[^\n]*\n"
        r"(?P<text>.*?)(?=\n{2,}|\Z)",
        re.S,
    )
    cues = []
    for index, match in enumerate(pattern.finditer(text), start=1):
        cue_text = re.sub(r"<[^>]+>", "", match.group("text"))
        cues.append(
            {
                "cue_number": index,
                "start_ms": timestamp_ms(match.group("start")),
                "end_ms": timestamp_ms(match.group("end")),
                "text": " ".join(cue_text.split()),
            }
        )
    return cues


def write_manifest(rows: list[dict]) -> None:
    fields = [
        "imdb_id",
        "work_name",
        "work_type",
        "release_date",
        "status",
        "language",
        "subtitle_file",
        "cue_count",
        "duration_ms",
        "release",
        "download_count",
        "error",
    ]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "subtitle_manifest.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="en")
    parser.add_argument("--max-searches", type=int, default=20)
    parser.add_argument("--max-downloads", type=int, default=5)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Call the API; without this flag only plan the batch.",
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Search and cache results without consuming download quota.",
    )
    args = parser.parse_args()

    works = load_works()
    batch = works[args.offset : args.offset + args.max_searches]
    print(f"Works with IMDb IDs: {len(works)}")
    print(f"Planned batch: {len(batch)} (offset {args.offset})")
    for row in batch[:10]:
        print(f"  {row['imdb_id']}  {row['work_name']}")
    if not args.execute:
        print("Dry run only. Add --execute after configuring .env.subtitles.")
        return

    load_env_file()
    api_key = os.getenv("OPENSUBTITLES_API_KEY", "")
    if not api_key:
        raise SystemExit("Missing OPENSUBTITLES_API_KEY in .env.subtitles")

    cache_dir = OUTPUT / "cache"
    file_dir = OUTPUT / "files"
    cue_dir = OUTPUT / "cues"
    for directory in (cache_dir, file_dir, cue_dir):
        directory.mkdir(parents=True, exist_ok=True)

    token, allowance = login(api_key)
    if allowance is not None:
        print(f"Authenticated download allowance reported by API: {allowance}")

    manifest = []
    downloaded = 0
    for work in batch:
        row = {**work}
        try:
            cache_path = cache_dir / f"{work['imdb_id']}_{args.language}.json"
            if cache_path.exists():
                result = json.loads(cache_path.read_text(encoding="utf-8"))
            else:
                result = api_request(
                    "/subtitles",
                    api_key,
                    token,
                    params={
                        "imdb_id": work["imdb_id"][2:],
                        "languages": args.language,
                        "order_by": "download_count",
                        "order_direction": "desc",
                    },
                )
                cache_path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                time.sleep(1.1)
            selected = select_file(result)
            if not selected:
                row.update(status="not_found")
                manifest.append(row)
                continue
            row.update(selected)
            if args.search_only or downloaded >= args.max_downloads:
                row.update(status="found_not_downloaded")
                manifest.append(row)
                continue

            link = api_request(
                "/download",
                api_key,
                token,
                payload={"file_id": selected["file_id"]},
            )
            suffix = ".vtt" if selected["file_name"].lower().endswith(".vtt") else ".srt"
            subtitle_path = file_dir / f"{work['imdb_id']}_{args.language}{suffix}"
            download_file(link["link"], subtitle_path)
            cues = parse_cues(subtitle_path)
            (cue_dir / f"{work['imdb_id']}_{args.language}.json").write_text(
                json.dumps(cues, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            row.update(
                status="downloaded",
                subtitle_file=str(subtitle_path.relative_to(ROOT)),
                cue_count=len(cues),
                duration_ms=max((cue["end_ms"] for cue in cues), default=0),
            )
            downloaded += 1
            time.sleep(1.1)
        except Exception as error:
            row.update(status="error", error=str(error)[:500])
        manifest.append(row)
        write_manifest(manifest)

    write_manifest(manifest)
    print(f"Searches processed: {len(manifest)}")
    print(f"Subtitle files downloaded: {downloaded}")
    print(f"Manifest: {OUTPUT / 'subtitle_manifest.csv'}")


if __name__ == "__main__":
    main()
