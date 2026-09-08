from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

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
    try:
        model_store.load()
    except (FileNotFoundError, ValueError):
        # Stay inspectable without pretending a missing artifact is a model.
        pass

    def require_model():
        if model_store.loaded is None:
            raise HTTPException(status_code=503, detail="Model unavailable; install a validated artifact and restart")
        return model_store.loaded

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        loaded = model_store.loaded
        return HealthResponse(status="ok" if loaded else "unavailable", model_loaded=loaded is not None, model_version=loaded.model_version if loaded else "unavailable")

    @app.get("/model/info", response_model=ModelInfoResponse)
    def model_info() -> ModelInfoResponse:
        loaded = require_model()
        return ModelInfoResponse(
            model_version=loaded.model_version,
            model_type=loaded.model_type,
            horizon_days=loaded.horizon_days,
            features=loaded.feature_columns,
            metrics=loaded.metrics,
            provenance=loaded.provenance,
            explanation_method=loaded.explanation_method,
        )

    @app.post("/score", response_model=ScoreResponse)
    def score(item: ScoreRequest) -> ScoreResponse:
        require_model()
        try:
            risk_score, risk_bucket, top_reasons = model_store.score(item.features)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return ScoreResponse(
            drive_id=item.drive_id,
            day=item.day,
            risk_score=risk_score,
            risk_bucket=risk_bucket,
            top_reasons=top_reasons,
            model_version=require_model().model_version,
            scored_at=datetime.now(timezone.utc),
        )

    @app.post("/score_batch", response_model=list[ScoreResponse])
    def score_batch(payload: BatchScoreRequest) -> list[ScoreResponse]:
        responses: list[ScoreResponse] = []
        loaded = require_model()
        scored_at = datetime.now(timezone.utc)

        for item in payload.items:
            try:
                risk_score, risk_bucket, top_reasons = model_store.score(item.features)
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
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
