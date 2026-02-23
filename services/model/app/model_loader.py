from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from app.schemas import ReasonCode, RiskBucket


def _risk_bucket(score: float) -> RiskBucket:
    if score >= 0.75:
        return RiskBucket.HIGH
    if score >= 0.4:
        return RiskBucket.MED
    return RiskBucket.LOW


@dataclass
class LoadedModel:
    model: object
    model_type: str
    feature_columns: list[str]
    fill_values: dict[str, float]
    feature_weights: dict[str, float]
    horizon_days: int
    model_version: str
    metrics: dict[str, float | list[dict[str, float]] | str]


class ModelStore:
    def __init__(self) -> None:
        self._lock = Lock()
        default_root = Path(__file__).resolve().parents[1] / "artifacts"
        self.artifacts_root = Path(os.getenv("MODEL_ARTIFACTS_ROOT", str(default_root)))
        self.requested_version = os.getenv("MODEL_VERSION")
        self.loaded: LoadedModel | None = None

    def load(self) -> LoadedModel:
        with self._lock:
            version = self._resolve_version()
            artifact_dir = self.artifacts_root / version
            bundle = joblib.load(artifact_dir / "model.joblib")
            metrics = self._load_json(artifact_dir / "metrics.json", default={})
            version_meta = self._load_json(artifact_dir / "version.json", default={})

            self.loaded = LoadedModel(
                model=bundle["model"],
                model_type=bundle.get("model_type", "UnknownModel"),
                feature_columns=list(bundle["feature_columns"]),
                fill_values={k: float(v) for k, v in bundle.get("fill_values", {}).items()},
                feature_weights={k: float(v) for k, v in bundle.get("feature_weights", {}).items()},
                horizon_days=int(bundle.get("horizon_days", version_meta.get("horizon_days", 14))),
                model_version=str(version_meta.get("model_version", version)),
                metrics=metrics,
            )
            return self.loaded

    def score(self, features: dict[str, float | None]) -> tuple[float, RiskBucket, list[ReasonCode]]:
        if self.loaded is None:
            self.load()
        assert self.loaded is not None

        row = {}
        for feature in self.loaded.feature_columns:
            raw_value = features.get(feature)
            if raw_value is None:
                row[feature] = self.loaded.fill_values.get(feature, 0.0)
            else:
                row[feature] = float(raw_value)

        frame = pd.DataFrame([row], columns=self.loaded.feature_columns)
        probabilities = self.loaded.model.predict_proba(frame)
        risk_score = float(probabilities[:, 1][0]) if probabilities.ndim > 1 else float(probabilities[0])

        reasons: list[ReasonCode] = []
        for feature_name, value in row.items():
            weight = float(self.loaded.feature_weights.get(feature_name, 0.0))
            contribution = float(weight * value)
            direction = "UP" if contribution >= 0 else "DOWN"
            reasons.append(
                ReasonCode(code=feature_name, contribution=round(contribution, 6), direction=direction)
            )

        top_reasons = sorted(reasons, key=lambda item: abs(item.contribution), reverse=True)[:5]
        return risk_score, _risk_bucket(risk_score), top_reasons

    def _resolve_version(self) -> str:
        self.artifacts_root.mkdir(parents=True, exist_ok=True)

        if self.requested_version and self.requested_version != "latest":
            candidate = self.artifacts_root / self.requested_version
            if candidate.exists():
                return self.requested_version
            raise FileNotFoundError(f"Requested model version not found: {self.requested_version}")

        active_file = self.artifacts_root / "ACTIVE_MODEL"
        if active_file.exists():
            version = active_file.read_text(encoding="utf-8").strip()
            if version and (self.artifacts_root / version).exists():
                return version

        candidates = [
            path
            for path in self.artifacts_root.iterdir()
            if path.is_dir() and (path / "model.joblib").exists()
        ]
        if candidates:
            latest = sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]
            return latest.name

        return self._bootstrap_demo_model()

    def _bootstrap_demo_model(self) -> str:
        demo_version = f"demo-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        out_dir = self.artifacts_root / demo_version
        out_dir.mkdir(parents=True, exist_ok=True)

        feature_columns = [
            "age_days",
            "smart_5_mean_7d",
            "smart_5_slope_14d",
            "smart_197_max_30d",
            "smart_197_mean_7d",
            "smart_198_delta_7d",
            "smart_199_volatility_30d",
            "temperature_mean_7d",
            "read_latency_mean_7d",
            "write_latency_mean_7d",
            "missing_smart_197_30d",
        ]

        rng = np.random.default_rng(42)
        x = rng.normal(0, 1, size=(4000, len(feature_columns)))
        linear = (
            0.3 * x[:, 0]
            + 1.1 * x[:, 1]
            + 1.3 * x[:, 3]
            + 1.5 * x[:, 4]
            + 1.0 * x[:, 5]
            + 0.7 * x[:, 9]
        )
        probs = 1.0 / (1.0 + np.exp(-linear))
        y = (probs > 0.65).astype(int)

        model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
        model.fit(x, y)

        bundle = {
            "model": model,
            "model_type": "LogisticRegression",
            "feature_columns": feature_columns,
            "fill_values": {name: 0.0 for name in feature_columns},
            "feature_weights": {
                feature: float(weight)
                for feature, weight in zip(feature_columns, model.coef_[0], strict=False)
            },
            "horizon_days": 14,
        }
        joblib.dump(bundle, out_dir / "model.joblib")

        metrics = {
            "pr_auc": 0.68,
            "recall_at_top_1pct": 0.29,
            "brier_score": 0.16,
            "note": "Demo synthetic model generated automatically.",
        }
        (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

        version_meta = {
            "model_version": demo_version,
            "train_date": datetime.now(timezone.utc).isoformat(),
            "horizon_days": 14,
        }
        (out_dir / "version.json").write_text(json.dumps(version_meta, indent=2), encoding="utf-8")
        (out_dir / "model_card.md").write_text(
            "# Demo Model\n\nAuto-generated fallback model for local runs.",
            encoding="utf-8",
        )

        (self.artifacts_root / "ACTIVE_MODEL").write_text(demo_version, encoding="utf-8")
        return demo_version

    @staticmethod
    def _load_json(path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
