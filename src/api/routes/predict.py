"""
routes/predict.py
-----------------
POST /predict
Runs classification (EVENT_TYPE) + regression (TOTAL_DAMAGE_USD)
and returns a unified prediction response with risk score.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas          import PredictRequest, PredictResponse, TopPrediction
from src.api.dependencies     import get_classifier, get_regressor, get_keyword_extractor
from src.utils.risk           import compute_single_risk_score
from src.utils.logger         import get_logger
from src.utils.exceptions     import ModelNotFoundError, PredictionError, InvalidInputError
from src.utils.config         import CONFIG

logger = get_logger(__name__)
router = APIRouter()

# Load feature columns from training data to ensure alignment at inference time
_processed_dir = Path(CONFIG["data"]["processed_dir"])
_feature_cols_path = _processed_dir / "feature_columns.json"

if _feature_cols_path.exists():
    with open(_feature_cols_path, "r") as f:
        _feature_cols = json.load(f)
    # Extract STATE names from the feature columns (filter for STATE_* columns)
    _all_features = _feature_cols.get("structured", [])
    STATE_COLS = [c.replace("STATE_", "") for c in _all_features if c.startswith("STATE_")]
else:
    # Fallback to default if feature_columns.json not found
    logger.warning("feature_columns.json not found, using default states list")
    STATE_COLS = []

# If we still don't have states, use the hardcoded list as fallback
if not STATE_COLS:
    STATE_COLS = [
        "ALABAMA", "ALASKA", "ARIZONA", "ARKANSAS", "CALIFORNIA",
        "COLORADO", "CONNECTICUT", "DELAWARE", "FLORIDA", "GEORGIA",
        "HAWAII", "IDAHO", "ILLINOIS", "INDIANA", "IOWA", "KANSAS",
        "KENTUCKY", "LOUISIANA", "MAINE", "MARYLAND", "MASSACHUSETTS",
        "MICHIGAN", "MINNESOTA", "MISSISSIPPI", "MISSOURI", "MONTANA",
        "NEBRASKA", "NEVADA", "NEW HAMPSHIRE", "NEW JERSEY", "NEW MEXICO",
        "NEW YORK", "NORTH CAROLINA", "NORTH DAKOTA", "OHIO", "OKLAHOMA",
        "OREGON", "PENNSYLVANIA", "RHODE ISLAND", "SOUTH CAROLINA",
        "SOUTH DAKOTA", "TENNESSEE", "TEXAS", "UTAH", "VERMONT",
        "VIRGINIA", "WASHINGTON", "WEST VIRGINIA", "WISCONSIN", "WYOMING",
    ]

# Damage tier thresholds (USD)
_DAMAGE_TIERS = [
    (0,           "None"),
    (10_000,      "Minor"),
    (1_000_000,   "Moderate"),
    (100_000_000, "Major"),
    (float("inf"),"Catastrophic"),
]

_RISK_TIERS = [
    (25,  "Low"),
    (50,  "Medium"),
    (75,  "High"),
    (101, "Critical"),
]


def _damage_tier_label(usd: float) -> str:
    for threshold, label in _DAMAGE_TIERS:
        if usd <= threshold:
            return label
    return "Catastrophic"


def _risk_tier_label(score: float) -> str:
    for threshold, label in _RISK_TIERS:
        if score < threshold:
            return label
    return "Critical"


# US Census region mapping from state (same as in feature_engineering.py)
STATE_TO_REGION = {
    "ALABAMA": "South", "ALASKA": "West", "ARIZONA": "West",
    "ARKANSAS": "South", "CALIFORNIA": "West", "COLORADO": "West",
    "CONNECTICUT": "Northeast", "DELAWARE": "South", "FLORIDA": "South",
    "GEORGIA": "South", "HAWAII": "West", "IDAHO": "West",
    "ILLINOIS": "Midwest", "INDIANA": "Midwest", "IOWA": "Midwest",
    "KANSAS": "Midwest", "KENTUCKY": "South", "LOUISIANA": "South",
    "MAINE": "Northeast", "MARYLAND": "South", "MASSACHUSETTS": "Northeast",
    "MICHIGAN": "Midwest", "MINNESOTA": "Midwest", "MISSISSIPPI": "South",
    "MISSOURI": "Midwest", "MONTANA": "West", "NEBRASKA": "Midwest",
    "NEVADA": "West", "NEW HAMPSHIRE": "Northeast", "NEW JERSEY": "Northeast",
    "NEW MEXICO": "West", "NEW YORK": "Northeast", "NORTH CAROLINA": "South",
    "NORTH DAKOTA": "Midwest", "OHIO": "Midwest", "OKLAHOMA": "South",
    "OREGON": "West", "PENNSYLVANIA": "Northeast", "RHODE ISLAND": "Northeast",
    "SOUTH CAROLINA": "South", "SOUTH DAKOTA": "Midwest", "TENNESSEE": "South",
    "TEXAS": "South", "UTAH": "West", "VERMONT": "Northeast",
    "VIRGINIA": "South", "WASHINGTON": "West", "WEST VIRGINIA": "South",
    "WISCONSIN": "Midwest", "WYOMING": "West",
}

# US Season mapping by month
MONTH_TO_SEASON = {
    1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring",
    5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer",
    9: "Fall", 10: "Fall", 11: "Fall", 12: "Winter",
}

# Categorical values that were one-hot encoded during training (in order)
# These must match exactly what was created in src/data/pipeline.py

# SEASONS - must match exactly what was used during training (no "Unknown" in training data)
SEASONS = ["Fall", "Spring", "Summer", "Winter"]

# REGIONS - must match exactly what was used during training (no "Unknown" in training data)
REGIONS = ["Midwest", "Northeast", "South", "West", "Unknown"]

# STATES - must match exactly what was used during training
# This includes US states, territories, and maritime zones from the NOAA dataset
STATES = [
    "ALABAMA", "ALASKA", "AMERICAN SAMOA", "ARIZONA", "ARKANSAS",
    "ATLANTIC SOUTH", "CALIFORNIA", "COLORADO", "CONNECTICUT", "DELAWARE",
    "DISTRICT OF COLUMBIA", "FLORIDA", "GEORGIA", "GULF OF MEXICO",
    "HAWAII", "IDAHO", "ILLINOIS", "INDIANA", "IOWA", "KANSAS",
    "KENTUCKY", "LAKE ERIE", "LAKE MICHIGAN", "LAKE ST CLAIR",
    "LOUISIANA", "MAINE", "MARYLAND", "MASSACHUSETTS", "MICHIGAN",
    "MINNESOTA", "MISSISSIPPI", "MISSOURI", "MONTANA", "NEBRASKA",
    "NEVADA", "NEW HAMPSHIRE", "NEW JERSEY", "NEW MEXICO", "NEW YORK",
    "NORTH CAROLINA", "NORTH DAKOTA", "OHIO", "OKLAHOMA", "OREGON",
    "PENNSYLVANIA", "PUERTO RICO", "SOUTH CAROLINA", "SOUTH DAKOTA",
    "TENNESSEE", "TEXAS", "UTAH", "VERMONT", "VIRGIN ISLANDS",
    "VIRGINIA", "WASHINGTON", "WEST VIRGINIA", "WISCONSIN", "WYOMING",
]


def _build_feature_row(req: PredictRequest) -> pd.DataFrame:
    """
    Convert a PredictRequest into a single-row feature DataFrame.

    This mirrors the feature columns produced by feature_engineering.py.
    For inference on a single event, we construct the same columns the
    model was trained on. Missing optional fields default to 0.

    The feature names MUST match exactly those in the training data, which
    includes one-hot encoded columns for SEASON and REGION.
    """
    # Determine season from month - default to Fall for unknown months
    # (must use one of the actual seasons from training data)
    season = MONTH_TO_SEASON.get(req.month, "Fall")

    # Determine region from state (if provided)
    # For inference without state, default to South (must use a valid region from training)
    # If you have state info, pass it in PredictRequest
    state_upper = (req.state or "").upper() if hasattr(req, "state") else ""
    region = STATE_TO_REGION.get(state_upper, "South")  # Default to South for unknown states

    # If lat/lon are provided and no valid state, try to infer region from coordinates
    # This is a simplified geocoder for major US regions
    if (req.lat or 0) != 0 and (req.lon or 0) != 0 and not state_upper:
        region = _infer_region_from_coords(req.lat, req.lon)

    is_high_season = int(3 <= req.month <= 10)
    decade = int((req.year or 2020) // 10 * 10)

    row = {
        # Time features
        "YEAR":            req.year or 2020,
        "MONTH_NUM":       req.month,
        "IS_HIGH_SEASON":  is_high_season,
        "DECADE":          decade,
        # Damage (will be predicted, but column must exist)
        "LOG_DAMAGE_USD":  0.0,
        "DAMAGE_TIER":     0,
        # Severity
        "TOTAL_CASUALTIES": 0.0,
        "SEVERITY_INDEX":  0.0,
        # Physical
        "MAGNITUDE":       req.magnitude,
        # Geospatial (using encoded values, not raw lat/lon)
        "GEO_CLUSTER":     -1,       # Unknown without KMeans
        "HAS_GEOSPATIAL":  1 if (req.lat != 0 and req.lon != 0) else 0,
        # Text-derived
        "NARRATIVE_LENGTH": len(req.narrative.split()) if req.narrative else 0,
        # Risk
        "RISK_SCORE":      0.0,
    }

    # Add one-hot encoded SEASON columns (must match training order)
    for s in SEASONS:
        row[f"SEASON_{s}"] = int(season == s)

    # Add one-hot encoded REGION columns (must match training order)
    for r in REGIONS:
        row[f"REGION_{r}"] = int(region == r)

    # Add one-hot encoded STATE columns (must match training order)
    # For inference, only the matching state gets 1, all others get 0
    for st in STATES:
        row[f"STATE_{st}"] = int(state_upper == st)

    return pd.DataFrame([row])


def _infer_region_from_coords(lat: float, lon: float) -> str:
    """
    Simple region inference from coordinates for inference without state.
    This is a simplified geocoder that approximates US regions.
    """
    if pd.isna(lat) or pd.isna(lon):
        return "South"  # Default to South for unknown coordinates

    # Approximate US region boundaries
    # Note: This is approximate; for production use a proper geocoder

    # Alaska and Hawaii
    if lat > 50:  # Alaska (~51-71)
        return "West"

    # Northeast: 39-47.5, -79 to -65
    if 39 <= lat <= 47.5 and -79 <= lon <= -65:
        return "Northeast"

    # Southeast: 25-39, -85 to -75
    if 25 <= lat <= 39 and -85 <= lon <= -75:
        return "South"

    # Midwest: 35-50, -104 to -85 (excluding DE/MD/DC)
    if 35 <= lat <= 50 and -104 <= lon <= -85:
        return "Midwest"

    # West: 32-50, -125 to -104 (excluding AK)
    if 32 <= lat <= 50 and -125 <= lon <= -104:
        return "West"

    # Southwest: 32-40, -118 to -104 (TX to CO/WY)
    if 32 <= lat <= 40 and -118 <= lon <= -104:
        return "West"

    return "South"  # Default to South for coordinates outside known regions

def _align_features(X: pd.DataFrame) -> pd.DataFrame:
    """
    Align inference features with training schema using feature_columns.json
    """
    feature_path = Path(CONFIG["data"]["processed_dir"]) / "feature_columns.json"

    if not feature_path.exists():
        raise ValueError("feature_columns.json not found")

    with open(feature_path, "r") as f:
        feature_cols = json.load(f)

    if "structured" not in feature_cols or not feature_cols["structured"]:
        raise ValueError("Invalid feature_columns.json")

    expected_cols = feature_cols["structured"]

    # Add missing columns
    for col in expected_cols:
        if col not in X.columns:
            X[col] = 0

    # Remove extra columns
    X = X.drop(columns=[c for c in X.columns if c not in expected_cols])

    # 🔥 FORCE EXACT ORDER
    X = X.reindex(columns=expected_cols)

    return X


@router.post("", response_model=PredictResponse)
def predict(
    req: PredictRequest,
    classifier=Depends(get_classifier),
    regressor=Depends(get_regressor),
    kw_extractor=Depends(get_keyword_extractor),
):
    """
    Run event type classification and damage regression for a single event.

    Steps:
    1. Build feature row from request fields
    2. Run classifier → top-N EVENT_TYPE predictions
    3. Run regressor  → predicted damage (USD)
    4. Compute risk score from damage + magnitude
    5. Extract keywords from narrative (if provided)
    6. Build human-readable explanation
    """
    logger.info(
        "POST /predict — lat=%.4f lon=%.4f month=%d magnitude=%.2f",
        req.lat, req.lon, req.month, req.magnitude,
    )

    try:
        X = _build_feature_row(req)
        X = _align_features(X) 

        # ── Classification ────────────────────────────────────────────────────
        top_preds = classifier.predict_top_n(X, n=3)
        top_event_type = top_preds[0][0]["label"]
        top_predictions = [
            TopPrediction(label=p["label"], probability=p["probability"])
            for p in top_preds[0]
        ]

        # ── Regression ────────────────────────────────────────────────────────
        log_preds = regressor.predict(X, return_log_scale=True)
        damage_usd = float(np.expm1(log_preds[0]))
        log_damage = float(log_preds[0])

        # ── Risk score ────────────────────────────────────────────────────────
        risk_score = compute_single_risk_score(
            predicted_log_damage=log_damage,
            deaths=0.0,
            injuries=0.0,
            magnitude=req.magnitude,
        )

        # ── Keywords ──────────────────────────────────────────────────────────
        keywords = []
        if req.narrative:
            keywords = kw_extractor.extract(req.narrative, top_n=5)

        # ── Explanation ───────────────────────────────────────────────────────
        tier = _damage_tier_label(damage_usd)
        risk_tier = _risk_tier_label(risk_score)
        explanation = (
            f"The most likely disaster type is '{top_event_type}' "
            f"(confidence {top_predictions[0].probability:.1%}). "
            f"Estimated damage: ${damage_usd:,.0f} ({tier}). "
            f"Risk score: {risk_score:.1f}/100 ({risk_tier})."
        )

        return PredictResponse(
            event_type=top_event_type,
            top_predictions=top_predictions,
            damage_usd=round(damage_usd, 2),
            damage_tier=tier,
            risk_score=round(risk_score, 2),
            explanation=explanation,
            keywords=keywords,
        )

    except ModelNotFoundError as exc:
        logger.error("Model not found: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except (PredictionError, InvalidInputError) as exc:
        logger.error("Prediction error: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in /predict: %s", str(exc))
        raise HTTPException(status_code=500, detail="Internal prediction error.")