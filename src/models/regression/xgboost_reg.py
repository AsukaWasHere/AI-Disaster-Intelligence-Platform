"""
xgboost_reg.py
--------------
XGBoost regressor for TOTAL_DAMAGE_USD prediction.
Trains on log1p(TOTAL_DAMAGE_USD), predicts in dollar scale via expm1.
Uses early stopping to prevent overfitting on the log-scale target.
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from src.utils.config import CONFIG
from src.utils.logger import get_logger
from src.utils.exceptions import ModelNotFoundError, PredictionError, InvalidInputError

logger = get_logger(__name__)

DEFAULT_MODEL_DIR = Path("models/regression")


class DisasterXGBoostRegressor:
    """
    XGBoost regressor wrapper for disaster damage estimation.

    Training target: log1p(TOTAL_DAMAGE_USD)
    API output:      expm1(prediction) clipped to [0, ∞)

    XGBoost handles the heavy right tail of damage values better than
    linear models even after log-transformation, because it can learn
    non-linear interactions between EVENT_TYPE, MAGNITUDE, and geographic features.
    """

    def __init__(self) -> None:
        cfg = CONFIG["regression"]["xgboost"]
        reg_cfg = CONFIG["regression"]

        self.model = XGBRegressor(
            n_estimators=cfg["n_estimators"],
            max_depth=cfg["max_depth"],
            learning_rate=cfg["learning_rate"],
            subsample=cfg["subsample"],
            colsample_bytree=cfg["colsample_bytree"],
            objective="reg:squarederror",   # MSE loss on log scale
            eval_metric="rmse",
            n_jobs=-1,
            random_state=reg_cfg["random_state"],
            verbosity=0,
        )
        self.is_trained: bool = False
        logger.info("XGBoostRegressor initialized.")

    # ── Training ─────────────────────────────────────────────────────────────

    def fit(
        self,
        X_train: np.ndarray | pd.DataFrame,
        y_train: np.ndarray | pd.Series,
        use_early_stopping: bool = True,
        early_stopping_rounds: int = 50,
    ) -> "DisasterXGBoostRegressor":
        """
        Train on log-scale damage target with optional early stopping.

        Args:
            X_train: Feature matrix.
            y_train: LOG_DAMAGE_USD (log1p transformed). Never pass raw dollars.
            use_early_stopping: Holds out 10% for validation-based stopping.
            early_stopping_rounds: Patience rounds.

        Returns:
            self
        """
        logger.info(
            "Training XGBoost regressor: %d samples, %d features.",
            len(X_train),
            X_train.shape[1],
        )

        if use_early_stopping:
            X_tr, X_val, y_tr, y_val = train_test_split(
                X_train,
                y_train,
                test_size=0.10,
                random_state=CONFIG["regression"]["random_state"],
            )
            self.model.fit(
                X_tr,
                y_tr,
                eval_set=[(X_val, y_val)],
                early_stopping_rounds=early_stopping_rounds,
                verbose=False,
            )
            logger.info(
                "Early stopping: best iteration=%d, best RMSE (log)=%.4f",
                self.model.best_iteration,
                self.model.best_score,
            )
        else:
            self.model.fit(X_train, y_train)

        self.is_trained = True

        # Log feature importances (top 10)
        if hasattr(X_train, "columns"):
            fi = pd.Series(
                self.model.feature_importances_,
                index=X_train.columns,
            ).sort_values(ascending=False)
            logger.info("Top 10 feature importances:\n%s", fi.head(10).to_string())

        logger.info("XGBoost regression training complete.")
        return self

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(
        self,
        X: np.ndarray | pd.DataFrame,
        return_log_scale: bool = False,
    ) -> np.ndarray:
        """
        Predict total damage.

        Args:
            X: Feature matrix.
            return_log_scale: If True, return log-scale predictions (for RMSE eval).
                              If False (default), return dollar amounts.

        Returns:
            np.ndarray of predictions.
        """
        self._validate_for_inference(X)
        try:
            log_preds = self.model.predict(X)
            if return_log_scale:
                return log_preds
            return np.expm1(log_preds).clip(min=0)
        except Exception as exc:
            raise PredictionError(f"XGBoost regression prediction failed: {exc}") from exc

    # ── Serialization ─────────────────────────────────────────────────────────

    def save_model(self, path: str | None = None) -> Path:
        if not self.is_trained:
            raise PredictionError("Cannot save an untrained model.")
        save_path = Path(path or DEFAULT_MODEL_DIR / "xgboost_regressor.pkl")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, save_path, compress=3)
        logger.info("XGBoost regressor saved: %s", save_path)
        return save_path

    @classmethod
    def load_model(cls, path: str | None = None) -> "DisasterXGBoostRegressor":
        load_path = Path(path or DEFAULT_MODEL_DIR / "xgboost_regressor.pkl")
        if not load_path.exists():
            raise ModelNotFoundError(f"XGBoost regressor not found at: {load_path}")
        instance = joblib.load(load_path)
        logger.info("XGBoost regressor loaded from: %s", load_path)
        return instance

    def _validate_for_inference(self, X) -> None:
        if not self.is_trained:
            raise PredictionError("Model not trained. Call fit() or load_model().")
        if hasattr(X, "shape") and len(X.shape) != 2:
            raise InvalidInputError(f"Expected 2D input, got shape {X.shape}.")