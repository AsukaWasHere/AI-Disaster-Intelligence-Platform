"""
src/utils/merge_features.py
----------------------------
Merges structured feature matrices (dense, from Parquet)
with NLP TF-IDF matrices (sparse, from .npz files).

CONCATENATION STRATEGY:
  Dense + Sparse → final matrix must be sparse.

  scipy.sparse.hstack() is the correct tool.
  It accepts a mix of dense arrays and sparse matrices,
  converts everything to sparse CSR format, and horizontally stacks.

  DO NOT use numpy.hstack() — it converts sparse to dense first,
  which for a 500-feature TF-IDF matrix across 1M rows would require
  ~4GB RAM just for the text features.

COLUMN ORDER:
  [structured features | TF-IDF features]
  Structured first so feature importances are interpretable without
  counting into the TF-IDF block.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.sparse import csr_matrix, hstack, issparse

from src.utils.logger import get_logger
from src.utils.exceptions import InvalidInputError

logger = get_logger(__name__)


def merge_structured_and_nlp(
    X_structured: pd.DataFrame | np.ndarray,
    X_tfidf: csr_matrix,
) -> csr_matrix:
    """
    Horizontally concatenate structured features with TF-IDF sparse matrix.

    Args:
        X_structured: Dense feature matrix from X_train.parquet.
                      Shape: (n_samples, n_structured_features)
        X_tfidf:      Sparse TF-IDF matrix from tfidf_train.npz.
                      Shape: (n_samples, n_tfidf_features)

    Returns:
        scipy csr_matrix of shape (n_samples, n_structured + n_tfidf).

    Raises:
        InvalidInputError: If row counts don't match.
    """
    n_struct = X_structured.shape[0]
    n_tfidf = X_tfidf.shape[0]

    if n_struct != n_tfidf:
        raise InvalidInputError(
            f"Row count mismatch: structured={n_struct}, tfidf={n_tfidf}. "
            "Ensure both matrices come from the same split."
        )

    # Convert dense DataFrame/array to sparse for hstack compatibility
    if isinstance(X_structured, pd.DataFrame):
        X_struct_sparse = csr_matrix(X_structured.values.astype(np.float32))
    elif isinstance(X_structured, np.ndarray):
        X_struct_sparse = csr_matrix(X_structured.astype(np.float32))
    elif issparse(X_structured):
        X_struct_sparse = X_structured.tocsr()
    else:
        raise InvalidInputError(f"Unsupported type for X_structured: {type(X_structured)}")

    # Ensure TF-IDF is CSR format for efficient row slicing
    X_tfidf_csr = X_tfidf.tocsr()

    merged = hstack([X_struct_sparse, X_tfidf_csr], format="csr")

    logger.info(
        "Feature merge: structured(%d) + tfidf(%d) = %d total features, %d samples.",
        X_struct_sparse.shape[1],
        X_tfidf_csr.shape[1],
        merged.shape[1],
        merged.shape[0],
    )
    return merged


def load_and_merge(split: str = "train") -> csr_matrix:
    """
    Convenience loader: reads X_{split}.parquet + tfidf_{split}.npz and merges them.

    Args:
        split: "train" or "test"

    Returns:
        Merged sparse feature matrix.
    """
    from scipy.sparse import load_npz
    from src.utils.config import CONFIG

    processed_dir = Path(CONFIG["data"]["processed_dir"])

    X_struct = pd.read_parquet(processed_dir / f"X_{split}.parquet")
    X_tfidf = load_npz(str(processed_dir / f"tfidf_{split}.npz"))

    return merge_structured_and_nlp(X_struct, X_tfidf)