"""
data_loader.py
--------------
Responsibility: Load raw NOAA storm events data from disk into a typed DataFrame.
No cleaning, no feature engineering — raw ingestion only.
"""

import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger
from src.utils.config import CONFIG
from src.utils.exceptions import DataLoadError

logger = get_logger(__name__)

# Explicit dtype map prevents pandas from guessing wrong types
# (e.g. EVENT_ID read as float when it should be str, or STATE as category)
COLUMN_DTYPES: dict[str, str] = {
    "EVENT_ID":           "str",
    "EPISODE_ID":         "str",
    "YEAR":               "int32",
    "MONTH_NAME":         "str",
    "STATE":              "str",
    "EVENT_TYPE":         "str",
    "DEATHS_DIRECT":      "float32",
    "DEATHS_INDIRECT":    "float32",
    "INJURIES_DIRECT":    "float32",
    "INJURIES_INDIRECT":  "float32",
    "DAMAGE_PROPERTY":    "str",   # Raw: "1.5K", "2M" — parsed in cleaner
    "DAMAGE_CROPS":       "str",
    "MAGNITUDE":          "float32",
    "MAGNITUDE_TYPE":     "str",
    "BEGIN_LAT":          "float32",
    "BEGIN_LON":          "float32",
    "END_LAT":            "float32",
    "END_LON":            "float32",
    "EVENT_NARRATIVE":    "str",
    "EPISODE_NARRATIVE":  "str",
}


def load_raw_data(filepath: str | None = None) -> pd.DataFrame:
    """
    Load the raw NOAA storm events CSV into a DataFrame.

    Args:
        filepath: Optional override path. Defaults to config value.

    Returns:
        pd.DataFrame with raw data, dtypes partially enforced.

    Raises:
        DataLoadError: If file does not exist or cannot be parsed.
    """
    path = Path(filepath or CONFIG["data"]["raw_dir"]) / CONFIG["data"]["raw_filename"]

    if not path.exists():
        raise DataLoadError(f"Raw data file not found: {path}")

    logger.info("Loading raw data from: %s", path)

    try:
        # Use only the dtype columns that exist in this dataset version
        # (protects against schema drift between NOAA dataset releases)
        df = pd.read_csv(
            path,
            dtype={k: v for k, v in COLUMN_DTYPES.items()},
            low_memory=False,
            na_values=["", "NA", "N/A", "NULL", "None", "UNKNOWN"],
        )
    except Exception as exc:
        raise DataLoadError(f"Failed to parse CSV at {path}: {exc}") from exc

    logger.info(
        "Loaded %d rows × %d columns from raw data.",
        len(df),
        len(df.columns),
    )
    _log_missing_summary(df)

    return df


def _log_missing_summary(df: pd.DataFrame) -> None:
    """Log columns with >5% missingness as an early warning."""
    missing_pct = (df.isnull().sum() / len(df) * 100).sort_values(ascending=False)
    high_missing = missing_pct[missing_pct > 5]

    if high_missing.empty:
        logger.info("No columns with >5%% missing values.")
    else:
        logger.warning(
            "Columns with >5%% missing values:\n%s",
            high_missing.to_string(),
        )