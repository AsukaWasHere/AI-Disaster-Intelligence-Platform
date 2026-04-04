"""
nlp_processing.py  (model layer)
---------------------------------
Loads the saved TF-IDF vectorizer from the data pipeline and transforms
new narratives into sparse feature matrices for inference.

DESIGN: This module is the inference-time counterpart to the pipeline's
build_tfidf_matrix(). The pipeline FITS the vectorizer.
This module only TRANSFORMS using the already-fitted vectorizer.
Never call fit_transform here — that would cause train/test leakage.
"""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.sparse import csr_matrix, load_npz, hstack

from src.utils.config import CONFIG
from src.utils.logger import get_logger
from src.utils.exceptions import ModelNotFoundError, InvalidInputError

logger = get_logger(__name__)


class NLPProcessor:
    """
    Wraps the fitted TF-IDF vectorizer for inference-time text transformation.

    Usage:
        processor = NLPProcessor()
        sparse_matrix = processor.transform(df["COMBINED_NARRATIVE"])
    """

    def __init__(self, vectorizer_path: str | None = None) -> None:
        vec_path = Path(
            vectorizer_path
            or CONFIG["data"]["processed_dir"] + "tfidf_vectorizer.pkl"
        )
        if not vec_path.exists():
            raise ModelNotFoundError(f"TF-IDF vectorizer not found at: {vec_path}")

        self.vectorizer = joblib.load(vec_path)
        self.vocab_size = len(self.vectorizer.vocabulary_)
        logger.info(
            "TF-IDF vectorizer loaded. Vocabulary size: %d",
            self.vocab_size,
        )

    def transform(self, texts: pd.Series | list[str]) -> csr_matrix:
        """
        Transform narrative texts into a sparse TF-IDF matrix.

        Args:
            texts: Series or list of cleaned narrative strings.
                   Use the same cleaning applied during pipeline
                   (lowercase, punctuation removed).

        Returns:
            scipy csr_matrix of shape (n_samples, vocab_size).

        Raises:
            InvalidInputError: If texts is empty.
        """
        if isinstance(texts, pd.Series):
            texts = texts.fillna("").tolist()
        texts = [str(t) for t in texts]

        if len(texts) == 0:
            raise InvalidInputError("Cannot transform empty text list.")

        # transform() uses the fitted vocabulary — never refit
        sparse = self.vectorizer.transform(texts)
        logger.debug(
            "TF-IDF transform: %d docs → shape %s, density %.5f",
            len(texts),
            sparse.shape,
            sparse.nnz / max(sparse.shape[0] * sparse.shape[1], 1),
        )
        return sparse

    def get_feature_names(self) -> list[str]:
        """Return the TF-IDF vocabulary feature names (for interpretability)."""
        return self.vectorizer.get_feature_names_out().tolist()


def load_tfidf_matrix(split: str = "train") -> csr_matrix:
    """
    Load a pre-computed TF-IDF sparse matrix from data/processed/.

    Args:
        split: "train" or "test"

    Returns:
        scipy csr_matrix

    Raises:
        ModelNotFoundError: If the .npz file is missing.
    """
    path = Path(CONFIG["data"]["processed_dir"]) / f"tfidf_{split}.npz"
    if not path.exists():
        raise ModelNotFoundError(f"TF-IDF matrix not found: {path}. Run pipeline.py first.")
    matrix = load_npz(str(path))
    logger.info("Loaded TF-IDF %s matrix: shape=%s", split, matrix.shape)
    return matrix