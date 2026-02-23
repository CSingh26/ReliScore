#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


def _remote_size(session: requests.Session, url: str) -> int | None:
    try:
        response = session.head(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length:
            return int(content_length)
    except Exception:
        return None
    return None


def _download_with_resume(session: requests.Session, url: str, target: Path) -> None:
    expected_size = _remote_size(session, url)
    existing_size = target.stat().st_size if target.exists() else 0

    if expected_size is not None and existing_size == expected_size:
        print(f"Skip (already complete): {target.name}")
        return

    headers: dict[str, str] = {}
    mode = "wb"

    if target.exists() and expected_size is not None and existing_size < expected_size:
        headers["Range"] = f"bytes={existing_size}-"
        mode = "ab"
        print(f"Resuming {target.name} at byte {existing_size}")
    elif target.exists() and expected_size is not None and existing_size > expected_size:
        target.unlink()
        existing_size = 0
    elif target.exists() and expected_size is None:
        print(f"Skip (size unknown, file exists): {target.name}")
        return

    with session.get(url, timeout=120, stream=True, headers=headers) as response:
        if response.status_code == 416 and expected_size is not None:
            print(f"Skip (range complete): {target.name}")
            return

        response.raise_for_status()
        with target.open(mode) as file_obj:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file_obj.write(chunk)

    final_size = target.stat().st_size
    if expected_size is not None and final_size != expected_size:
        raise RuntimeError(
            f"Download size mismatch for {target.name}: expected {expected_size}, got {final_size}"
        )

    print(f"Downloaded: {target.name} ({final_size} bytes)")


def download_from_manifest(manifest_path: Path, dest_dir: Path, max_files: int | None) -> list[Path]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = payload.get("datasets", [])
    if not isinstance(datasets, list) or not datasets:
        raise RuntimeError("Manifest has no dataset entries")

    if max_files is not None and max_files > 0:
        datasets = datasets[:max_files]

    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded_paths: list[Path] = []

    with requests.Session() as session:
        for item in datasets:
            url = str(item["url"])
            file_name = str(item["file_name"])
            target = dest_dir / file_name
            _download_with_resume(session, url, target)
            downloaded_paths.append(target)

    print(f"Ready ZIP files: {len(downloaded_paths)} in {dest_dir}")
    return downloaded_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Backblaze ZIP datasets from manifest")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/backblaze/manifest.json"),
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data/backblaze/zips"),
    )
    parser.add_argument(
        "--max_files",
        type=int,
        default=None,
        help="Limit files for smoke tests",
    )
    args = parser.parse_args()

    download_from_manifest(manifest_path=args.manifest, dest_dir=args.dest, max_files=args.max_files)


if __name__ == "__main__":
    main()
