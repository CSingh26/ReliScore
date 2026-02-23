from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI

from app.model_loader import ModelStore
from app.schemas import (
  BatchScoreRequest,
  HealthResponse,
  ModelInfoResponse,
  ScoreRequest,
  ScoreResponse,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="ReliScore Model Service",
        description="FastAPI service for drive failure-risk scoring",
        version="0.1.0",
    )
    model_store = ModelStore()
    model_store.load()

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        loaded = model_store.loaded
        assert loaded is not None
        return HealthResponse(status="ok", model_loaded=True, model_version=loaded.model_version)

    @app.get("/model/info", response_model=ModelInfoResponse)
    def model_info() -> ModelInfoResponse:
        loaded = model_store.loaded or model_store.load()
        return ModelInfoResponse(
            model_version=loaded.model_version,
            model_type=loaded.model_type,
            horizon_days=loaded.horizon_days,
            features=loaded.feature_columns,
            metrics=loaded.metrics,
        )

    @app.post("/score", response_model=ScoreResponse)
    def score(item: ScoreRequest) -> ScoreResponse:
        risk_score, risk_bucket, top_reasons = model_store.score(item.features)
        return ScoreResponse(
            drive_id=item.drive_id,
            day=item.day,
            risk_score=risk_score,
            risk_bucket=risk_bucket,
            top_reasons=top_reasons,
            model_version=(model_store.loaded or model_store.load()).model_version,
            scored_at=datetime.now(timezone.utc),
        )

    @app.post("/score_batch", response_model=list[ScoreResponse])
    def score_batch(payload: BatchScoreRequest) -> list[ScoreResponse]:
        responses: list[ScoreResponse] = []
        loaded = model_store.loaded or model_store.load()
        scored_at = datetime.now(timezone.utc)

        for item in payload.items:
            risk_score, risk_bucket, top_reasons = model_store.score(item.features)
            responses.append(
                ScoreResponse(
                    drive_id=item.drive_id,
                    day=item.day,
                    risk_score=risk_score,
                    risk_bucket=risk_bucket,
                    top_reasons=top_reasons,
                    model_version=loaded.model_version,
                    scored_at=scored_at,
                )
            )

        return responses

    return app


app = create_app()
