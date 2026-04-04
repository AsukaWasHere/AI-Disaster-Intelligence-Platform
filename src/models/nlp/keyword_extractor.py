"""
keyword_extractor.py
--------------------
Extract top keywords from EVENT_NARRATIVE using two approaches:

1. TF-IDF based (default): Uses the fitted TF-IDF vectorizer to find
   terms that are distinctive for a specific document relative to the corpus.
   Best for: "what words make this event unique?"

2. Frequency based (fallback): Simple word frequency after stopword removal.
   Best for: fast inference with no vectorizer dependency.
"""

import re
import numpy as np
import pandas as pd
from collections import Counter

from src.models.nlp.nlp_processing import NLPProcessor
from src.utils.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)

# NOAA-domain stopwords (extend standard English stopwords)
_DOMAIN_STOPWORDS: set[str] = {
    "county", "area", "reported", "occurred", "event", "noaa", "storm",
    "weather", "service", "national", "nws", "local", "approximately",
    "mph", "inch", "inches", "mile", "miles", "hour", "hours",
    "minute", "minutes", "wind", "winds",
}


class KeywordExtractor:
    """
    Extracts top keywords from disaster narratives.

    Preferred mode: TF-IDF scoring (uses fitted vectorizer).
    Fallback mode:  Token frequency (no vectorizer needed).
    """

    def __init__(self, use_tfidf: bool = True) -> None:
        """
        Args:
            use_tfidf: If True (default), use TF-IDF scoring.
                       If False, fall back to frequency-based extraction.
        """
        self.use_tfidf = use_tfidf
        self._processor: NLPProcessor | None = None

        if use_tfidf:
            try:
                self._processor = NLPProcessor()
            except Exception as exc:
                logger.warning(
                    "TF-IDF vectorizer unavailable (%s). Falling back to frequency-based extraction.",
                    exc,
                )
                self.use_tfidf = False

    def extract(self, text: str, top_n: int | None = None) -> list[str]:
        """
        Extract top keywords from a single narrative string.

        Args:
            text:  Raw or cleaned narrative text.
            top_n: Number of keywords to return. Defaults to config value.

        Returns:
            List of keyword strings, most important first.
        """
        top_n = top_n or CONFIG["nlp"]["top_keywords"]
        if not text or not text.strip():
            return []

        if self.use_tfidf and self._processor is not None:
            return self._extract_tfidf([text], top_n)[0]
        return self._extract_frequency(text, top_n)

    def extract_batch(
        self,
        texts: list[str] | pd.Series,
        top_n: int | None = None,
    ) -> list[list[str]]:
        """
        Extract keywords from a batch of narratives efficiently.

        Args:
            texts: List or Series of narrative strings.
            top_n: Keywords per document.

        Returns:
            List of keyword lists, one per input text.
        """
        top_n = top_n or CONFIG["nlp"]["top_keywords"]
        if isinstance(texts, pd.Series):
            texts = texts.fillna("").tolist()

        if self.use_tfidf and self._processor is not None:
            return self._extract_tfidf(texts, top_n)

        return [self._extract_frequency(t, top_n) for t in texts]

    # ── TF-IDF extraction ─────────────────────────────────────────────────────

    def _extract_tfidf(self, texts: list[str], top_n: int) -> list[list[str]]:
        """
        Use TF-IDF scores to rank terms within each document.

        For each document, find the terms with the highest TF-IDF score.
        These are terms that appear frequently in THIS document but are
        relatively rare across the whole corpus — i.e., distinctive terms.
        """
        try:
            sparse_matrix = self._processor.transform(texts)
            feature_names = np.array(self._processor.get_feature_names())
            results = []

            for i in range(sparse_matrix.shape[0]):
                row = sparse_matrix[i].toarray().flatten()
                if row.sum() == 0:
                    results.append([])
                    continue
                top_indices = np.argsort(row)[::-1][:top_n]
                keywords = [
                    feature_names[idx]
                    for idx in top_indices
                    if row[idx] > 0
                ]
                results.append(keywords)

            return results

        except Exception as exc:
            logger.warning("TF-IDF keyword extraction failed: %s. Using frequency fallback.", exc)
            return [self._extract_frequency(t, top_n) for t in texts]

    # ── Frequency extraction ──────────────────────────────────────────────────

    def _extract_frequency(self, text: str, top_n: int) -> list[str]:
        """
        Simple frequency-based keyword extraction.

        Steps:
        1. Lowercase + remove non-alphabetic characters
        2. Tokenize on whitespace
        3. Remove stopwords (spaCy defaults + domain stopwords)
        4. Remove tokens shorter than 3 characters
        5. Return top-N by frequency
        """
        text = re.sub(r"[^a-zA-Z\s]", " ", text.lower())
        tokens = text.split()

        # Build stopword set once per call (small overhead, avoids spaCy import here)
        try:
            import spacy
            nlp = spacy.load(CONFIG["nlp"]["spacy_model"], disable=["parser", "ner", "tagger"])
            stopwords = nlp.Defaults.stop_words | _DOMAIN_STOPWORDS
        except Exception:
            # Minimal fallback if spaCy is unavailable
            stopwords = _DOMAIN_STOPWORDS

        filtered = [
            t for t in tokens
            if t not in stopwords and len(t) >= 3
        ]

        freq = Counter(filtered)
        return [word for word, _ in freq.most_common(top_n)]