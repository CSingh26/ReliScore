import argparse
import hashlib
import zipfile
from pathlib import Path

import requests

from src.config import CACHE_ROOT

BACKBLAZE_URLS = {
    "2020_Q1": "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q1_2020.zip",
    "2020_Q2": "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q2_2020.zip",
    "2020_Q3": "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_Q3_2020.zip",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_quarter(quarter: str, cache_dir: Path) -> Path:
    if quarter not in BACKBLAZE_URLS:
        raise ValueError(f"Unsupported quarter {quarter}. Available: {', '.join(BACKBLAZE_URLS)}")

    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / f"{quarter}.zip"
    extract_dir = cache_dir / quarter

    if extract_dir.exists() and any(extract_dir.glob("*.csv")):
        print(f"Using cached extracted dataset: {extract_dir}")
        return extract_dir

    if not zip_path.exists():
        print(f"Downloading {quarter} from Backblaze...")
        response = requests.get(BACKBLAZE_URLS[quarter], timeout=120, stream=True)
        response.raise_for_status()
        with zip_path.open("wb") as file_obj:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file_obj.write(chunk)
        print(f"Downloaded to {zip_path} (sha256={sha256(zip_path)})")
    else:
        print(f"Using cached zip: {zip_path} (sha256={sha256(zip_path)})")

    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    print(f"Extracted {quarter} dataset to {extract_dir}")
    return extract_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and cache Backblaze quarter dataset")
    parser.add_argument("--quarter", default="2020_Q2", help="Backblaze quarter identifier")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_ROOT)
    args = parser.parse_args()

    download_quarter(args.quarter, args.cache_dir)


if __name__ == "__main__":
    main()
