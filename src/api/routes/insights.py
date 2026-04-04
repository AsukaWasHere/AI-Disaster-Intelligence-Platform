"""
routes/insights.py
------------------
GET /insights
Returns summary statistics aggregated from the processed dataset.
Loaded once at first call and cached for the process lifetime.
Suitable for dashboard overview cards and map initialisation.
"""

import pandas as pd
from pathlib import Path
from functools import lru_cache

from fastapi import APIRouter, HTTPException

from src.api.schemas      import InsightsSummary
from src.utils.config     import CONFIG
from src.utils.logger     import get_logger
from src.utils.exceptions import DataLoadError

logger = get_logger(__name__)
router = APIRouter()


@lru_cache(maxsize=1)
def _load_processed_data() -> pd.DataFrame:
    """
    Load the full processed Parquet file once and cache it.
    lru_cache(maxsize=1) ensures this runs only on the first /insights call.
    """
    path = Path(CONFIG["data"]["processed_dir"]) / "noaa_processed.parquet"
    if not path.exists():
        raise DataLoadError(
            f"Processed data not found at {path}. Run the data pipeline first."
        )
    logger.info("Loading processed dataset for insights: %s", path)
    df = pd.read_parquet(
        path,
        columns=[
            "EVENT_TYPE", "STATE", "YEAR",
            "TOTAL_DAMAGE_USD", "RISK_SCORE",
            "DEATHS_DIRECT", "DEATHS_INDIRECT",
            "INJURIES_DIRECT", "INJURIES_INDIRECT",
        ],
    )
    logger.info("Insights dataset loaded: %d rows.", len(df))
    return df


@router.get("", response_model=InsightsSummary)
def get_insights():
    """
    Return high-level summary statistics from the processed disaster dataset.

    All values are computed from data/processed/noaa_processed.parquet.
    The result is effectively cached after the first call.
    """
    logger.info("GET /insights")

    try:
        df = _load_processed_data()
    except DataLoadError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to load processed data: %s", exc)
        raise HTTPException(status_code=500, detail="Could not load dataset.")

    try:
        total_events = int(len(df))

        # Top 10 event types by frequency
        top_event_types = (
            df["EVENT_TYPE"]
            .astype(str)
            .value_counts()
            .head(10)
            .reset_index()
            .rename(columns={"index": "event_type", "EVENT_TYPE": "count"})
            .to_dict(orient="records")
        )

        avg_damage = float(df["TOTAL_DAMAGE_USD"].fillna(0).mean())

        avg_risk = float(df["RISK_SCORE"].fillna(0).mean()) \
                   if "RISK_SCORE" in df.columns else 0.0

        # High-risk states: states whose median RISK_SCORE exceeds the 75th percentile
        if "RISK_SCORE" in df.columns and "STATE" in df.columns:
            threshold = df["RISK_SCORE"].quantile(0.75)
            state_risk = (
                df.groupby("STATE")["RISK_SCORE"]
                .median()
                .sort_values(ascending=False)
            )
            high_risk_states = state_risk[state_risk >= threshold].head(10).index.tolist()
        else:
            high_risk_states = []

        date_range = {
            "min_year": int(df["YEAR"].min()) if "YEAR" in df.columns else 0,
            "max_year": int(df["YEAR"].max()) if "YEAR" in df.columns else 0,
        }

        return InsightsSummary(
            total_events=total_events,
            top_event_types=top_event_types,
            avg_damage_usd=round(avg_damage, 2),
            avg_risk_score=round(avg_risk, 2),
            high_risk_states=high_risk_states,
            date_range=date_range,
        )

    except Exception as exc:
        logger.exception("Error computing insights: %s", exc)
        raise HTTPException(status_code=500, detail="Insights computation failed.")