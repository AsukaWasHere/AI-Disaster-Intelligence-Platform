"""
feature_engineering.py
----------------------
Responsibility: Create all derived features from a clean DataFrame.

Groups:
  - Time features (year, month_num, season, decade)
  - Damage features (log_damage, damage_tier)
  - Severity features (total_casualties, severity_index)
  - Geospatial features (geo_cluster, region)
  - Risk score (composite weighted formula)

DESIGN: Every feature group is a separate function.
The master `engineer()` function chains them all.
No function modifies the input in place — always returns a new/modified copy.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler

from src.utils.logger import get_logger
from src.utils.config import CONFIG

logger = get_logger(__name__)

# Season mapping by calendar month (Northern Hemisphere, US context)
MONTH_TO_SEASON: dict[str, str] = {
    "January":   "Winter", "February":  "Winter", "March":     "Spring",
    "April":     "Spring",  "May":        "Spring", "June":      "Summer",
    "July":      "Summer",  "August":     "Summer", "September": "Fall",
    "October":   "Fall",    "November":   "Fall",   "December":  "Winter",
}

# Month name → integer, for use as an ordinal feature
MONTH_TO_NUM: dict[str, int] = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

# US Census region groupings (coarser geography than 50 states)
STATE_TO_REGION: dict[str, str] = {
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


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def engineer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all feature engineering transformations in the correct order.

    Order matters: geo_cluster depends on lat/lon columns being numeric
    (guaranteed after cleaning). Risk score depends on casualties and damage
    features (built in severity and damage steps).

    Args:
        df: Clean DataFrame from data_cleaning.py

    Returns:
        DataFrame with all engineered features appended.
    """
    logger.info("Starting feature engineering. Input shape: %s", df.shape)

    df = _add_time_features(df)
    df = _add_damage_features(df)
    df = _add_severity_features(df)
    df = _add_geo_features(df)
    df = _add_risk_score(df)

    new_cols = [
        "MONTH_NUM", "SEASON", "DECADE", "IS_WEEKEND_ADJACENT",
        "LOG_DAMAGE_USD", "DAMAGE_TIER",
        "TOTAL_CASUALTIES", "SEVERITY_INDEX",
        "GEO_CLUSTER", "REGION",
        "RISK_SCORE",
    ]
    created = [c for c in new_cols if c in df.columns]
    logger.info(
        "Feature engineering complete. %d new features created. Output shape: %s",
        len(created),
        df.shape,
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Feature group functions
# ─────────────────────────────────────────────────────────────────────────────

def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create time-based features from YEAR and MONTH_NAME.

    Features:
      MONTH_NUM:           Ordinal month (1–12). Preserves temporal order
                           better than one-hot for most tree models.
      SEASON:              Winter/Spring/Summer/Fall. Captures seasonal
                           disaster patterns (tornado season = Spring, etc.)
      DECADE:              10-year bucketing. Captures long-term climate trend
                           signal without overfitting to specific years.
      IS_HIGH_SEASON:      Binary. Marks Mar–Oct (peak disaster months in US).
                           Useful for imbalanced event types.

    Why not use raw YEAR as a feature? YEAR has too many unique values and
    models tend to memorize year-specific patterns rather than generalizing.
    DECADE balances temporal signal with generalization.
    """
    logger.info("Adding time features.")

    # Month → numeric
    df["MONTH_NUM"] = (
        df["MONTH_NAME"].astype(str).map(MONTH_TO_NUM).fillna(0).astype("int8")
    )

    # Month → season string → then encode as integer in pipeline
    df["SEASON"] = df["MONTH_NAME"].astype(str).map(MONTH_TO_SEASON).fillna("Unknown")

    # Decade bucketing (e.g. 1995 → 1990, 2012 → 2010)
    df["DECADE"] = (df["YEAR"] // 10 * 10).astype("int32")

    # High season flag: March through October inclusive
    df["IS_HIGH_SEASON"] = df["MONTH_NUM"].between(3, 10).astype("int8")

    return df


def _add_damage_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create damage-related features.

    Features:
      LOG_DAMAGE_USD:  Already created in cleaning step — carried forward.
                       log1p compresses the extreme right tail of damage values.
      DAMAGE_TIER:     Ordinal category (0=No damage → 4=Catastrophic).
                       Gives models a categorical handle on damage severity
                       instead of requiring them to learn raw dollar thresholds.

    Damage tier thresholds based on FEMA/insurance industry conventions:
      0 = $0 (no recorded damage)
      1 = $1–$10,000 (minor)
      2 = $10,001–$1,000,000 (moderate)
      3 = $1,000,001–$100,000,000 (major)
      4 = >$100,000,000 (catastrophic)
    """
    logger.info("Adding damage features.")

    # LOG_DAMAGE_USD created in cleaner; re-create here if missing (defensive)
    if "LOG_DAMAGE_USD" not in df.columns:
        df["LOG_DAMAGE_USD"] = np.log1p(df["TOTAL_DAMAGE_USD"].fillna(0))

    # Damage tier: ordinal encoding of dollar magnitude
    conditions = [
        df["TOTAL_DAMAGE_USD"] == 0,
        df["TOTAL_DAMAGE_USD"].between(1, 10_000),
        df["TOTAL_DAMAGE_USD"].between(10_001, 1_000_000),
        df["TOTAL_DAMAGE_USD"].between(1_000_001, 100_000_000),
        df["TOTAL_DAMAGE_USD"] > 100_000_000,
    ]
    choices = [0, 1, 2, 3, 4]
    df["DAMAGE_TIER"] = np.select(conditions, choices, default=0).astype("int8")

    return df


def _add_severity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create human-impact severity features.

    Features:
      TOTAL_CASUALTIES:  Deaths + injuries (all types). Single number capturing
                         human impact. Direct + Indirect combined because the
                         distinction is often inconsistently recorded.
      SEVERITY_INDEX:    Weighted composite of deaths (weight 2×) + injuries (1×)
                         + log-damage (0.5×). Deaths are weighted double because
                         loss of life is categorically more severe than injury.
                         The formula is normalized to [0, 100] for interpretability.

    Why not just use raw death count?
    Death count alone has too many zeros — most events cause no fatalities.
    The composite gives models a richer gradient to work with.
    """
    logger.info("Adding severity features.")

    deaths = (
        df.get("DEATHS_DIRECT", pd.Series(0, index=df.index)).fillna(0)
        + df.get("DEATHS_INDIRECT", pd.Series(0, index=df.index)).fillna(0)
    )
    injuries = (
        df.get("INJURIES_DIRECT", pd.Series(0, index=df.index)).fillna(0)
        + df.get("INJURIES_INDIRECT", pd.Series(0, index=df.index)).fillna(0)
    )
    log_dmg = df.get("LOG_DAMAGE_USD", pd.Series(0, index=df.index)).fillna(0)

    df["TOTAL_CASUALTIES"] = (deaths + injuries).astype("float32")

    # Weighted composite — raw score before normalization
    raw_severity = (2.0 * deaths) + (1.0 * injuries) + (0.5 * log_dmg)

    # Normalize to 0–100 using min-max scaling
    severity_min = raw_severity.min()
    severity_max = raw_severity.max()
    if severity_max > severity_min:
        df["SEVERITY_INDEX"] = (
            (raw_severity - severity_min) / (severity_max - severity_min) * 100
        ).astype("float32")
    else:
        df["SEVERITY_INDEX"] = 0.0

    logger.info(
        "SEVERITY_INDEX: mean=%.2f, max=%.2f",
        df["SEVERITY_INDEX"].mean(),
        df["SEVERITY_INDEX"].max(),
    )
    return df


def _add_geo_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create geospatial features.

    Features:
      GEO_CLUSTER:  KMeans cluster label (0–N) for events with valid lat/lon.
                    Groups geographically similar events — useful for
                    discovering regional disaster patterns the model can
                    leverage without knowing US geography explicitly.
                    Events missing lat/lon are assigned cluster -1.
      REGION:       US Census region (Northeast/South/Midwest/West).
                    Coarser but more interpretable than 50 state dummies.
                    Encodes as ordinal integer for models.

    KMeans cluster count (k=10 default) is tuned via elbow method in
    notebooks/geo_clustering_eda.ipynb. Set in config.yaml.

    Why KMeans on geo coordinates? It creates spatial features that capture
    "events in the Gulf Coast cluster" vs "Great Plains cluster" without
    the model needing to learn this from raw lat/lon directly.
    """
    logger.info("Adding geospatial features.")

    # --- Region encoding ---
    df["REGION"] = (
        df["STATE"].astype(str).str.upper().map(STATE_TO_REGION).fillna("Unknown")
    )

    # --- KMeans geo clustering (only on valid lat/lon rows) ---
    geo_mask = df["HAS_GEOSPATIAL"].astype(bool) if "HAS_GEOSPATIAL" in df.columns \
               else df["BEGIN_LAT"].ne(0) & df["BEGIN_LON"].ne(0)

    df["GEO_CLUSTER"] = -1  # Default: no cluster for missing geo

    if geo_mask.sum() > 0:
        geo_df = df.loc[geo_mask, ["BEGIN_LAT", "BEGIN_LON"]].copy()
        n_clusters = CONFIG.get("features", {}).get("n_geo_clusters", 10)

        # Cap clusters to avoid k > n_samples
        n_clusters = min(n_clusters, len(geo_df))

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init="auto",
        )
        cluster_labels = kmeans.fit_predict(geo_df[["BEGIN_LAT", "BEGIN_LON"]])
        df.loc[geo_mask, "GEO_CLUSTER"] = cluster_labels.astype("int8")

        logger.info(
            "KMeans geo clustering: k=%d, clustered %d/%d rows.",
            n_clusters,
            geo_mask.sum(),
            len(df),
        )
    else:
        logger.warning("No valid geospatial data — GEO_CLUSTER set to -1 for all rows.")

    return df


def _add_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a composite RISK_SCORE (0–100) per event.

    Formula:
      RISK_SCORE = 100 × (
          w_damage   × norm(LOG_DAMAGE_USD)
        + w_deaths   × norm(TOTAL_DEATHS)
        + w_injuries × norm(TOTAL_INJURIES)
        + w_mag      × norm(MAGNITUDE)
      )

    Weights from config.yaml risk_score.weights.
    All components are MinMax-normalized independently so no single
    component dominates due to scale differences.

    This score is:
      - A feature for classification models (high-risk events may cluster by type)
      - A standalone API output for risk dashboards
      - An input to the geospatial heatmap
    """
    logger.info("Computing composite risk score.")

    weights = CONFIG.get("risk_score", {}).get("weights", {
        "damage": 0.40, "deaths": 0.35, "injuries": 0.15, "magnitude": 0.10
    })

    deaths_total = (
        df.get("DEATHS_DIRECT", 0) + df.get("DEATHS_INDIRECT", 0)
    ).fillna(0)
    injuries_total = (
        df.get("INJURIES_DIRECT", 0) + df.get("INJURIES_INDIRECT", 0)
    ).fillna(0)

    components = pd.DataFrame({
        "damage":    df.get("LOG_DAMAGE_USD", pd.Series(0, index=df.index)).fillna(0),
        "deaths":    deaths_total,
        "injuries":  injuries_total,
        "magnitude": df.get("MAGNITUDE", pd.Series(0, index=df.index)).fillna(0),
    })

    scaler = MinMaxScaler()
    normalized = pd.DataFrame(
        scaler.fit_transform(components),
        columns=components.columns,
        index=df.index,
    )

    df["RISK_SCORE"] = (
        weights["damage"]    * normalized["damage"]
        + weights["deaths"]   * normalized["deaths"]
        + weights["injuries"] * normalized["injuries"]
        + weights["magnitude"] * normalized["magnitude"]
    ) * 100

    df["RISK_SCORE"] = df["RISK_SCORE"].astype("float32")

    logger.info(
        "RISK_SCORE: mean=%.2f, p50=%.2f, p95=%.2f, max=%.2f",
        df["RISK_SCORE"].mean(),
        df["RISK_SCORE"].quantile(0.50),
        df["RISK_SCORE"].quantile(0.95),
        df["RISK_SCORE"].max(),
    )
    return df