"""
linear.py
---------
Ridge regression baseline for TOTAL_DAMAGE_USD.
Trains on LOG_DAMAGE_USD (log1p transformed target).
Predictions are inverse-transformed (expm1) back to dollar scale.
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from src.utils.config import CONFIG
from src.utils.logger import get_logger
from src.utils.exceptions import ModelNotFoundError, PredictionError, InvalidInputError

logger = get_logger(__name__)

DEFAULT_MODEL_DIR = Path("models/regression")


class DisasterLinearRegressor:
    """
    Ridge regression wrapper for disaster damage prediction.

    Training target: LOG_DAMAGE_USD = log1p(TOTAL_DAMAGE_USD)
    Prediction output: TOTAL_DAMAGE_USD = expm1(model_output)

    The sklearn Pipeline internally chains StandardScaler → Ridge so
    the scaler is always applied consistently at inference.
    """

    def __init__(self) -> None:
        reg_cfg = CONFIG["regression"]["linear"]

        # Pipeline: scale features → ridge regression
        # StandardScaler is important for Ridge because regularization
        # is scale-sensitive — unscaled features with large ranges
        # (e.g., LAT/LON vs MAGNITUDE) dominate the penalty term.
        self.pipeline = Pipeline([
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("ridge", Ridge(
                alpha=1.0,                     # L2 regularization strength
                fit_intercept=reg_cfg["fit_intercept"],
            )),
        ])
        self.is_trained: bool = False
        logger.info("LinearRegressor (Ridge) initialized.")

    # ── Training ─────────────────────────────────────────────────────────────

    def fit(
        self,
        X_train: np.ndarray | pd.DataFrame,
        y_train: np.ndarray | pd.Series,
    ) -> "DisasterLinearRegressor":
        """
        Train on log-transformed damage values.

        Args:
            X_train: Feature matrix.
            y_train: LOG_DAMAGE_USD = log1p(TOTAL_DAMAGE_USD).
                     Must be the log-scale target, NOT raw dollars.

        Returns:
            self
        """
        logger.info(
            "Training Ridge regressor: %d samples, %d features.",
            len(X_train),
            X_train.shape[1],
        )
        logger.info(
            "Target (log scale): min=%.3f, max=%.3f, mean=%.3f",
            float(np.min(y_train)),
            float(np.max(y_train)),
            float(np.mean(y_train)),
        )

        self.pipeline.fit(X_train, y_train)
        self.is_trained = True

        # Log Ridge coefficients statistics
        coefs = self.pipeline.named_steps["ridge"].coef_
        logger.info(
            "Ridge coefficients: %d features, abs_mean=%.4f, abs_max=%.4f",
            len(coefs),
            np.abs(coefs).mean(),
            np.abs(coefs).max(),
        )
        logger.info("Ridge training complete.")
        return self

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(
        self,
        X: np.ndarray | pd.DataFrame,
        return_log_scale: bool = False,
    ) -> np.ndarray:
        """
        Predict total damage in USD.

        Args:
            X: Feature matrix.
            return_log_scale: If True, returns raw log-scale predictions
                              instead of dollar values. Use for RMSE computation.

        Returns:
            np.ndarray of damage predictions.
              - If return_log_scale=False: dollar amounts via expm1(log_pred)
              - If return_log_scale=True:  raw log predictions
        """
        self._validate_for_inference(X)
        try:
            log_preds = self.pipeline.predict(X)
            if return_log_scale:
                return log_preds
            # expm1 is the exact inverse of log1p — more numerically stable than exp(x) - 1
            return np.expm1(log_preds).clip(min=0)   # Clip negatives (numerical artifact)
        except Exception as exc:
            raise PredictionError(f"Linear regression prediction failed: {exc}") from exc

    # ── Serialization ─────────────────────────────────────────────────────────

    def save_model(self, path: str | None = None) -> Path:
        if not self.is_trained:
            raise PredictionError("Cannot save an untrained model.")
        save_path = Path(path or DEFAULT_MODEL_DIR / "linear_regressor.pkl")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, save_path, compress=3)
        logger.info("Linear model saved: %s", save_path)
        return save_path

    @classmethod
    def load_model(cls, path: str | None = None) -> "DisasterLinearRegressor":
        load_path = Path(path or DEFAULT_MODEL_DIR / "linear_regressor.pkl")
        if not load_path.exists():
            raise ModelNotFoundError(f"Linear model not found at: {load_path}")
        instance = joblib.load(load_path)
        logger.info("Linear model loaded from: %s", load_path)
        return instance

    def _validate_for_inference(self, X) -> None:
        if not self.is_trained:
            raise PredictionError("Model not trained. Call fit() or load_model().")
        if hasattr(X, "shape") and len(X.shape) != 2:
            raise InvalidInputError(f"Expected 2D input, got shape {X.shape}.")