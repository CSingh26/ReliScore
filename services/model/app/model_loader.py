from __future__ import annotations

import json
import os
from dataclasses import dataclass
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
                row[feature] = self.loaded.fill_values.get(feature, 0.0)
            else:
                row[feature] = float(raw_value)

        frame = pd.DataFrame([row], columns=self.loaded.feature_columns)
        model_input = frame
        if self.loaded.scaler is not None:
            scaled = self.loaded.scaler.transform(frame.to_numpy(dtype=np.float64))
            model_input = pd.DataFrame(scaled, columns=self.loaded.feature_columns)

        probabilities = self.loaded.model.predict_proba(model_input)
        risk_score = float(probabilities[:, 1][0]) if probabilities.ndim > 1 else float(probabilities[0])

        reasons: list[ReasonCode] = []
        for feature_name in self.loaded.feature_columns:
            value = float(row[feature_name])
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
        ordered_features = feature_schema.get("ordered_features")
        if isinstance(ordered_features, list) and ordered_features:
            columns = [str(item.get("name")) for item in ordered_features if isinstance(item, dict)]
            if columns and all(columns):
                return columns

        bundle_features = bundle.get("feature_columns")
        if isinstance(bundle_features, list) and bundle_features:
            return [str(name) for name in bundle_features]

        raise ValueError("Unable to resolve feature columns from feature_schema.json or model bundle")

    @staticmethod
    def _load_json(path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
