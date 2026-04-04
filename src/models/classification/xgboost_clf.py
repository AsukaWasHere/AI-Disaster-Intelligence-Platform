"""
xgboost_clf.py
--------------
XGBoost classifier for EVENT_TYPE multi-class prediction.
Uses scale_pos_weight equivalent via sample_weight for imbalance handling.
Supports early stopping on a validation set to prevent overfitting.
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from src.utils.config import CONFIG
from src.utils.logger import get_logger
from src.utils.exceptions import ModelNotFoundError, PredictionError, InvalidInputError

logger = get_logger(__name__)

DEFAULT_MODEL_DIR = Path("models/classification")


class DisasterXGBoostClassifier:
    """
    XGBoost multi-class classifier for EVENT_TYPE.

    Key differences from RandomForest:
      - Supports early stopping (pass eval_set to fit)
      - Gradient boosting generally outperforms RF on tabular data
      - Uses sample_weight to handle class imbalance (equivalent to class_weight='balanced')
    """

    def __init__(self, label_encoder_path: str | None = None) -> None:
        cfg = CONFIG["classification"]["xgboost"]
        clf_cfg = CONFIG["classification"]

        self.model = XGBClassifier(
            n_estimators=cfg["n_estimators"],
            max_depth=cfg["max_depth"],
            learning_rate=cfg["learning_rate"],
            subsample=cfg["subsample"],
            colsample_bytree=cfg["colsample_bytree"],
            eval_metric="mlogloss",          # Multi-class log loss
            use_label_encoder=False,
            n_jobs=cfg["n_jobs"],
            random_state=clf_cfg["random_state"],
            verbosity=0,
        )

        # Load LabelEncoder from data pipeline
        le_path = Path(
            label_encoder_path
            or CONFIG["data"]["processed_dir"] + "label_encoder.pkl"
        )
        if not le_path.exists():
            raise ModelNotFoundError(f"LabelEncoder not found at: {le_path}")

        self.label_encoder: LabelEncoder = joblib.load(le_path)
        self.is_trained: bool = False
        self._n_classes: int = len(self.label_encoder.classes_)
        logger.info(
            "XGBoostClassifier initialized. %d event type classes.",
            self._n_classes,
        )

    # ── Training ─────────────────────────────────────────────────────────────

    def fit(
        self,
        X_train: np.ndarray | pd.DataFrame,
        y_train: np.ndarray | pd.Series,
        use_early_stopping: bool = True,
        early_stopping_rounds: int = 50,
    ) -> "DisasterXGBoostClassifier":
        """
        Train XGBoost classifier with optional early stopping.

        Class imbalance is handled by computing per-sample weights inversely
        proportional to class frequency — equivalent to class_weight='balanced'
        in sklearn, but applied as sample_weight in XGBoost.

        Args:
            X_train: Feature matrix.
            y_train: Integer-encoded EVENT_TYPE labels.
            use_early_stopping: If True, splits off 10% of train for validation
                                 and stops training when val loss stops improving.
            early_stopping_rounds: How many rounds to wait before stopping.

        Returns:
            self
        """
        logger.info(
            "Training XGBoost classifier: %d samples, %d features.",
            len(X_train),
            X_train.shape[1],
        )

        # Compute sample weights to address class imbalance
        sample_weights = self._compute_sample_weights(y_train)

        if use_early_stopping:
            # Hold out 10% as internal validation set for early stopping
            X_tr, X_val, y_tr, y_val, w_tr, _ = train_test_split(
                X_train,
                y_train,
                sample_weights,
                test_size=0.10,
                random_state=CONFIG["classification"]["random_state"],
                stratify=y_train,
            )
            self.model.fit(
                X_tr,
                y_tr,
                sample_weight=w_tr,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=early_stopping_rounds,
                verbose=False,
            )
            logger.info(
                "Early stopping: best iteration = %d",
                self.model.best_iteration,
            )
        else:
            self.model.fit(X_train, y_train, sample_weight=sample_weights)

        self.is_trained = True
        logger.info("XGBoost training complete.")
        return self

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, X: np.ndarray | pd.DataFrame) -> np.ndarray:
        """
        Predict EVENT_TYPE labels as decoded strings.

        Returns:
            np.ndarray of EVENT_TYPE strings.
        """
        self._validate_for_inference(X)
        try:
            encoded = self.model.predict(X)
            return self.label_encoder.inverse_transform(encoded.astype(int))
        except Exception as exc:
            raise PredictionError(f"XGBoost prediction failed: {exc}") from exc

    def predict_proba(self, X: np.ndarray | pd.DataFrame) -> np.ndarray:
        """Return class probabilities. Shape: (n_samples, n_classes)."""
        self._validate_for_inference(X)
        try:
            return self.model.predict_proba(X)
        except Exception as exc:
            raise PredictionError(f"predict_proba failed: {exc}") from exc

    def predict_top_n(self, X: np.ndarray | pd.DataFrame, n: int = 3) -> list[list[dict]]:
        """Return top-N predictions with probabilities per sample."""
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
        """Save the trained model to disk."""
        if not self.is_trained:
            raise PredictionError("Cannot save an untrained model.")

        save_path = Path(path or DEFAULT_MODEL_DIR / "xgboost_clf.pkl")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, save_path, compress=3)
        logger.info("XGBoost model saved: %s", save_path)
        return save_path

    @classmethod
    def load_model(cls, path: str | None = None) -> "DisasterXGBoostClassifier":
        """Load a serialized XGBoost classifier from disk."""
        load_path = Path(path or DEFAULT_MODEL_DIR / "xgboost_clf.pkl")
        if not load_path.exists():
            raise ModelNotFoundError(f"XGBoost classifier not found at: {load_path}")
        instance = joblib.load(load_path)
        logger.info("XGBoost classifier loaded from: %s", load_path)
        return instance

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _compute_sample_weights(self, y: np.ndarray | pd.Series) -> np.ndarray:
        """
        Compute per-sample weights inversely proportional to class frequency.

        Formula: weight[i] = n_samples / (n_classes * count[class_of_sample_i])
        This is identical to sklearn's class_weight='balanced'.
        """
        y_arr = np.asarray(y)
        classes, counts = np.unique(y_arr, return_counts=True)
        n_samples = len(y_arr)
        n_classes = len(classes)

        # Map class → weight
        weight_map = {
            cls: n_samples / (n_classes * cnt)
            for cls, cnt in zip(classes, counts)
        }
        weights = np.array([weight_map[label] for label in y_arr])
        logger.debug(
            "Sample weights: min=%.3f, max=%.3f, mean=%.3f",
            weights.min(), weights.max(), weights.mean(),
        )
        return weights

    def _validate_for_inference(self, X) -> None:
        if not self.is_trained:
            raise PredictionError("Model not trained. Call fit() or load_model().")
        if hasattr(X, "shape") and len(X.shape) != 2:
            raise InvalidInputError(f"Expected 2D input, got shape {X.shape}.")