from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid", allow_inf_nan=False)


class RiskBucket(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class ScoreRequest(SchemaModel):
    drive_id: str = Field(min_length=1, max_length=128, pattern=r"^\S+$")
    day: date
    features: dict[Annotated[str, Field(min_length=1, max_length=128)], Annotated[float, Field(strict=True, allow_inf_nan=False)] | None] = Field(min_length=1, max_length=256)


class ReasonCode(SchemaModel):
    code: str
    contribution: float
    direction: Literal["UP", "DOWN"]


class ScoreResponse(SchemaModel):
    drive_id: str
    day: date
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_bucket: RiskBucket
    top_reasons: list[ReasonCode]
    model_version: str
    scored_at: datetime


class BatchScoreRequest(SchemaModel):
    items: list[ScoreRequest] = Field(min_length=1, max_length=1000)


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
    provenance: dict = Field(default_factory=dict)
    explanation_method: str = "unavailable"
