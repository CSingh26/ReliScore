from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src.config import ARTIFACTS_ROOT, FEATURE_COLUMNS, HORIZON_DAYS_DEFAULT


@dataclass
class TrainingMetrics:
    pr_auc: float
    roc_auc: float
    brier_score: float
    recall_at_top_0_5pct: float
    recall_at_top_1pct: float
    recall_at_top_2pct: float


def _recall_at_top_k(y_true: np.ndarray, scores: np.ndarray, fraction: float) -> float:
    if len(y_true) == 0:
        return 0.0

    k = max(1, int(len(scores) * fraction))
    top_idx = np.argsort(scores)[::-1][:k]
    positives = y_true.sum()
    if positives == 0:
        return 0.0

    return float(y_true[top_idx].sum() / positives)


def _safe_predict_proba(model, features: pd.DataFrame) -> np.ndarray:
    proba = model.predict_proba(features)
    if proba.ndim == 1:
        return proba
    return proba[:, 1]


def _build_model_card(
    model_version: str,
    horizon_days: int,
    metrics: TrainingMetrics,
    selected_model: str,
    train_window: dict[str, str],
) -> str:
    return f"""# Model Card - {model_version}

## Intended Use
Predict probability that a drive fails within **{horizon_days} days** using daily telemetry-derived features.

## Model
- Selected model: `{selected_model}`
- Candidate models: LogisticRegression, GradientBoostingClassifier
- Feature count: {len(FEATURE_COLUMNS)}

## Data Window
- Train start: {train_window['train_start']}
- Train end: {train_window['train_end']}
- Test start: {train_window['test_start']}
- Test end: {train_window['test_end']}

## Metrics (test split)
- PR-AUC: {metrics.pr_auc:.4f}
- ROC-AUC: {metrics.roc_auc:.4f}
- Brier score: {metrics.brier_score:.4f}
- Recall@top 0.5%: {metrics.recall_at_top_0_5pct:.4f}
- Recall@top 1%: {metrics.recall_at_top_1pct:.4f}
- Recall@top 2%: {metrics.recall_at_top_2pct:.4f}

## Limitations
- Backblaze metadata and synthetic latency fields may not represent all production fleets.
- Model is refreshed with batch telemetry; no streaming behavior in MVP.
- Explanations are feature-attribution approximations for operator triage.
"""


def train(prepared_path: Path, model_version: str | None, horizon_days: int) -> Path:
    if not prepared_path.exists():
        raise FileNotFoundError(
            f"Prepared dataset not found: {prepared_path}. Run prepare_dataset.py first."
        )

    df = pd.read_csv(prepared_path, parse_dates=["day"])  # type: ignore[arg-type]
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    train_df = df[df["split"] == "train"].copy()
    val_df = df[df["split"] == "val"].copy()
    test_df = df[df["split"] == "test"].copy()

    if len(train_df) < 100:
        raise RuntimeError("Not enough train rows. Increase input size or max-drives.")

    if len(val_df) == 0:
        val_df = train_df.sample(frac=0.2, random_state=42)

    if len(test_df) == 0:
        test_df = val_df.copy()

    fill_values = train_df[FEATURE_COLUMNS].median(numeric_only=True)

    x_train = train_df[FEATURE_COLUMNS].fillna(fill_values)
    y_train = train_df["label_fail_within_14d"].astype(int)

    x_val = val_df[FEATURE_COLUMNS].fillna(fill_values)
    y_val = val_df["label_fail_within_14d"].astype(int)

    x_test = test_df[FEATURE_COLUMNS].fillna(fill_values)
    y_test = test_df["label_fail_within_14d"].astype(int).to_numpy()

    logistic = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    logistic.fit(x_train, y_train)
    logistic_pr_auc = average_precision_score(y_val, _safe_predict_proba(logistic, x_val))

    gbdt = GradientBoostingClassifier(random_state=42)
    gbdt.fit(x_train, y_train)
    gbdt_pr_auc = average_precision_score(y_val, _safe_predict_proba(gbdt, x_val))

    if gbdt_pr_auc > logistic_pr_auc:
        selected_model = gbdt
        selected_model_name = "GradientBoostingClassifier"
    else:
        selected_model = logistic
        selected_model_name = "LogisticRegression"

    test_scores = _safe_predict_proba(selected_model, x_test)

    metrics = TrainingMetrics(
        pr_auc=float(average_precision_score(y_test, test_scores)),
        roc_auc=float(roc_auc_score(y_test, test_scores)) if len(np.unique(y_test)) > 1 else 0.5,
        brier_score=float(brier_score_loss(y_test, test_scores)),
        recall_at_top_0_5pct=_recall_at_top_k(y_test, test_scores, 0.005),
        recall_at_top_1pct=_recall_at_top_k(y_test, test_scores, 0.01),
        recall_at_top_2pct=_recall_at_top_k(y_test, test_scores, 0.02),
    )

    # Reliability curve points for calibration diagnostics.
    prob_true, prob_pred = calibration_curve(y_test, test_scores, n_bins=10, strategy="quantile")

    version = model_version or f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    artifact_dir = ARTIFACTS_ROOT / version
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if hasattr(selected_model, "coef_"):
        feature_weights = {
            feature: float(weight)
            for feature, weight in zip(FEATURE_COLUMNS, selected_model.coef_[0], strict=False)
        }
    else:
        feature_weights = {
            feature: float(weight)
            for feature, weight in zip(FEATURE_COLUMNS, selected_model.feature_importances_, strict=False)
        }

    bundle = {
        "model": selected_model,
        "model_type": selected_model_name,
        "feature_columns": FEATURE_COLUMNS,
        "fill_values": {key: float(value) for key, value in fill_values.to_dict().items()},
        "feature_weights": feature_weights,
        "horizon_days": horizon_days,
    }
    joblib.dump(bundle, artifact_dir / "model.joblib")

    with (artifact_dir / "metrics.json").open("w", encoding="utf-8") as file_obj:
        json.dump(
            {
                **asdict(metrics),
                "calibration_curve": [
                    {"predicted": float(pred), "observed": float(obs)}
                    for pred, obs in zip(prob_pred, prob_true, strict=False)
                ],
            },
            file_obj,
            indent=2,
        )

    train_window = {
        "train_start": str(train_df["day"].min().date()),
        "train_end": str(train_df["day"].max().date()),
        "test_start": str(test_df["day"].min().date()),
        "test_end": str(test_df["day"].max().date()),
    }

    with (artifact_dir / "version.json").open("w", encoding="utf-8") as file_obj:
        json.dump(
            {
                "model_version": version,
                "train_date": datetime.now(timezone.utc).isoformat(),
                "horizon_days": horizon_days,
                "selected_model": selected_model_name,
                "trained_data_window": train_window,
            },
            file_obj,
            indent=2,
        )

    with (artifact_dir / "feature_schema.json").open("w", encoding="utf-8") as file_obj:
        json.dump({"features": FEATURE_COLUMNS}, file_obj, indent=2)

    model_card = _build_model_card(
        model_version=version,
        horizon_days=horizon_days,
        metrics=metrics,
        selected_model=selected_model_name,
        train_window=train_window,
    )
    (artifact_dir / "model_card.md").write_text(model_card, encoding="utf-8")

    active_pointer = ARTIFACTS_ROOT / "ACTIVE_MODEL"
    active_pointer.write_text(version, encoding="utf-8")

    print(f"Model artifacts written to: {artifact_dir}")
    return artifact_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Train predictive failure model and emit versioned artifacts")
    parser.add_argument(
        "--prepared",
        type=Path,
        default=Path("ml/training/data/processed/training_dataset.csv"),
    )
    parser.add_argument("--model-version", type=str, default=None)
    parser.add_argument("--horizon-days", type=int, default=HORIZON_DAYS_DEFAULT)
    args = parser.parse_args()

    train(prepared_path=args.prepared, model_version=args.model_version, horizon_days=args.horizon_days)


if __name__ == "__main__":
    main()
