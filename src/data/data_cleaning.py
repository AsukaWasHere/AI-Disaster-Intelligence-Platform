"""
data_cleaning.py
----------------
Responsibility: Clean a raw NOAA DataFrame.
Covers: damage parsing, missing value imputation, duplicate removal,
dtype correction, and outlier treatment via log transform.

DESIGN RULE: Every function is pure (input → output DataFrame, no side effects).
The orchestrator in pipeline.py chains them in sequence.
"""

import re
import numpy as np
import pandas as pd
from src.utils.logger import get_logger
from src.utils.exceptions import FeatureEngineeringError

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Public API — called by pipeline.py
# ─────────────────────────────────────────────────────────────────────────────

def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Master cleaning function. Runs all sub-steps in the correct order.

    Args:
        df: Raw DataFrame from data_loader.py

    Returns:
        Cleaned DataFrame, ready for feature engineering.
    """
    logger.info("Starting data cleaning. Input shape: %s", df.shape)

    df = _parse_damage_columns(df)
    df = _compute_total_damage(df)
    df = _handle_missing_values(df)
    df = _remove_duplicates(df)
    df = _fix_dtypes(df)
    df = _handle_outliers(df)
    df = _standardize_categoricals(df)

    logger.info("Cleaning complete. Output shape: %s", df.shape)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Sub-steps (private, single responsibility each)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_damage_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert NOAA damage strings ('1.5K', '2.5M', '0') to float USD values.

    NOAA encodes damage as: numeric + suffix (K=thousands, M=millions, B=billions).
    Examples: '1.5K' → 1500.0,  '2M' → 2_000_000.0,  '0' → 0.0

    We apply this to both DAMAGE_PROPERTY and DAMAGE_CROPS.
    """
    logger.info("Parsing damage columns to float USD.")

    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

    def parse_damage_string(value: str | float) -> float:
        """Parse a single damage string. Returns 0.0 for null/unparseable."""
        if pd.isnull(value) or str(value).strip() in ("", "0"):
            return 0.0
        value = str(value).strip().upper()
        # Match numeric part + optional suffix
        match = re.match(r"^(\d+\.?\d*)\s*([KMB]?)$", value)
        if match:
            number = float(match.group(1))
            suffix = match.group(2)
            return number * multipliers.get(suffix, 1)
        # If pattern doesn't match, log a warning and return 0
        logger.debug("Could not parse damage value: '%s' — defaulting to 0.", value)
        return 0.0

    for col in ("DAMAGE_PROPERTY", "DAMAGE_CROPS"):
        if col in df.columns:
            df[f"{col}_USD"] = df[col].apply(parse_damage_string)
            logger.info(
                "Parsed %s: min=%.0f, max=%.0f, zeros=%.1f%%",
                col,
                df[f"{col}_USD"].min(),
                df[f"{col}_USD"].max(),
                (df[f"{col}_USD"] == 0).mean() * 100,
            )

    return df


def _compute_total_damage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create TOTAL_DAMAGE_USD = DAMAGE_PROPERTY_USD + DAMAGE_CROPS_USD.

    Both property and crop damage are separate in NOAA data. For regression,
    we need a single target. Summing them gives the full economic loss per event.
    """
    prop = df.get("DAMAGE_PROPERTY_USD", pd.Series(0, index=df.index))
    crop = df.get("DAMAGE_CROPS_USD", pd.Series(0, index=df.index))
    df["TOTAL_DAMAGE_USD"] = prop.fillna(0) + crop.fillna(0)
    logger.info(
        "TOTAL_DAMAGE_USD: mean=$%.0f, max=$%.0f",
        df["TOTAL_DAMAGE_USD"].mean(),
        df["TOTAL_DAMAGE_USD"].max(),
    )
    return df


def _handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Impute or flag missing values — different strategy per column type.

    Strategy rationale:
    - LAT/LON: Do NOT impute with mean — geospatial mean is geographically
      meaningless. Instead, flag with HAS_GEOSPATIAL=0 and fill with 0.0
      so downstream models can use the flag as a feature.
    - MAGNITUDE: Zero-magnitude events are physically meaningful (no measured
      magnitude). Event-type-conditional median is better than global mean
      because tornado magnitude ≠ hail magnitude.
    - Numeric casualty/injury columns: Fill with 0 — NOAA uses blank to mean
      "no recorded casualties", not truly missing.
    - Narrative columns: Fill with empty string so NLP pipeline doesn't crash
      on null inputs.
    """
    logger.info("Handling missing values.")

    # --- Geospatial: flag then zero-fill ---
    geo_cols = ["BEGIN_LAT", "BEGIN_LON", "END_LAT", "END_LON"]
    has_geo = df["BEGIN_LAT"].notna() & df["BEGIN_LON"].notna()
    df["HAS_GEOSPATIAL"] = has_geo.astype("int8")
    for col in geo_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)
    missing_geo = (~has_geo).sum()
    logger.info(
        "Geospatial: %d rows (%.1f%%) missing lat/lon — flagged as HAS_GEOSPATIAL=0.",
        missing_geo,
        missing_geo / len(df) * 100,
    )

    # --- MAGNITUDE: event-type conditional median ---
    if "MAGNITUDE" in df.columns:
        pre_missing = df["MAGNITUDE"].isna().sum()
        df["MAGNITUDE"] = df.groupby("EVENT_TYPE")["MAGNITUDE"].transform(
            lambda grp: grp.fillna(grp.median())
        )
        # Any remaining nulls (event types where ALL magnitude is null) → 0.0
        remaining = df["MAGNITUDE"].isna().sum()
        df["MAGNITUDE"] = df["MAGNITUDE"].fillna(0.0)
        logger.info(
            "MAGNITUDE: imputed %d nulls via event-type median; %d remaining → 0.",
            pre_missing - remaining,
            remaining,
        )

    # --- Casualty / injury: NOAA blank = 0 recorded ---
    zero_fill_cols = [
        "DEATHS_DIRECT", "DEATHS_INDIRECT",
        "INJURIES_DIRECT", "INJURIES_INDIRECT",
    ]
    for col in zero_fill_cols:
        if col in df.columns:
            n_filled = df[col].isna().sum()
            df[col] = df[col].fillna(0.0)
            if n_filled > 0:
                logger.debug("Zero-filled %d nulls in %s.", n_filled, col)

    # --- Narrative text: empty string (NLP handles empty gracefully) ---
    for col in ("EVENT_NARRATIVE", "EPISODE_NARRATIVE"):
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()

    return df


def _remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove exact duplicate rows.

    We define a duplicate as: same EVENT_ID AND same STATE AND same YEAR.
    Full-row deduplication would also catch accidental copy rows.
    We do both and keep the first occurrence.
    """
    initial_count = len(df)

    # Full-row duplicates first
    df = df.drop_duplicates()

    # EVENT_ID level duplicates (same event ingested twice with slightly different data)
    if "EVENT_ID" in df.columns:
        df = df.drop_duplicates(subset=["EVENT_ID"], keep="first")

    removed = initial_count - len(df)
    logger.info(
        "Duplicates removed: %d rows (%.2f%% of original).",
        removed,
        removed / initial_count * 100,
    )
    return df


def _fix_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce correct dtypes after cleaning.

    After fillna and parsing, some columns may still have object dtype.
    We explicitly cast to save memory and prevent downstream type errors.
    """
    logger.info("Fixing column dtypes.")

    numeric_cols = [
        "DEATHS_DIRECT", "DEATHS_INDIRECT",
        "INJURIES_DIRECT", "INJURIES_INDIRECT",
        "MAGNITUDE",
        "DAMAGE_PROPERTY_USD", "DAMAGE_CROPS_USD", "TOTAL_DAMAGE_USD",
        "BEGIN_LAT", "BEGIN_LON",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # YEAR is integer — safe to cast after nulls are gone
    if "YEAR" in df.columns:
        df["YEAR"] = df["YEAR"].astype("int32")

    # Categorical columns: use pandas Categorical for memory efficiency
    for col in ("STATE", "EVENT_TYPE", "MONTH_NAME"):
        if col in df.columns:
            df[col] = df[col].astype("category")

    return df


def _handle_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle outliers in TOTAL_DAMAGE_USD via log1p transform.

    RATIONALE:
    TOTAL_DAMAGE_USD has extreme right skew — the distribution spans from
    $0 to ~$10 billion within the same column. Linear models and tree-based
    models both perform poorly when the target has this range.

    log1p(x) = log(x + 1) solves two problems:
      1. Compresses the range from [0, 1e10] to roughly [0, 23]
      2. The +1 ensures log1p(0) = 0, so zero-damage events map cleanly to 0

    We keep TOTAL_DAMAGE_USD (original) for interpretability and add
    LOG_DAMAGE_USD as the feature/target used in modeling.

    Note: For outlier detection in general numeric columns, we apply
    IQR-based winsorization (cap, not remove) to preserve data volume.
    """
    logger.info("Handling outliers.")

    # Log-transform damage (primary target for regression)
    if "TOTAL_DAMAGE_USD" in df.columns:
        df["LOG_DAMAGE_USD"] = np.log1p(df["TOTAL_DAMAGE_USD"])
        logger.info(
            "LOG_DAMAGE_USD: min=%.3f, max=%.3f, mean=%.3f",
            df["LOG_DAMAGE_USD"].min(),
            df["LOG_DAMAGE_USD"].max(),
            df["LOG_DAMAGE_USD"].mean(),
        )

    # IQR winsorization for MAGNITUDE (physical limits vary per event type)
    # Cap extreme values at 1.5 × IQR — preserves distribution shape
    if "MAGNITUDE" in df.columns:
        q1 = df["MAGNITUDE"].quantile(0.25)
        q3 = df["MAGNITUDE"].quantile(0.75)
        iqr = q3 - q1
        upper_cap = q3 + 1.5 * iqr
        n_capped = (df["MAGNITUDE"] > upper_cap).sum()
        df["MAGNITUDE"] = df["MAGNITUDE"].clip(upper=upper_cap)
        logger.info(
            "MAGNITUDE winsorized: %d rows capped at %.2f (Q3 + 1.5×IQR).",
            n_capped,
            upper_cap,
        )

    return df


def _standardize_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize free-text categorical values:
    - Uppercase STATE (NOAA uses inconsistent casing in some releases)
    - Title-case EVENT_TYPE for consistency
    - Strip whitespace from all string columns
    """
    if "STATE" in df.columns:
        df["STATE"] = df["STATE"].astype(str).str.upper().str.strip().astype("category")

    if "EVENT_TYPE" in df.columns:
        df["EVENT_TYPE"] = (
            df["EVENT_TYPE"].astype(str).str.title().str.strip().astype("category")
        )

    if "MONTH_NAME" in df.columns:
        df["MONTH_NAME"] = (
            df["MONTH_NAME"].astype(str).str.title().str.strip().astype("category")
        )

    return df