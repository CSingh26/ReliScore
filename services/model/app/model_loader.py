from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

import joblib
import numpy as np
import pandas as pd

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
    scaler: object | None
    model_type: str
    feature_columns: list[str]
    fill_values: dict[str, float]
    feature_weights: dict[str, float]
    horizon_days: int
    model_version: str
    metrics: dict[str, float | list[dict[str, float]] | str]
    provenance: dict = field(default_factory=dict)

    @property
    def explanation_method(self) -> str:
        from sklearn.linear_model import LogisticRegression, SGDClassifier
        supported = isinstance(self.model, LogisticRegression) or (isinstance(self.model, SGDClassifier) and self.model.loss == "log_loss")
        return "linear_log_odds" if supported and getattr(self.model, "coef_", np.empty((0,))).shape == (1, len(self.feature_columns)) else "unavailable"


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
            feature_schema = self._load_json(artifact_dir / "feature_schema.json", default={})

            feature_columns = self._resolve_feature_columns(bundle=bundle, feature_schema=feature_schema)
            horizon_days = int(version_meta.get("horizon_days", bundle.get("horizon_days", 30)))
            model_version = str(version_meta.get("model_version", version))

            fills = bundle.get("fill_values", {})
            if set(fills) != set(feature_columns) or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in fills.values()):
                raise ValueError("Artifact fill_values must contain one finite training-time fill per feature")
            if horizon_days <= 0 or model_version != version:
                raise ValueError("Artifact version/horizon metadata is inconsistent")
            self.loaded = LoadedModel(
                model=bundle["model"],
                scaler=bundle.get("scaler"),
                model_type=str(bundle.get("model_type", "UnknownModel")),
                feature_columns=feature_columns,
                fill_values={
                    key: float(value)
                    for key, value in bundle.get("fill_values", {}).items()
                },
                feature_weights={
                    key: float(value)
                    for key, value in bundle.get("feature_weights", {}).items()
                },
                horizon_days=horizon_days,
                model_version=model_version,
                metrics=metrics,
                provenance={**version_meta, "artifact_sha256": hashlib.sha256((artifact_dir / "model.joblib").read_bytes()).hexdigest()},
            )
            return self.loaded

    def score(
        self,
        features: dict[str, float | None],
    ) -> tuple[float, RiskBucket, list[ReasonCode]]:
        if self.loaded is None:
            self.load()
        assert self.loaded is not None

        expected_keys = set(self.loaded.feature_columns)
        provided_keys = set(features.keys())

        missing = sorted(expected_keys - provided_keys)
        extra = sorted(provided_keys - expected_keys)
        if missing or extra:
            raise ValueError(
                "Feature schema mismatch. "
                f"Missing keys: {missing if missing else 'none'}. "
                f"Unexpected keys: {extra if extra else 'none'}."
            )

        row = {}
        for feature in self.loaded.feature_columns:
            raw_value = features.get(feature)
            if raw_value is None:
                if feature not in self.loaded.fill_values:
                    raise ValueError(f"Missing training-time fill for {feature}")
                row[feature] = self.loaded.fill_values[feature]
            else:
                if isinstance(raw_value, bool) or not isinstance(raw_value, (float, int)):
                    raise ValueError("Feature values must be finite numbers or null")
                row[feature] = float(raw_value)
            if not math.isfinite(row[feature]):
                raise ValueError("Feature values and fills must be finite")

        frame = pd.DataFrame([row], columns=self.loaded.feature_columns)
        model_input = frame
        if self.loaded.scaler is not None:
            scaled = self.loaded.scaler.transform(frame.to_numpy(dtype=np.float64))
            model_input = pd.DataFrame(scaled, columns=self.loaded.feature_columns)

        if not np.isfinite(model_input.to_numpy()).all():
            raise ValueError("Transformed features must be finite")
        classes = list(self.loaded.model.classes_)
        if len(classes) != 2 or set(classes) != {0, 1}:
            raise ValueError("Model must identify binary failure class 1")
        predict_input = model_input if hasattr(self.loaded.model, "feature_names_in_") else model_input.to_numpy()
        probabilities = np.asarray(self.loaded.model.predict_proba(predict_input))
        if probabilities.shape != (1, 2) or not np.isfinite(probabilities).all() or (probabilities < 0).any() or (probabilities > 1).any() or not np.isclose(probabilities.sum(), 1):
            raise ValueError("Model returned invalid probabilities")
        risk_score = float(probabilities[0, classes.index(1)])

        reasons: list[ReasonCode] = []
        if self.loaded.explanation_method == "linear_log_odds":
            # The coefficients act on transformed features; these are log-odds
            # contributions, not probabilities, causal effects, or SHAP values.
            coefficients = self.loaded.model.coef_[0]
            for index, feature_name in enumerate(self.loaded.feature_columns):
                contribution = float(coefficients[index] * model_input.iloc[0, index])
                if not math.isfinite(contribution):
                    raise ValueError("Model returned nonfinite explanations")
                reasons.append(ReasonCode(code=feature_name, contribution=round(contribution, 6), direction="UP" if contribution >= 0 else "DOWN"))

        top_reasons = sorted(reasons, key=lambda item: abs(item.contribution), reverse=True)[:5]
        return risk_score, _risk_bucket(risk_score), top_reasons

    def _resolve_version(self) -> str:
        self.artifacts_root.mkdir(parents=True, exist_ok=True)

        if self.requested_version and self.requested_version != "latest":
            candidate = self.artifacts_root / self.requested_version
            if not candidate.exists():
                raise FileNotFoundError(f"Requested model version not found: {self.requested_version}")
            self._validate_artifact_dir(candidate)
            return self.requested_version

        candidates = [
            path
            for path in self.artifacts_root.iterdir()
            if path.is_dir()
        ]
        candidates = [path for path in candidates if self._is_valid_artifact_dir(path)]

        if not candidates:
            raise FileNotFoundError(
                f"No model artifacts found in {self.artifacts_root}. "
                "Train a model first (make train-h30-all or make train-smoke)."
            )

        latest = sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]
        return latest.name

    def _is_valid_artifact_dir(self, artifact_dir: Path) -> bool:
        required_files = [
            artifact_dir / "model.joblib",
            artifact_dir / "version.json",
            artifact_dir / "feature_schema.json",
            artifact_dir / "metrics.json",
        ]
        return all(path.exists() for path in required_files)

    def _validate_artifact_dir(self, artifact_dir: Path) -> None:
        if not self._is_valid_artifact_dir(artifact_dir):
            raise FileNotFoundError(
                f"Artifact directory {artifact_dir} is missing one or more required files: "
                "model.joblib, version.json, feature_schema.json, metrics.json"
            )

    @staticmethod
    def _resolve_feature_columns(bundle: dict, feature_schema: dict) -> list[str]:
        ordered = feature_schema.get("ordered_features")
        columns = [item.get("name") for item in ordered] if isinstance(ordered, list) and all(isinstance(item, dict) for item in ordered) else []
        if not columns or any(not isinstance(name, str) or not name for name in columns) or len(set(columns)) != len(columns):
            raise ValueError("Artifact requires unique ordered feature names")
        if bundle.get("feature_columns") != columns:
            raise ValueError("Artifact feature schema disagrees with model bundle order")
        return columns

    @staticmethod
    def _load_json(path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
