from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskBucket(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class ScoreRequest(BaseModel):
    drive_id: str
    day: date
    features: dict[str, float | None]


class ReasonCode(BaseModel):
    code: str
    contribution: float
    direction: str


class ScoreResponse(BaseModel):
    drive_id: str
    day: date
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_bucket: RiskBucket
    top_reasons: list[ReasonCode]
    model_version: str
    scored_at: datetime


class BatchScoreRequest(BaseModel):
    items: list[ScoreRequest]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str


class ModelInfoResponse(BaseModel):
    model_version: str
    model_type: str
    horizon_days: int
    features: list[str]
    metrics: dict[str, float | list[dict[str, float]] | str]
