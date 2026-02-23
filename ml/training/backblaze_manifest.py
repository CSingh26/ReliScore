#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_SOURCE_URL = "https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data"


@dataclass(frozen=True)
class ManifestEntry:
    dataset_id: str
    year: int
    period: str
    url: str
    file_name: str


def _extract_year_period(file_name: str) -> tuple[int | None, str]:
    quarter_patterns = [
        re.compile(r"(?i)(?:^|[_\-])Q([1-4])[_\-]?((?:19|20)\d{2})"),
        re.compile(r"(?i)((?:19|20)\d{2})[_\-]?Q([1-4])"),
    ]

    for pattern in quarter_patterns:
        match = pattern.search(file_name)
        if not match:
            continue

        groups = match.groups()
        if pattern.pattern.startswith("(?i)(?:^|[_\\-])Q"):
            quarter, year = groups
        else:
            year, quarter = groups
        return int(year), f"Q{quarter}"

    annual_match = re.search(r"((?:19|20)\d{2})", file_name)
    if annual_match:
        return int(annual_match.group(1)), "ANNUAL"

    return None, "UNKNOWN"


def _is_candidate_zip(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.path.lower().endswith(".zip"):
        return False

    lowered = url.lower()
    return any(
        marker in lowered
        for marker in [
            "hard-drive-data",
            "hard_drive_data",
            "drive-stats",
            "drivestats",
            "backblaze",
        ]
    )


def _period_order(period: str) -> int:
    if period == "ANNUAL":
        return 0
    if period.startswith("Q") and len(period) == 2 and period[1].isdigit():
        return int(period[1])
    return 99


def build_manifest(
    source_url: str,
    out_path: Path,
    include_year_from: int,
    include_year_to: int | None,
) -> dict:
    response = requests.get(source_url, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    seen: set[str] = set()
    entries: list[ManifestEntry] = []

    for link in soup.find_all("a", href=True):
        href = str(link["href"]).strip()
        full_url = urljoin(source_url, href)
        if full_url in seen or not _is_candidate_zip(full_url):
            continue

        file_name = Path(urlparse(full_url).path).name
        year, period = _extract_year_period(file_name)
        if year is None:
            continue

        seen.add(full_url)
        entries.append(
            ManifestEntry(
                dataset_id=f"{year}_{period}_{file_name}",
                year=year,
                period=period,
                url=full_url,
                file_name=file_name,
            )
        )

    if not entries:
        raise RuntimeError(f"No Backblaze dataset ZIP links found at {source_url}")

    detected_latest_year = max(item.year for item in entries)
    year_to = include_year_to if include_year_to is not None else detected_latest_year

    filtered = [
        item
        for item in entries
        if include_year_from <= item.year <= year_to
    ]

    filtered.sort(key=lambda item: (item.year, _period_order(item.period), item.file_name))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "include_year_from": include_year_from,
        "include_year_to": year_to,
        "detected_latest_year": detected_latest_year,
        "datasets": [
            {
                "dataset_id": item.dataset_id,
                "year": item.year,
                "period": item.period,
                "file_name": item.file_name,
                "url": item.url,
            }
            for item in filtered
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved manifest with {len(filtered)} datasets to {out_path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build manifest for all Backblaze Drive Stats ZIP files")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/backblaze/manifest.json"),
        help="Output manifest JSON path",
    )
    parser.add_argument(
        "--source-url",
        type=str,
        default=DEFAULT_SOURCE_URL,
        help="Backblaze source page URL",
    )
    parser.add_argument("--include_year_from", type=int, default=2013)
    parser.add_argument("--include_year_to", type=int, default=None)
    args = parser.parse_args()

    build_manifest(
        source_url=args.source_url,
        out_path=args.out,
        include_year_from=args.include_year_from,
        include_year_to=args.include_year_to,
    )


if __name__ == "__main__":
    main()
