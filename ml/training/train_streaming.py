#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.preprocessing import StandardScaler

NUMERIC_TYPES = {
    "BIGINT",
    "INTEGER",
    "SMALLINT",
    "TINYINT",
    "UBIGINT",
    "UINTEGER",
    "USMALLINT",
    "UTINYINT",
    "HUGEINT",
    "UHUGEINT",
    "DECIMAL",
    "DOUBLE",
    "FLOAT",
    "REAL",
}

IGNORED_COLUMNS = {
    "as_of_date",
    "serial_number",
    "model",
    "label_30d",
    "year",
    "month",
}


@dataclass
class DatasetSplit:
    min_date: datetime
    max_date: datetime
    cutoff_date: datetime
    train_end_date: datetime


def _sha256(path: Path) -> str:
    if not path.exists():
        return "manifest_missing"

    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_datetime(value) -> datetime:
    timestamp = pd.Timestamp(value)
    return timestamp.to_pydatetime().replace(tzinfo=timezone.utc)


def discover_numeric_features(conn: duckdb.DuckDBPyConnection, feature_glob: str) -> list[str]:
    rows = conn.execute(
        "DESCRIBE SELECT * FROM read_parquet(?, union_by_name=true)",
        [feature_glob],
    ).fetchall()

    features: list[str] = []
    for row in rows:
        column_name, column_type = str(row[0]), str(row[1]).upper()
        if column_name in IGNORED_COLUMNS:
            continue
        if column_type in NUMERIC_TYPES:
            features.append(column_name)

    if not features:
        raise RuntimeError("No numeric features discovered in features parquet dataset")

    return features


def resolve_split(
    conn: duckdb.DuckDBPyConnection,
    feature_glob: str,
    test_months: int,
    horizon_days: int = 30,
) -> DatasetSplit:
    min_date, max_date = conn.execute(
        "SELECT MIN(as_of_date), MAX(as_of_date) FROM read_parquet(?, union_by_name=true)",
        [feature_glob],
    ).fetchone()

    if min_date is None or max_date is None:
        raise RuntimeError("Features dataset is empty")

    min_ts = pd.Timestamp(min_date)
    max_ts = pd.Timestamp(max_date)
    candidate_cutoff = max_ts - pd.DateOffset(months=test_months)

    if candidate_cutoff <= min_ts:
        span_days = max(1, int((max_ts - min_ts).days))
        candidate_cutoff = min_ts + pd.Timedelta(days=int(span_days * 0.8))

    return DatasetSplit(
        min_date=_as_datetime(min_ts),
        max_date=_as_datetime(max_ts),
        cutoff_date=_as_datetime(candidate_cutoff),
        train_end_date=_as_datetime(candidate_cutoff - pd.Timedelta(days=horizon_days)),
    )


def iter_batches(
    conn: duckdb.DuckDBPyConnection,
    feature_glob: str,
    numeric_features: list[str],
    split: DatasetSplit,
    mode: str,
    batch_size: int,
    max_batches: int | None = None,
) -> Iterable[pd.DataFrame]:
    comparator = "<=" if mode == "train" else ">"

    query = f"""
      SELECT
        as_of_date,
        label_30d,
        {', '.join(numeric_features)}
      FROM read_parquet(?, union_by_name=true)
      WHERE as_of_date {comparator} ?
        AND label_30d IS NOT NULL
      ORDER BY as_of_date
    """

    reader = conn.execute(
        query,
        [feature_glob, (split.train_end_date if mode == "train" else split.cutoff_date).date()],
    ).fetch_record_batch(rows_per_batch=batch_size)

    yielded = 0
    for batch in reader:
        frame = batch.to_pandas()
        if frame.empty:
            continue

        yield frame
        yielded += 1
        if max_batches is not None and yielded >= max_batches:
            break


def _recall_at_top_fraction(y_true: np.ndarray, scores: np.ndarray, fraction: float) -> float:
    if len(y_true) == 0:
        return 0.0

    positives = y_true.sum()
    if positives == 0:
        return 0.0

    k = max(1, int(len(scores) * fraction))
    top_indices = np.argsort(scores)[::-1][:k]
    return float(y_true[top_indices].sum() / positives)


def _calibration_bins(y_true: np.ndarray, scores: np.ndarray, bins: int = 10) -> list[dict[str, float]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    result: list[dict[str, float]] = []

    for idx in range(bins):
        left, right = edges[idx], edges[idx + 1]
        if idx == bins - 1:
            mask = (scores >= left) & (scores <= right)
        else:
            mask = (scores >= left) & (scores < right)

        if not np.any(mask):
            continue

        result.append(
            {
                "bin_left": float(left),
                "bin_right": float(right),
                "predicted_mean": float(scores[mask].mean()),
                "observed_rate": float(y_true[mask].mean()),
                "count": int(mask.sum()),
            }
        )

    return result


def train_streaming(
    features_dir: Path,
    artifacts_root: Path,
    horizon_days: int,
    batch_size: int,
    test_months: int,
    manifest_path: Path,
    max_train_batches: int | None,
    max_test_batches: int | None,
) -> Path:
    if horizon_days != 30:
        raise ValueError("The label_30d feature contract requires horizon_days=30")
    if batch_size < 1 or test_months < 1 or any(value is not None and value < 1 for value in (max_train_batches, max_test_batches)):
        raise ValueError("Batch limits and test months must be positive")
    feature_glob = str(features_dir / "**" / "*.parquet")
    conn = duckdb.connect(database=":memory:")

    numeric_features = discover_numeric_features(conn, feature_glob)
    split = resolve_split(conn, feature_glob, test_months=test_months, horizon_days=horizon_days)

    scaler = StandardScaler(with_mean=True, with_std=True)
    class_counts = {0: 0, 1: 0}
    for batch in iter_batches(
        conn,
        feature_glob,
        numeric_features,
        split,
        mode="train",
        batch_size=batch_size,
        max_batches=max_train_batches,
    ):
        x = batch[numeric_features].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=np.float64)
        y = batch["label_30d"].astype(int).to_numpy()
        scaler.partial_fit(x)
        class_counts[0] += int((y == 0).sum())
        class_counts[1] += int((y == 1).sum())

    classifier = SGDClassifier(
        loss="log_loss",
        penalty="l2",
        alpha=1e-5,
        random_state=42,
    )
    total_train = class_counts[0] + class_counts[1]
    if total_train == 0:
        raise RuntimeError("No training rows available after split")

    class_weights = {
        0: (total_train / (2 * class_counts[0])) if class_counts[0] > 0 else 1.0,
        1: (total_train / (2 * class_counts[1])) if class_counts[1] > 0 else 1.0,
    }

    is_first_batch = True
    for batch in iter_batches(
        conn,
        feature_glob,
        numeric_features,
        split,
        mode="train",
        batch_size=batch_size,
        max_batches=max_train_batches,
    ):
        x = batch[numeric_features].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=np.float64)
        y = batch["label_30d"].astype(int).to_numpy()
        sample_weight = np.where(y == 1, class_weights[1], class_weights[0]).astype(np.float64)

        x_scaled = scaler.transform(x)
        if is_first_batch:
            classifier.partial_fit(
                x_scaled,
                y,
                classes=np.array([0, 1]),
                sample_weight=sample_weight,
            )
            is_first_batch = False
        else:
            classifier.partial_fit(x_scaled, y, sample_weight=sample_weight)

    if is_first_batch:
        raise RuntimeError("No training batches yielded rows. Check features dataset and split.")

    y_true_chunks: list[np.ndarray] = []
    score_chunks: list[np.ndarray] = []

    for batch in iter_batches(
        conn,
        feature_glob,
        numeric_features,
        split,
        mode="test",
        batch_size=batch_size,
        max_batches=max_test_batches,
    ):
        x = batch[numeric_features].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=np.float64)
        y = batch["label_30d"].astype(int).to_numpy()
        x_scaled = scaler.transform(x)
        scores = classifier.predict_proba(x_scaled)[:, 1]

        y_true_chunks.append(y)
        score_chunks.append(scores)

    if not y_true_chunks:
        raise RuntimeError("No chronological holdout rows; training rows must never substitute for evaluation")

    y_true = np.concatenate(y_true_chunks)
    y_scores = np.concatenate(score_chunks)

    baseline_scores = np.full(len(y_true), class_counts[1] / total_train)
    metrics = {
        "evaluation_scope": "chronological_holdout",
        "baseline_brier_score": float(brier_score_loss(y_true, baseline_scores)),
        "baseline_pr_auc": float(y_true.mean()),
        "train_rows": total_train,
        "pr_auc": float(average_precision_score(y_true, y_scores)),
        "brier_score": float(brier_score_loss(y_true, y_scores)),
        "recall_at_top_1pct": _recall_at_top_fraction(y_true, y_scores, 0.01),
        "recall_at_top_5pct": _recall_at_top_fraction(y_true, y_scores, 0.05),
        "test_rows": int(len(y_true)),
        "positive_rate_test": float(y_true.mean()),
        "calibration": _calibration_bins(y_true, y_scores, bins=10),
    }

    model_version = f"telemetry_h30_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    artifact_dir = artifacts_root / model_version
    artifact_dir.mkdir(parents=True, exist_ok=False)

    # Identical to the missing-value preprocessing used in both training passes.
    fill_values = {feature: 0.0 for feature in numeric_features}
    feature_weights = {
        feature: float(value)
        for feature, value in zip(numeric_features, classifier.coef_[0], strict=True)
    }

    bundle = {
        "model": classifier,
        "scaler": scaler,
        "model_type": "SGDClassifier(log_loss)",
        "feature_columns": numeric_features,
        "fill_values": fill_values,
        "feature_weights": feature_weights,
        "horizon_days": horizon_days,
    }
    joblib.dump(bundle, artifact_dir / "model.joblib")

    feature_schema = {
        "ordered_features": [{"name": feature, "dtype": "float"} for feature in numeric_features],
        "label_column": "label_30d",
        "horizon_days": horizon_days,
    }
    (artifact_dir / "feature_schema.json").write_text(
        json.dumps(feature_schema, indent=2),
        encoding="utf-8",
    )

    (artifact_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    version_meta = {
        "model_version": model_version,
        "horizon_days": horizon_days,
        "train_date": datetime.now(timezone.utc).isoformat(),
        "train_range": {
            "start": split.min_date.date().isoformat(),
            "end": split.train_end_date.date().isoformat(),
        },
        "test_range": {
            "start": (split.cutoff_date + pd.Timedelta(days=1)).date().isoformat(),
            "end": split.max_date.date().isoformat(),
        },
        "dataset_manifest_hash": _sha256(manifest_path),
        "data_source": json.loads(manifest_path.read_text()).get("source", "user-provided feature parquet") if manifest_path.exists() else "user-provided feature parquet; manifest unavailable",
        "imputation": "constant_zero_before_scaling",
        "purge_days": horizon_days,
        "evaluation_scope": "chronological_holdout",
        "max_train_batches": max_train_batches,
        "max_test_batches": max_test_batches,
        "probability_calibration": "not calibrated; class-balanced logistic score",

    }
    (artifact_dir / "version.json").write_text(json.dumps(version_meta, indent=2), encoding="utf-8")

    model_card = f"""# Model Card - {model_version}

## Summary
Incremental logistic model trained on supplied telemetry feature parquet with a **{horizon_days}-day** failure horizon.

## Training Data
- Source: {version_meta["data_source"]}
- Manifest SHA-256: {version_meta["dataset_manifest_hash"]}
- Training/evaluation batch limits: {max_train_batches} / {max_test_batches}
- Eligible train range: {version_meta['train_range']['start']} to {version_meta['train_range']['end']}
- Eligible test range: {version_meta['test_range']['start']} to {version_meta['test_range']['end']}

## Evaluation
- PR-AUC: {metrics['pr_auc']:.4f}
- Recall@top 1%: {metrics['recall_at_top_1pct']:.4f}
- Recall@top 5%: {metrics['recall_at_top_5pct']:.4f}
- Brier score: {metrics['brier_score']:.4f}

## Notes
- Chronological split with {horizon_days}-day purge; no training-data evaluation fallback.
- Scores use class-balanced training and are not calibrated fleet failure probabilities.
- A shared drive can appear in both periods; this is temporal generalization, not unseen-device evaluation.
- Incremental fitting enables full-dataset training without loading all rows into memory.
- Feature validation enforced in model service through exported schema.
"""
    (artifact_dir / "model_card.md").write_text(model_card, encoding="utf-8")

    (artifacts_root / "ACTIVE_MODEL").write_text(model_version, encoding="utf-8")

    conn.close()
    print(f"Training complete. Artifact: {artifact_dir}")
    return artifact_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Train H=30 model on Backblaze features with streaming")
    parser.add_argument("--features", type=Path, default=Path("data/backblaze/features_h30"))
    parser.add_argument("--artifacts-root", type=Path, default=Path("services/model/artifacts"))
    parser.add_argument("--manifest", type=Path, default=Path("data/backblaze/manifest.json"))
    parser.add_argument("--horizon-days", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=250_000)
    parser.add_argument("--test-months", type=int, default=9)
    parser.add_argument("--max-train-batches", type=int, default=None)
    parser.add_argument("--max-test-batches", type=int, default=None)
    args = parser.parse_args()

    train_streaming(
        features_dir=args.features,
        artifacts_root=args.artifacts_root,
        horizon_days=args.horizon_days,
        batch_size=args.batch_size,
        test_months=args.test_months,
        manifest_path=args.manifest,
        max_train_batches=args.max_train_batches,
        max_test_batches=args.max_test_batches,
    )


if __name__ == "__main__":
    main()
