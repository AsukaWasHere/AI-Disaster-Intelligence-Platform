"""
schemas.py
----------
Pydantic request and response models for all API endpoints.
Validation happens automatically before any route handler runs.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ── Shared ────────────────────────────────────────────────────────────────────

class TopPrediction(BaseModel):
    label: str
    probability: float


# ── /predict ─────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    lat:       float  = Field(...,  ge=-90,  le=90,   description="Latitude of event origin")
    lon:       float  = Field(...,  ge=-180, le=180,  description="Longitude of event origin")
    month:     int    = Field(...,  ge=1,    le=12,   description="Month number (1–12)")
    magnitude: float  = Field(0.0, ge=0,              description="Event magnitude (optional)")
    narrative: Optional[str] = Field(None, max_length=2000, description="Event narrative for NLP features")
    state:     Optional[str] = Field(None, max_length=50)
    year:      Optional[int] = Field(None, ge=1950, le=2100)

    @field_validator("narrative")
    @classmethod
    def strip_narrative(cls, v):
        return v.strip() if v else v


class PredictResponse(BaseModel):
    event_type:     str
    top_predictions: list[TopPrediction]
    damage_usd:     float  = Field(..., description="Predicted total damage in USD")
    damage_tier:    str    = Field(..., description="Minor / Moderate / Major / Catastrophic")
    risk_score:     float  = Field(..., ge=0, le=100)
    explanation:    str    = Field(..., description="Human-readable summary of the prediction")
    keywords:       list[str] = Field(default_factory=list)


# ── /risk ─────────────────────────────────────────────────────────────────────

class RiskRequest(BaseModel):
    predicted_log_damage: float = Field(0.0, ge=0)
    deaths:               float = Field(0.0, ge=0)
    injuries:             float = Field(0.0, ge=0)
    magnitude:            float = Field(0.0, ge=0)
    weights: Optional[dict[str, float]] = Field(
        None,
        description="Override risk weights. Keys: damage, deaths, injuries, magnitude."
    )

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v):
        if v is None:
            return v
        required = {"damage", "deaths", "injuries", "magnitude"}
        if not required.issubset(v.keys()):
            raise ValueError(f"weights must contain keys: {required}")
        return v


class RiskResponse(BaseModel):
    risk_score: float = Field(..., ge=0, le=100)
    tier:       str   = Field(..., description="Low / Medium / High / Critical")
    components: dict[str, float]


# ── /insights ─────────────────────────────────────────────────────────────────

class InsightsSummary(BaseModel):
    total_events:      int
    top_event_types:   list[dict]
    avg_damage_usd:    float
    avg_risk_score:    float
    high_risk_states:  list[str]
    date_range:        dict[str, int]