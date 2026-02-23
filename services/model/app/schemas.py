from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class RiskBucket(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class ScoreRequest(SchemaModel):
    drive_id: str
    day: date
    features: dict[str, float | None]


class ReasonCode(SchemaModel):
    code: str
    contribution: float
    direction: str


class ScoreResponse(SchemaModel):
    drive_id: str
    day: date
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_bucket: RiskBucket
    top_reasons: list[ReasonCode]
    model_version: str
    scored_at: datetime


class BatchScoreRequest(SchemaModel):
    items: list[ScoreRequest]


class HealthResponse(SchemaModel):
    status: str
    model_loaded: bool
    model_version: str


class ModelInfoResponse(SchemaModel):
    model_version: str
    model_type: str
    horizon_days: int
    features: list[str]
    metrics: dict[str, float | list[dict[str, float]] | str]
