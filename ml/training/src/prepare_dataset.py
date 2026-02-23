from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import HORIZON_DAYS_DEFAULT, PROCESSED_ROOT
from src.features import engineer_features

RAW_COLUMNS = {
    "date": "day",
    "serial_number": "drive_id",
    "model": "model",
    "capacity_bytes": "capacity_bytes",
    "failure": "is_failed_today",
    "smart_5_raw": "smart_5",
    "smart_187_raw": "smart_187",
    "smart_188_raw": "smart_188",
    "smart_197_raw": "smart_197",
    "smart_198_raw": "smart_198",
    "smart_199_raw": "smart_199",
    "smart_194_raw": "temperature",
}


def _attach_synthetic_io(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    io_read = np.maximum(1.0, rng.normal(3.5, 0.8, size=len(df)))
    io_write = np.maximum(1.0, rng.normal(4.2, 0.9, size=len(df)))

    failure_mask = df["is_failed_today"].fillna(0).astype(int) == 1
    io_read = np.where(failure_mask, io_read * 1.8, io_read)
    io_write = np.where(failure_mask, io_write * 1.9, io_write)

    out = df.copy()
    out["io_read_latency_ms"] = io_read
    out["io_write_latency_ms"] = io_write
    return out


def _time_split(df: pd.DataFrame) -> pd.DataFrame:
    unique_days = sorted(df["day"].dropna().unique())
    if len(unique_days) < 10:
        df["split"] = "train"
        return df

    train_cutoff = unique_days[int(len(unique_days) * 0.7)]
    val_cutoff = unique_days[int(len(unique_days) * 0.85)]

    def assign(day: pd.Timestamp) -> str:
        if day <= train_cutoff:
            return "train"
        if day <= val_cutoff:
            return "val"
        return "test"

    out = df.copy()
    out["split"] = out["day"].apply(assign)
    return out


def prepare_dataset(input_dir: Path, output_path: Path, horizon_days: int, max_drives: int) -> Path:
    csv_paths = sorted(input_dir.rglob("*.csv"))
    if not csv_paths:
        raise FileNotFoundError(
            f"No CSV files found in {input_dir}. Run download script first or point to dataset path."
        )

    data_frames: list[pd.DataFrame] = []
    for csv_path in csv_paths:
        df = pd.read_csv(csv_path, low_memory=False)
        intersect_columns = [column for column in RAW_COLUMNS if column in df.columns]
        if {"date", "serial_number", "failure"}.difference(intersect_columns):
            continue
        selected = df[intersect_columns].rename(columns=RAW_COLUMNS)
        data_frames.append(selected)

    if not data_frames:
        raise RuntimeError("No usable Backblaze CSVs found after column filtering.")

    telemetry = pd.concat(data_frames, ignore_index=True)
    telemetry["day"] = pd.to_datetime(telemetry["day"], errors="coerce")
    telemetry = telemetry.dropna(subset=["drive_id", "day"]).copy()
    telemetry["is_failed_today"] = telemetry["is_failed_today"].fillna(0).astype(int)

    if max_drives > 0:
        top_drive_ids = telemetry["drive_id"].value_counts().head(max_drives).index
        telemetry = telemetry[telemetry["drive_id"].isin(top_drive_ids)].copy()

    telemetry = _attach_synthetic_io(telemetry)
    features = engineer_features(telemetry, horizon_days=horizon_days)
    split_df = _time_split(features)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    split_df.to_csv(output_path, index=False)

    print(
        f"Prepared dataset at {output_path} with {len(split_df)} rows. "
        f"Split counts: {split_df['split'].value_counts().to_dict()}"
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare model-ready dataset with engineered features")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROCESSED_ROOT / "training_dataset.csv",
    )
    parser.add_argument("--horizon-days", type=int, default=HORIZON_DAYS_DEFAULT)
    parser.add_argument("--max-drives", type=int, default=500)
    args = parser.parse_args()

    prepare_dataset(
        input_dir=args.input_dir,
        output_path=args.output,
        horizon_days=args.horizon_days,
        max_drives=args.max_drives,
    )


if __name__ == "__main__":
    main()
