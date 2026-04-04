"""
random_forest.py
----------------
Random Forest classifier for EVENT_TYPE multi-class prediction.
Handles class imbalance via class_weight='balanced'.
Supports save/load/predict interface consistent across all models.
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from src.utils.config import CONFIG
from src.utils.logger import get_logger
from src.utils.exceptions import ModelNotFoundError, PredictionError, InvalidInputError

logger = get_logger(__name__)

# Default save location — overridable via save_model(path=...)
DEFAULT_MODEL_DIR = Path("models/classification")


class DisasterRandomForestClassifier:
    """
    Random Forest wrapper for EVENT_TYPE classification.

    Encapsulates:
      - Model training with class-imbalance handling
      - Label encoding/decoding via saved LabelEncoder
      - Serialization / deserialization
      - Prediction with confidence scores
    """

    def __init__(self, label_encoder_path: str | None = None) -> None:
        cfg = CONFIG["classification"]["random_forest"]
        clf_cfg = CONFIG["classification"]

        self.model = RandomForestClassifier(
            n_estimators=cfg["n_estimators"],
            max_depth=cfg["max_depth"],
            min_samples_split=cfg["min_samples_split"],
            min_samples_leaf=cfg["min_samples_leaf"],
            class_weight="balanced",   # Handles EVENT_TYPE imbalance without SMOTE
            n_jobs=cfg["n_jobs"],
            random_state=clf_cfg["random_state"],
            verbose=0,
        )

        # Load the LabelEncoder fitted during the data pipeline
        le_path = Path(
            label_encoder_path
            or CONFIG["data"]["processed_dir"] + "label_encoder.pkl"
        )
        if not le_path.exists():
            raise ModelNotFoundError(f"LabelEncoder not found at: {le_path}")

        self.label_encoder: LabelEncoder = joblib.load(le_path)
        self.is_trained: bool = False
        logger.info(
            "RandomForestClassifier initialized. %d event type classes loaded.",
            len(self.label_encoder.classes_),
        )

    # ── Training ─────────────────────────────────────────────────────────────

    def fit(self, X_train: np.ndarray | pd.DataFrame, y_train: np.ndarray | pd.Series) -> "DisasterRandomForestClassifier":
        """
        Train the Random Forest on the feature matrix.

        Args:
            X_train: Feature matrix (structured + optionally TF-IDF merged).
                     Shape: (n_samples, n_features)
            y_train: Integer-encoded EVENT_TYPE labels from label_encoder.pkl.

        Returns:
            self (for method chaining)
        """
        logger.info(
            "Training RandomForest: %d samples, %d features, %d classes.",
            len(X_train),
            X_train.shape[1],
            len(np.unique(y_train)),
        )

        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Log top 10 feature importances for interpretability
        if hasattr(X_train, "columns"):
            importances = pd.Series(
                self.model.feature_importances_, index=X_train.columns
            ).sort_values(ascending=False)
            logger.info(
                "Top 10 feature importances:\n%s",
                importances.head(10).to_string(),
            )

        logger.info("RandomForest training complete.")
        return self

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, X: np.ndarray | pd.DataFrame) -> np.ndarray:
        """
        Predict EVENT_TYPE labels (decoded to original string labels).

        Args:
            X: Feature matrix, same shape as training features.

        Returns:
            np.ndarray of EVENT_TYPE strings, e.g. ["Tornado", "Flash Flood", ...]

        Raises:
            PredictionError: If model is not trained or input shape is wrong.
        """
        self._validate_for_inference(X)
        try:
            encoded_preds = self.model.predict(X)
            return self.label_encoder.inverse_transform(encoded_preds)
        except Exception as exc:
            raise PredictionError(f"RandomForest prediction failed: {exc}") from exc

    def predict_proba(self, X: np.ndarray | pd.DataFrame) -> np.ndarray:
        """
        Return class probability scores for all EVENT_TYPE classes.

        Returns:
            np.ndarray of shape (n_samples, n_classes).
            Column order matches self.label_encoder.classes_
        """
        self._validate_for_inference(X)
        try:
            return self.model.predict_proba(X)
        except Exception as exc:
            raise PredictionError(f"predict_proba failed: {exc}") from exc

    def predict_top_n(self, X: np.ndarray | pd.DataFrame, n: int = 3) -> list[list[dict]]:
        """
        Return top-N predicted EVENT_TYPEs with their probabilities per sample.

        Useful for API responses where confidence ranking matters.

        Returns:
            List of lists: [[{"label": "Tornado", "prob": 0.82}, ...], ...]
        """
        probas = self.predict_proba(X)
        results = []
        for row in probas:
            top_idx = np.argsort(row)[::-1][:n]
            results.append([
                {
                    "label": self.label_encoder.classes_[i],
                    "probability": round(float(row[i]), 4),
                }
                for i in top_idx
            ])
        return results

    # ── Serialization ─────────────────────────────────────────────────────────

    def save_model(self, path: str | None = None) -> Path:
        """
        Serialize the trained model to disk using joblib.

        Args:
            path: Full file path. Defaults to models/classification/random_forest.pkl

        Returns:
            Path where the model was saved.

        Raises:
            PredictionError: If model has not been trained yet.
        """
        if not self.is_trained:
            raise PredictionError("Cannot save an untrained model.")

        save_path = Path(path or DEFAULT_MODEL_DIR / "random_forest.pkl")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, save_path, compress=3)
        logger.info("Model saved to: %s (%.2f MB)", save_path, save_path.stat().st_size / 1e6)
        return save_path

    @classmethod
    def load_model(cls, path: str | None = None) -> "DisasterRandomForestClassifier":
        """
        Load a serialized model from disk.

        Args:
            path: Full file path. Defaults to models/classification/random_forest.pkl

        Returns:
            Loaded DisasterRandomForestClassifier instance.

        Raises:
            ModelNotFoundError: If the file does not exist.
        """
        load_path = Path(path or DEFAULT_MODEL_DIR / "random_forest.pkl")
        if not load_path.exists():
            raise ModelNotFoundError(f"RandomForest model not found at: {load_path}")

        instance = joblib.load(load_path)
        logger.info("Model loaded from: %s", load_path)
        return instance

    # ── Internal validation ───────────────────────────────────────────────────

    def _validate_for_inference(self, X) -> None:
        """Raise informative errors before prediction rather than cryptic sklearn errors."""
        if not self.is_trained:
            raise PredictionError(
                "Model has not been trained. Call fit() or load_model() first."
            )
        if hasattr(X, "shape") and len(X.shape) != 2:
            raise InvalidInputError(
                f"Expected 2D input, got shape {X.shape}. "
                "Ensure X is (n_samples, n_features)."
            )