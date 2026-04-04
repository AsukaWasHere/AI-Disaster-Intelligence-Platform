"""
routes/risk.py
--------------
POST /risk
Computes a composite risk score from damage, casualties, and magnitude.
Can be called independently of /predict (e.g., given ground truth data).
"""

from fastapi import APIRouter, HTTPException

from src.api.schemas      import RiskRequest, RiskResponse
from src.utils.risk       import compute_single_risk_score
from src.utils.config     import CONFIG
from src.utils.logger     import get_logger
from src.utils.exceptions import InvalidInputError

logger = get_logger(__name__)
router = APIRouter()

_RISK_TIERS = [(25, "Low"), (50, "Medium"), (75, "High"), (101, "Critical")]


def _risk_tier(score: float) -> str:
    for threshold, label in _RISK_TIERS:
        if score < threshold:
            return label
    return "Critical"


@router.post("", response_model=RiskResponse)
def compute_risk(req: RiskRequest):
    """
    Compute a 0–100 composite risk score.

    Accepts optional weight overrides to customise the scoring formula
    (e.g., an emergency manager may weight deaths more heavily than damage).
    """
    logger.info(
        "POST /risk — log_damage=%.3f deaths=%.0f injuries=%.0f magnitude=%.2f",
        req.predicted_log_damage, req.deaths, req.injuries, req.magnitude,
    )

    try:
        weights = req.weights or CONFIG["risk_score"]["weights"]

        score = compute_single_risk_score(
            predicted_log_damage=req.predicted_log_damage,
            deaths=req.deaths,
            injuries=req.injuries,
            magnitude=req.magnitude,
            weights=weights,
        )

        # Return normalised contribution of each component for transparency
        import numpy as np
        MAX_LOG_DAMAGE = 23.0
        MAX_DEATHS     = 200.0
        MAX_INJURIES   = 2000.0
        MAX_MAGNITUDE  = 100.0

        components = {
            "damage":    round(min(req.predicted_log_damage / MAX_LOG_DAMAGE, 1.0) * weights["damage"] * 100, 2),
            "deaths":    round(min(req.deaths    / MAX_DEATHS,    1.0) * weights["deaths"]    * 100, 2),
            "injuries":  round(min(req.injuries  / MAX_INJURIES,  1.0) * weights["injuries"]  * 100, 2),
            "magnitude": round(min(req.magnitude / MAX_MAGNITUDE, 1.0) * weights["magnitude"] * 100, 2),
        }

        return RiskResponse(
            risk_score=round(score, 2),
            tier=_risk_tier(score),
            components=components,
        )

    except InvalidInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in /risk: %s", exc)
        raise HTTPException(status_code=500, detail="Risk computation failed.")