"""
evaluator.py  (regression)
--------------------------
Evaluation utilities for damage regression models.
Reports RMSE and MAE on both log scale and dollar scale.
Produces a predicted vs actual scatter plot with residual insights.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from src.utils.logger import get_logger
from src.utils.exceptions import InvalidInputError

logger = get_logger(__name__)

PLOT_DIR = Path("docs/plots")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(
    y_true_log: np.ndarray,
    y_pred_log: np.ndarray,
    save_plots: bool = True,
    model_name: str = "model",
) -> dict:
    """
    Evaluate a regression model on log-scale predictions.

    Both inputs must be in LOG scale (log1p). Dollar-scale metrics are
    computed internally via expm1 so the caller never needs to worry about
    which scale to pass.

    Args:
        y_true_log:  True LOG_DAMAGE_USD values (from test split).
        y_pred_log:  Predicted LOG_DAMAGE_USD (from model.predict(return_log_scale=True)).
        save_plots:  Save plots to docs/plots/.
        model_name:  Label used in plots and logs.

    Returns:
        dict: rmse_log, mae_log, r2_log, rmse_dollars, mae_dollars, r2_dollars
    """
    _validate_inputs(y_true_log, y_pred_log)

    metrics = _compute_metrics(y_true_log, y_pred_log)
    _log_metrics(metrics, model_name)

    if save_plots:
        PLOT_DIR.mkdir(parents=True, exist_ok=True)
        _plot_predicted_vs_actual(y_true_log, y_pred_log, model_name)
        _plot_residuals(y_true_log, y_pred_log, model_name)

    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def _compute_metrics(y_true_log: np.ndarray, y_pred_log: np.ndarray) -> dict:
    """
    Compute RMSE, MAE, R² on both log and dollar scales.

    Log-scale metrics: what the model was actually optimized for.
    Dollar-scale metrics: what the business cares about.
    """
    # Log scale (training objective scale)
    rmse_log = float(np.sqrt(mean_squared_error(y_true_log, y_pred_log)))
    mae_log  = float(mean_absolute_error(y_true_log, y_pred_log))
    r2_log   = float(r2_score(y_true_log, y_pred_log))

    # Dollar scale (business interpretation)
    y_true_usd = np.expm1(y_true_log)
    y_pred_usd = np.expm1(y_pred_log).clip(min=0)

    rmse_usd = float(np.sqrt(mean_squared_error(y_true_usd, y_pred_usd)))
    mae_usd  = float(mean_absolute_error(y_true_usd, y_pred_usd))
    r2_usd   = float(r2_score(y_true_usd, y_pred_usd))

    return {
        "rmse_log":     round(rmse_log, 4),
        "mae_log":      round(mae_log, 4),
        "r2_log":       round(r2_log, 4),
        "rmse_dollars": round(rmse_usd, 2),
        "mae_dollars":  round(mae_usd, 2),
        "r2_dollars":   round(r2_usd, 4),
    }


def _log_metrics(metrics: dict, model_name: str) -> None:
    logger.info("─── %s — Regression Metrics ───", model_name)
    logger.info("  Log scale:    RMSE=%.4f | MAE=%.4f | R²=%.4f",
                metrics["rmse_log"], metrics["mae_log"], metrics["r2_log"])
    logger.info("  Dollar scale: RMSE=$%,.0f | MAE=$%,.0f | R²=%.4f",
                metrics["rmse_dollars"], metrics["mae_dollars"], metrics["r2_dollars"])


# ─────────────────────────────────────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────────────────────────────────────

def _plot_predicted_vs_actual(
    y_true_log: np.ndarray,
    y_pred_log: np.ndarray,
    model_name: str,
) -> None:
    """
    Scatter plot: predicted vs actual LOG_DAMAGE_USD.

    Plot in log scale for clarity — dollar scale compresses 99% of
    points near zero and makes the plot unreadable.
    The diagonal (perfect prediction line) is overlaid.
    """
    fig, ax = plt.subplots(figsize=(7, 6))

    # Hex bin for dense regions — more readable than 1M scatter points
    hb = ax.hexbin(
        y_true_log,
        y_pred_log,
        gridsize=50,
        cmap="Blues",
        mincnt=1,
        linewidths=0.2,
    )
    plt.colorbar(hb, ax=ax, label="Count per bin")

    # Perfect prediction line
    min_val = min(y_true_log.min(), y_pred_log.min())
    max_val = max(y_true_log.max(), y_pred_log.max())
    ax.plot([min_val, max_val], [min_val, max_val],
            color="#e74c3c", linewidth=1.5, linestyle="--", label="Perfect prediction")

    r2 = r2_score(y_true_log, y_pred_log)
    rmse = np.sqrt(mean_squared_error(y_true_log, y_pred_log))
    ax.set_title(f"{model_name} — predicted vs actual (log scale)\nR²={r2:.4f}  RMSE={rmse:.4f}",
                 fontsize=12)
    ax.set_xlabel("Actual log1p(damage)", fontsize=11)
    ax.set_ylabel("Predicted log1p(damage)", fontsize=11)
    ax.legend(fontsize=9)
    plt.tight_layout()

    out_path = PLOT_DIR / f"{model_name}_predicted_vs_actual.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Predicted vs actual plot saved: %s", out_path)


def _plot_residuals(
    y_true_log: np.ndarray,
    y_pred_log: np.ndarray,
    model_name: str,
) -> None:
    """
    Residual plot: (predicted - actual) vs actual.

    A good model should show residuals centered near zero with
    no systematic pattern. Funnel shapes indicate heteroscedasticity.
    """
    residuals = y_pred_log - y_true_log

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Left: residuals vs actual
    axes[0].scatter(y_true_log, residuals, alpha=0.3, s=5, color="#3498db")
    axes[0].axhline(0, color="#e74c3c", linewidth=1.5, linestyle="--")
    axes[0].set_xlabel("Actual log1p(damage)", fontsize=11)
    axes[0].set_ylabel("Residual (pred − actual)", fontsize=11)
    axes[0].set_title("Residuals vs actual", fontsize=12)

    # Right: residual distribution
    axes[1].hist(residuals, bins=60, color="#3498db", edgecolor="white", alpha=0.8)
    axes[1].axvline(0, color="#e74c3c", linewidth=1.5, linestyle="--")
    axes[1].axvline(residuals.mean(), color="#2ecc71", linewidth=1.5,
                    linestyle="-", label=f"Mean={residuals.mean():.3f}")
    axes[1].set_xlabel("Residual", fontsize=11)
    axes[1].set_ylabel("Count", fontsize=11)
    axes[1].set_title("Residual distribution", fontsize=12)
    axes[1].legend(fontsize=9)

    plt.suptitle(f"{model_name} — residual analysis", fontsize=13, y=1.02)
    plt.tight_layout()

    out_path = PLOT_DIR / f"{model_name}_residuals.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Residual plot saved: %s", out_path)


def _validate_inputs(y_true, y_pred) -> None:
    if len(y_true) != len(y_pred):
        raise InvalidInputError(
            f"y_true length {len(y_true)} != y_pred length {len(y_pred)}."
        )
    if len(y_true) == 0:
        raise InvalidInputError("Cannot evaluate on empty arrays.")
    if np.any(np.isnan(y_true)) or np.any(np.isnan(y_pred)):
        raise InvalidInputError("NaN values detected in y_true or y_pred.")