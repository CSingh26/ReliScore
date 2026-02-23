from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import FEATURE_COLUMNS


def _future_failure_label(values: np.ndarray, horizon_days: int) -> np.ndarray:
    labels = np.zeros_like(values, dtype=int)
    for idx in range(len(values)):
        future = values[idx + 1 : idx + horizon_days + 1]
        labels[idx] = int(future.max()) if len(future) else 0
    return labels


def _slope(series: pd.Series, window: int) -> pd.Series:
    return (series - series.shift(window)) / max(window, 1)


def engineer_features(df: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    required_columns = {"drive_id", "day", "is_failed_today"}
    missing_required = required_columns.difference(df.columns)
    if missing_required:
        raise ValueError(f"Missing required columns: {sorted(missing_required)}")

    work_df = df.copy()
    work_df["day"] = pd.to_datetime(work_df["day"])  # type: ignore[assignment]
    work_df = work_df.sort_values(["drive_id", "day"]).reset_index(drop=True)

    for column in [
        "smart_5",
        "smart_197",
        "smart_198",
        "smart_199",
        "temperature",
        "io_read_latency_ms",
        "io_write_latency_ms",
    ]:
        if column not in work_df:
            work_df[column] = np.nan

    grouped = work_df.groupby("drive_id", group_keys=False)
    first_seen = grouped["day"].transform("min")
    work_df["age_days"] = (work_df["day"] - first_seen).dt.days.clip(lower=0)

    work_df["smart_5_mean_7d"] = grouped["smart_5"].transform(
        lambda series: series.rolling(window=7, min_periods=1).mean()
    )
    work_df["smart_5_slope_14d"] = grouped["smart_5"].transform(lambda series: _slope(series, 14))
    work_df["smart_197_max_30d"] = grouped["smart_197"].transform(
        lambda series: series.rolling(window=30, min_periods=1).max()
    )
    work_df["smart_197_mean_7d"] = grouped["smart_197"].transform(
        lambda series: series.rolling(window=7, min_periods=1).mean()
    )
    work_df["smart_198_delta_7d"] = grouped["smart_198"].transform(lambda series: series - series.shift(7))
    work_df["smart_199_volatility_30d"] = grouped["smart_199"].transform(
        lambda series: series.rolling(window=30, min_periods=2).std()
    )
    work_df["temperature_mean_7d"] = grouped["temperature"].transform(
        lambda series: series.rolling(window=7, min_periods=1).mean()
    )
    work_df["read_latency_mean_7d"] = grouped["io_read_latency_ms"].transform(
        lambda series: series.rolling(window=7, min_periods=1).mean()
    )
    work_df["write_latency_mean_7d"] = grouped["io_write_latency_ms"].transform(
        lambda series: series.rolling(window=7, min_periods=1).mean()
    )
    work_df["missing_smart_197_30d"] = grouped["smart_197"].transform(
        lambda series: series.rolling(window=30, min_periods=1).apply(lambda v: int(np.isnan(v).all()))
    )

    work_df["label_fail_within_14d"] = grouped["is_failed_today"].transform(
        lambda series: _future_failure_label(series.fillna(0).astype(int).to_numpy(), horizon_days)
    )

    for feature_name in FEATURE_COLUMNS:
        if feature_name not in work_df:
            work_df[feature_name] = np.nan

    return work_df
