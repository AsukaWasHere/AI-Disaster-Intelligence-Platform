"""
evaluator.py  (classification)
-------------------------------
Evaluation utilities for EVENT_TYPE classifiers.
Computes F1 scores, confusion matrix, classification report,
and produces matplotlib/seaborn visualizations.

All plots are saved to docs/plots/ AND returned for embedding in dashboards.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # Non-interactive backend — safe for servers
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    f1_score,
    confusion_matrix,
    classification_report,
    ConfusionMatrixDisplay,
)
from sklearn.preprocessing import LabelEncoder

from src.utils.logger import get_logger
from src.utils.exceptions import InvalidInputError

logger = get_logger(__name__)

PLOT_DIR = Path("docs/plots")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label_encoder: LabelEncoder | None = None,
    save_plots: bool = True,
    model_name: str = "model",
) -> dict:
    """
    Full evaluation suite for a classification model.

    Args:
        y_true:        True integer-encoded labels.
        y_pred:        Predicted integer-encoded labels.
        label_encoder: If provided, class names are decoded for the report.
        save_plots:    If True, saves confusion matrix + F1 bar chart to docs/plots/.
        model_name:    Used in plot filenames and log messages.

    Returns:
        dict with keys: f1_weighted, f1_macro, f1_per_class, report_text
    """
    _validate_inputs(y_true, y_pred)

    class_names = (
        label_encoder.classes_.tolist() if label_encoder is not None else None
    )

    metrics = _compute_metrics(y_true, y_pred, class_names)
    _log_metrics(metrics, model_name)

    if save_plots:
        PLOT_DIR.mkdir(parents=True, exist_ok=True)
        _plot_confusion_matrix(y_true, y_pred, class_names, model_name)
        _plot_f1_per_class(metrics["f1_per_class"], model_name)

    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# Metric computation
# ─────────────────────────────────────────────────────────────────────────────

def _compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str] | None,
) -> dict:
    """Compute all classification metrics and return as a dict."""
    f1_weighted = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    f1_macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
    f1_per_class = f1_score(y_true, y_pred, average=None, zero_division=0)

    report = classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        zero_division=0,
        digits=4,
    )

    # Per-class F1 as a labeled Series for downstream use
    if class_names is not None:
        # Only label the classes that appear in y_true
        unique_labels = np.unique(y_true)
        labels_present = [class_names[i] for i in unique_labels if i < len(class_names)]
        f1_series = pd.Series(
            f1_score(y_true, y_pred, labels=unique_labels, average=None, zero_division=0),
            index=labels_present,
        ).sort_values(ascending=False)
    else:
        f1_series = pd.Series(f1_per_class).sort_values(ascending=False)

    return {
        "f1_weighted": round(float(f1_weighted), 4),
        "f1_macro":    round(float(f1_macro), 4),
        "f1_per_class": f1_series,
        "report_text":  report,
    }


def _log_metrics(metrics: dict, model_name: str) -> None:
    logger.info("─── %s — Classification Metrics ───", model_name)
    logger.info("  F1 (weighted) : %.4f", metrics["f1_weighted"])
    logger.info("  F1 (macro)    : %.4f", metrics["f1_macro"])
    logger.info("  Bottom 5 classes by F1:\n%s",
                metrics["f1_per_class"].tail(5).to_string())
    logger.info("Classification report:\n%s", metrics["report_text"])


# ─────────────────────────────────────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────────────────────────────────────

def _plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str] | None,
    model_name: str,
) -> None:
    """
    Plot a normalized confusion matrix heatmap.

    Normalized by true class (rows sum to 1.0) so rare classes are
    not visually dominated by frequent ones.
    """
    cm = confusion_matrix(y_true, y_pred, normalize="true")
    n_classes = cm.shape[0]

    # For large class counts (50+ EVENT_TYPEs), cap display to top-20 by frequency
    if n_classes > 25 and class_names is not None:
        top_idx = np.argsort(np.bincount(y_true.astype(int)))[::-1][:20]
        mask_true = np.isin(y_true, top_idx)
        mask_pred = np.isin(y_pred, top_idx)
        mask = mask_true & mask_pred
        if mask.sum() > 0:
            y_true_plot = y_true[mask]
            y_pred_plot = y_pred[mask]
            labels_plot = [class_names[i] for i in top_idx if i < len(class_names)]
            cm = confusion_matrix(y_true_plot, y_pred_plot, labels=top_idx, normalize="true")
        else:
            labels_plot = class_names
    else:
        labels_plot = class_names

    fig_size = max(10, len(cm) * 0.5)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.9))

    sns.heatmap(
        cm,
        annot=len(cm) <= 20,        # Annotate cells only when readable
        fmt=".2f",
        cmap="Blues",
        xticklabels=labels_plot or "auto",
        yticklabels=labels_plot or "auto",
        ax=ax,
        linewidths=0.3,
    )
    ax.set_title(f"{model_name} — normalized confusion matrix", fontsize=13, pad=12)
    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("True", fontsize=11)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    plt.tight_layout()

    out_path = PLOT_DIR / f"{model_name}_confusion_matrix.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Confusion matrix saved: %s", out_path)


def _plot_f1_per_class(f1_series: pd.Series, model_name: str) -> None:
    """
    Horizontal bar chart of F1 score per EVENT_TYPE class.

    Bars are colored by performance tier:
      - Green  (F1 ≥ 0.70): Good
      - Orange (0.40 ≤ F1 < 0.70): Needs improvement
      - Red    (F1 < 0.40): Poor
    """
    # Show top 30 classes for readability
    series = f1_series.head(30) if len(f1_series) > 30 else f1_series
    series = series.sort_values(ascending=True)  # Bottom of chart = worst

    colors = [
        "#2ecc71" if v >= 0.70 else "#e67e22" if v >= 0.40 else "#e74c3c"
        for v in series.values
    ]

    fig, ax = plt.subplots(figsize=(9, max(5, len(series) * 0.35)))
    bars = ax.barh(series.index, series.values, color=colors, edgecolor="none", height=0.7)

    # Value labels on bars
    for bar, val in zip(bars, series.values):
        ax.text(
            val + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}", va="center", ha="left", fontsize=8,
        )

    ax.set_xlim(0, 1.12)
    ax.set_xlabel("F1 Score", fontsize=11)
    ax.set_title(f"{model_name} — F1 per event type", fontsize=13, pad=12)
    ax.axvline(0.70, color="#2ecc71", linestyle="--", alpha=0.5, linewidth=1)
    ax.axvline(0.40, color="#e74c3c", linestyle="--", alpha=0.5, linewidth=1)
    ax.tick_params(axis="y", labelsize=9)
    plt.tight_layout()

    out_path = PLOT_DIR / f"{model_name}_f1_per_class.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("F1 per class plot saved: %s", out_path)


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate_inputs(y_true, y_pred) -> None:
    if len(y_true) != len(y_pred):
        raise InvalidInputError(
            f"y_true length {len(y_true)} != y_pred length {len(y_pred)}."
        )
    if len(y_true) == 0:
        raise InvalidInputError("Cannot evaluate on empty arrays.")