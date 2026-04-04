"""
src/utils/risk.py
-----------------
Composite Risk Score engine.

RISK_SCORE = 100 × Σ(weight_i × normalize(component_i))

Components:
  - predicted_damage:  model output (log scale → normalized)
  - deaths:            direct + indirect
  - injuries:          direct + indirect
  - magnitude:         physical measurement

All components are MinMax normalized to [0,1] independently.
Weights are configurable via configs/config.yaml (risk_score.weights).
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from src.utils.config import CONFIG
from src.utils.logger import get_logger
from src.utils.exceptions import InvalidInputError

logger = get_logger(__name__)


def compute_risk_scores(
    df: pd.DataFrame,
    predicted_log_damage: np.ndarray | None = None,
    weights: dict | None = None,
) -> pd.Series:
    """
    Compute a composite risk score (0–100) for each event row.

    Args:
        df: DataFrame with columns:
              DEATHS_DIRECT, DEATHS_INDIRECT,
              INJURIES_DIRECT, INJURIES_INDIRECT,
              MAGNITUDE, (optionally LOG_DAMAGE_USD)
        predicted_log_damage: Optional array of model-predicted LOG_DAMAGE_USD.
                              If None, falls back to LOG_DAMAGE_USD column in df.
        weights: Optional dict overriding config weights.
                 Keys: damage, deaths, injuries, magnitude.
                 Values must sum to approximately 1.0.

    Returns:
        pd.Series named "RISK_SCORE" with values in [0, 100].

    Raises:
        InvalidInputError: If required columns are missing.
    """
    w = weights or CONFIG["risk_score"]["weights"]
    _validate_weights(w)

    # ── Build component vectors ───────────────────────────────────────────────

    # Damage: use model prediction if available, else column from df
    if predicted_log_damage is not None:
        if len(predicted_log_damage) != len(df):
            raise InvalidInputError(
                f"predicted_log_damage length {len(predicted_log_damage)} "
                f"!= df length {len(df)}."
            )
        damage_vec = np.asarray(predicted_log_damage, dtype="float64")
    elif "LOG_DAMAGE_USD" in df.columns:
        damage_vec = df["LOG_DAMAGE_USD"].fillna(0).values.astype("float64")
    else:
        logger.warning("No damage data available — damage component set to 0.")
        damage_vec = np.zeros(len(df))

    deaths_vec = (
        df.get("DEATHS_DIRECT", 0) + df.get("DEATHS_INDIRECT", 0)
    ).fillna(0).values.astype("float64")

    injuries_vec = (
        df.get("INJURIES_DIRECT", 0) + df.get("INJURIES_INDIRECT", 0)
    ).fillna(0).values.astype("float64")

    magnitude_vec = df.get("MAGNITUDE", pd.Series(0, index=df.index)) \
                      .fillna(0).values.astype("float64")

    # ── Normalize each component independently to [0, 1] ────────────────────
    # Each component has a very different scale (deaths: 0–100, damage: 0–23 log).
    # MinMax normalization ensures no single component dominates purely due to
    # its numeric range.

    components = np.column_stack([damage_vec, deaths_vec, injuries_vec, magnitude_vec])
    scaler = MinMaxScaler(feature_range=(0, 1))
    normalized = scaler.fit_transform(components)  # shape: (n, 4)

    # ── Weighted sum ──────────────────────────────────────────────────────────
    weight_vec = np.array([
        w["damage"],
        w["deaths"],
        w["injuries"],
        w["magnitude"],
    ])

    raw_score = normalized @ weight_vec          # dot product: (n, 4) × (4,) → (n,)
    risk_score = (raw_score * 100).clip(0, 100)  # Scale to 0-100

    result = pd.Series(risk_score.astype("float32"), index=df.index, name="RISK_SCORE")

    logger.info(
        "Risk scores computed: mean=%.2f | p50=%.2f | p95=%.2f | max=%.2f",
        result.mean(),
        result.quantile(0.50),
        result.quantile(0.95),
        result.max(),
    )
    return result


def compute_single_risk_score(
    predicted_log_damage: float = 0.0,
    deaths: float = 0.0,
    injuries: float = 0.0,
    magnitude: float = 0.0,
    weights: dict | None = None,
    reference_df: pd.DataFrame | None = None,
) -> float:
    """
    Compute a risk score for a single event (API inference path).

    Because MinMax normalization is relative, a single event needs reference
    data to normalize against. If reference_df is provided, normalization
    is done relative to that distribution. Otherwise, simple weight-sum
    with log-scale capping is used.

    Args:
        predicted_log_damage: log1p(predicted_damage_USD)
        deaths:               total deaths
        injuries:             total injuries
        magnitude:            event magnitude
        weights:              optional weight override
        reference_df:         if provided, normalize against this population

    Returns:
        float in [0, 100]
    """
    w = weights or CONFIG["risk_score"]["weights"]

    if reference_df is not None:
        # Append the single event to the reference, score it, then extract
        single_row = pd.DataFrame([{
            "LOG_DAMAGE_USD": predicted_log_damage,
            "DEATHS_DIRECT": deaths,
            "DEATHS_INDIRECT": 0,
            "INJURIES_DIRECT": injuries,
            "INJURIES_INDIRECT": 0,
            "MAGNITUDE": magnitude,
        }])
        combined = pd.concat([reference_df, single_row], ignore_index=True)
        scores = compute_risk_scores(combined)
        return float(scores.iloc[-1])

    # Fallback: simple weighted average with log-scale capping
    # Normalize each component by reasonable maximums
    MAX_LOG_DAMAGE = 23.0   # log1p(10 billion)
    MAX_DEATHS     = 200.0
    MAX_INJURIES   = 2000.0
    MAX_MAGNITUDE  = 100.0

    score = (
        w["damage"]    * min(predicted_log_damage / MAX_LOG_DAMAGE, 1.0)
        + w["deaths"]   * min(deaths / MAX_DEATHS, 1.0)
        + w["injuries"] * min(injuries / MAX_INJURIES, 1.0)
        + w["magnitude"] * min(magnitude / MAX_MAGNITUDE, 1.0)
    ) * 100

    return round(float(np.clip(score, 0, 100)), 2)


def _validate_weights(w: dict) -> None:
    """Warn if weights don't sum to ~1.0."""
    required = {"damage", "deaths", "injuries", "magnitude"}
    missing = required - set(w.keys())
    if missing:
        raise InvalidInputError(f"Missing risk score weight keys: {missing}")
    total = sum(w.values())
    if not (0.95 <= total <= 1.05):
        logger.warning(
            "Risk score weights sum to %.3f (expected ~1.0). Scores may not be on [0,100].",
            total,
        )