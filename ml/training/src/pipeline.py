from __future__ import annotations

import argparse
from pathlib import Path

from src.config import HORIZON_DAYS_DEFAULT, PROCESSED_ROOT
from src.download_backblaze import download_quarter
from src.prepare_dataset import prepare_dataset
from src.train import train


def run_pipeline(quarter: str, cache_dir: Path, max_drives: int, horizon_days: int) -> Path:
    raw_dir = download_quarter(quarter=quarter, cache_dir=cache_dir)
    prepared_path = PROCESSED_ROOT / f"training_dataset_{quarter}.csv"
    prepare_dataset(
        input_dir=raw_dir,
        output_path=prepared_path,
        horizon_days=horizon_days,
        max_drives=max_drives,
    )
    return train(prepared_path=prepared_path, model_version=None, horizon_days=horizon_days)


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end training pipeline")
    parser.add_argument("--quarter", default="2020_Q2")
    parser.add_argument("--cache-dir", type=Path, default=Path("ml/training/data/cache"))
    parser.add_argument("--max-drives", type=int, default=500)
    parser.add_argument("--horizon-days", type=int, default=HORIZON_DAYS_DEFAULT)
    args = parser.parse_args()

    artifact_dir = run_pipeline(
        quarter=args.quarter,
        cache_dir=args.cache_dir,
        max_drives=args.max_drives,
        horizon_days=args.horizon_days,
    )
    print(f"Pipeline complete, artifact: {artifact_dir}")


if __name__ == "__main__":
    main()
