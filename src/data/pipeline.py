"""
pipeline.py
-----------
Responsibility: Orchestrate the full data pipeline end-to-end.

Execution order:
  1. Load raw data            (data_loader.py)
  2. Clean data               (data_cleaning.py)
  3. Engineer features        (feature_engineering.py)
  4. Process NLP              (nlp_processing.py)
  5. Define targets           (classification + regression)
  6. Train/test split         (stratified for classification)
  7. Save all outputs         (data/processed/)

This file contains NO business logic — it only coordinates.
All parameters come from config.yaml.
Run directly: python -m src.data.pipeline
"""
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from src.data.data_loader import load_raw_data
from src.data.data_cleaning import clean
from src.features.feature_engineering import engineer
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
from src.utils.logger import get_logger
from src.utils.config import CONFIG
from src.utils.exceptions import DataLoadError, FeatureEngineeringError

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Column definitions (defined centrally — no magic strings scattered in code)
# ─────────────────────────────────────────────────────────────────────────────

# Features used in structured ML models (classification + regression)
STRUCTURED_FEATURE_COLS: list[str] = [
    # Time
    "YEAR", "MONTH_NUM", "IS_HIGH_SEASON", "DECADE",
    # Damage
    "LOG_DAMAGE_USD", "DAMAGE_TIER",
    # Severity
    "TOTAL_CASUALTIES", "SEVERITY_INDEX",
    # Physical
    "MAGNITUDE",
    # Geospatial
    "GEO_CLUSTER", "HAS_GEOSPATIAL",
    # Text-derived (structural)
    "NARRATIVE_LENGTH",
    # Risk
    "RISK_SCORE",
]

# Categorical columns needing encoding before model training
CATEGORICAL_FEATURE_COLS: list[str] = [
    "STATE", "SEASON", "REGION",
]

# Classification target
CLASSIFICATION_TARGET: str = "EVENT_TYPE"

# Regression target (log-transformed)
REGRESSION_TARGET: str = "LOG_DAMAGE_USD"

# ─────────────────────────────────────────────────────────────────────────────
# NLP HELPERS (TRAIN-TIME ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def process_narratives(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine and clean narrative columns into one text field.
    """
    cols = CONFIG["data"]["narrative_columns"]

    df["COMBINED_NARRATIVE"] = (
        df[cols]
        .fillna("")
        .agg(" ".join, axis=1)
        .str.lower()
    )

    # simple feature
    df["NARRATIVE_LENGTH"] = df["COMBINED_NARRATIVE"].str.len()

    return df


def build_tfidf_matrix(text_series, max_features=500):
    """
    Fit TF-IDF on full dataset (train-time only).
    """
    vectorizer = TfidfVectorizer(max_features=max_features)

    X_tfidf = vectorizer.fit_transform(text_series)

    logger.info("TF-IDF built: shape=%s", X_tfidf.shape)

    return X_tfidf, vectorizer

# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline() -> None:
    """
    Execute the full data pipeline.

    Saves to data/processed/:
      - noaa_processed.parquet        Full processed DataFrame
      - X_train.parquet               Structured features, train split
      - X_test.parquet                Structured features, test split
      - y_clf_train.parquet           Classification target, train
      - y_clf_test.parquet            Classification target, test
      - y_reg_train.parquet           Regression target, train
      - y_reg_test.parquet            Regression target, test
      - tfidf_train.npz               Sparse TF-IDF matrix, train rows
      - tfidf_test.npz                Sparse TF-IDF matrix, test rows
      - label_encoder.pkl             Fitted LabelEncoder for EVENT_TYPE
      - tfidf_vectorizer.pkl          Fitted TfidfVectorizer

    Raises:
        DataLoadError: If raw data cannot be loaded.
        FeatureEngineeringError: If a feature step fails.
    """
    logger.info("=" * 60)
    logger.info("PIPELINE START")
    logger.info("=" * 60)

    processed_dir = Path(CONFIG["data"]["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Load ──────────────────────────────────────────────────────────
    logger.info("[1/7] Loading raw data...")
    df = load_raw_data()
    logger.info("Raw data loaded: %s rows.", f"{len(df):,}")

    # ── Step 2: Clean ─────────────────────────────────────────────────────────
    logger.info("[2/7] Cleaning data...")
    df = clean(df)
    logger.info("Cleaning complete: %s rows remain.", f"{len(df):,}")

    # ── Step 3: Feature engineering ───────────────────────────────────────────
    logger.info("[3/7] Engineering features...")
    df = engineer(df)
    logger.info("Feature engineering complete. Shape: %s", df.shape)

    # ── Step 4: NLP processing ────────────────────────────────────────────────
    logger.info("[4/7] Processing narratives (NLP)...")
    df = process_narratives(df)
    logger.info("NLP processing complete.")

    # ── Step 5: Define targets + feature matrix ───────────────────────────────
    logger.info("[5/7] Preparing feature matrix and targets...")
    df, label_encoder = _encode_targets(df)
    X = _build_feature_matrix(df)
    y_clf = df[CLASSIFICATION_TARGET + "_ENCODED"]
    y_reg = df[REGRESSION_TARGET]

    # ── Step 6: Train/test split ──────────────────────────────────────────────
    logger.info("[6/7] Splitting train/test...")
    (
        X_train, X_test,
        y_clf_train, y_clf_test,
        y_reg_train, y_reg_test,
        idx_train, idx_test,
    ) = _split_data(X, y_clf, y_reg)

    # TF-IDF split must align with same row indices
    tfidf_matrix, tfidf_vectorizer = build_tfidf_matrix(
        df["COMBINED_NARRATIVE"],
        max_features=CONFIG.get("nlp", {}).get("tfidf_max_features", 500),
    )
    tfidf_train = tfidf_matrix[idx_train]
    tfidf_test = tfidf_matrix[idx_test]

    # ── Step 7: Save all outputs ──────────────────────────────────────────────
    logger.info("[7/7] Saving processed outputs...")
    _save_outputs(
        processed_dir=processed_dir,
        df=df,
        X_train=X_train,
        X_test=X_test,
        y_clf_train=y_clf_train,
        y_clf_test=y_clf_test,
        y_reg_train=y_reg_train,
        y_reg_test=y_reg_test,
        tfidf_train=tfidf_train,
        tfidf_test=tfidf_test,
        label_encoder=label_encoder,
        tfidf_vectorizer=tfidf_vectorizer,
    )

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE. All outputs saved to: %s", processed_dir)
    logger.info("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _encode_targets(df: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    le = LabelEncoder()

    # Drop null targets
    df = df.dropna(subset=[CLASSIFICATION_TARGET])

    # 🔥 REMOVE RARE CLASSES (IMPORTANT FIX)
    counts = df[CLASSIFICATION_TARGET].value_counts()
    valid_classes = counts[counts >= 2].index

    df = df[df[CLASSIFICATION_TARGET].isin(valid_classes)]

    logger.info(
        "Removed rare classes (<2 samples). Remaining classes: %d",
        len(valid_classes),
    )

    # Encode
    df[CLASSIFICATION_TARGET + "_ENCODED"] = le.fit_transform(
        df[CLASSIFICATION_TARGET].astype(str)
    )

    logger.info("LabelEncoder fitted: %d classes.", len(le.classes_))

    return df, le


def _build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assemble the final feature matrix for ML models.

    Structured numeric features + one-hot encoded categoricals.
    TF-IDF features are handled separately (sparse matrix).

    One-hot encoding for STATE, SEASON, REGION is done here rather
    than in feature_engineering.py because encoding requires knowing
    the full vocabulary (all states/seasons), which is only guaranteed
    once you have the complete dataset. Doing it before splitting
    prevents unseen-category errors at inference.
    """
    # Start with numeric structured features (only columns that exist)
    available_structured = [c for c in STRUCTURED_FEATURE_COLS if c in df.columns]
    X = df[available_structured].copy()

    # One-hot encode categorical features
    for col in CATEGORICAL_FEATURE_COLS:
        if col not in df.columns:
            logger.warning("Categorical column %s not found — skipping.", col)
            continue
        dummies = pd.get_dummies(
            df[col].astype(str),
            prefix=col,
            drop_first=False,   # Keep all dummies; drop_first can mask rare categories
            dtype="int8",
        )
        X = pd.concat([X, dummies], axis=1)
        logger.info("One-hot encoded %s: %d new columns.", col, len(dummies.columns))

    # Ensure all numeric — replace any remaining NaN with 0
    X = X.fillna(0)

    logger.info("Feature matrix shape: %s", X.shape)
    return X


def _split_data(
    X: pd.DataFrame,
    y_clf: pd.Series,
    y_reg: pd.Series,
) -> tuple:
    """
    Stratified train/test split for classification.
    The same split indices are applied to the regression target and TF-IDF.

    Stratification on y_clf ensures each class appears in both train and test
    in proportion to its frequency — critical for rare disaster types.

    Returns indices as well as data splits so TF-IDF (sparse matrix)
    can be aligned without converting to dense.
    """
    cfg = CONFIG["classification"]
    test_size = cfg["test_size"]
    random_state = cfg["random_state"]

    # Generate index arrays for stratified split
    all_indices = np.arange(len(X))

    train_idx, test_idx = train_test_split(
        all_indices,
        test_size=test_size,
        random_state=random_state,
        stratify=y_clf,         # Preserve class distribution
    )

    X_train = X.iloc[train_idx].reset_index(drop=True)
    X_test  = X.iloc[test_idx].reset_index(drop=True)
    y_clf_train = y_clf.iloc[train_idx].reset_index(drop=True)
    y_clf_test  = y_clf.iloc[test_idx].reset_index(drop=True)
    y_reg_train = y_reg.iloc[train_idx].reset_index(drop=True)
    y_reg_test  = y_reg.iloc[test_idx].reset_index(drop=True)

    logger.info(
        "Train/test split: %d train rows, %d test rows (%.0f/%0.f split).",
        len(X_train),
        len(X_test),
        (1 - test_size) * 100,
        test_size * 100,
    )

    return (
        X_train, X_test,
        y_clf_train, y_clf_test,
        y_reg_train, y_reg_test,
        train_idx, test_idx,
    )


def _save_outputs(
    processed_dir: Path,
    df: pd.DataFrame,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_clf_train: pd.Series,
    y_clf_test: pd.Series,
    y_reg_train: pd.Series,
    y_reg_test: pd.Series,
    tfidf_train,
    tfidf_test,
    label_encoder: LabelEncoder,
    tfidf_vectorizer,
) -> None:
    """Save all pipeline outputs to data/processed/."""
    from scipy.sparse import save_npz

    # Full processed DataFrame (Parquet is faster + smaller than CSV for wide DataFrames)
    full_path = processed_dir / "noaa_processed.parquet"
    df.to_parquet(full_path, index=False)
    logger.info("Saved full processed data: %s (%.1f MB)", full_path, full_path.stat().st_size / 1e6)

    # Feature matrices
    X_train.to_parquet(processed_dir / "X_train.parquet", index=False)
    X_test.to_parquet(processed_dir / "X_test.parquet", index=False)

    # Targets
    y_clf_train.to_frame("EVENT_TYPE_ENCODED").to_parquet(processed_dir / "y_clf_train.parquet", index=False)
    y_clf_test.to_frame("EVENT_TYPE_ENCODED").to_parquet(processed_dir / "y_clf_test.parquet", index=False)
    y_reg_train.to_frame("LOG_DAMAGE_USD").to_parquet(processed_dir / "y_reg_train.parquet", index=False)
    y_reg_test.to_frame("LOG_DAMAGE_USD").to_parquet(processed_dir / "y_reg_test.parquet", index=False)

    # TF-IDF sparse matrices
    save_npz(str(processed_dir / "tfidf_train.npz"), tfidf_train)
    save_npz(str(processed_dir / "tfidf_test.npz"), tfidf_test)

    # Fitted transformers (needed at inference time)
    joblib.dump(label_encoder, processed_dir / "label_encoder.pkl")
    joblib.dump(tfidf_vectorizer, processed_dir / "tfidf_vectorizer.pkl")

    # Feature column names (needed for inference feature alignment)
    import json
    feature_cols_path = processed_dir / "feature_columns.json"
    feature_cols = {
        "structured": X_train.columns.tolist(),  # All columns after one-hot encoding
        "tfidf_features": CONFIG.get("nlp", {}).get("tfidf_max_features", 500),
    }
    with open(feature_cols_path, "w") as f:
        json.dump(feature_cols, f, indent=2)
    logger.info("Saved feature columns to: %s", feature_cols_path)

    logger.info("All outputs saved to: %s", processed_dir)
    _log_output_summary(processed_dir)


def _log_output_summary(processed_dir: Path) -> None:
    """Log file sizes for all saved outputs."""
    logger.info("─── Output file summary ───────────────────")
    for f in sorted(processed_dir.iterdir()):
        size_mb = f.stat().st_size / 1e6
        logger.info("  %-35s  %.2f MB", f.name, size_mb)
    logger.info("───────────────────────────────────────────")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_pipeline()