"""
summarizer.py
-------------
Lightweight narrative summarization for disaster event descriptions.

Two approaches (both without requiring a GPU):

1. TextRank (default): Graph-based extractive summarization.
   Sentences are nodes; edges = cosine similarity of TF-IDF vectors.
   Top-scoring sentences by PageRank are selected.
   Best for: multi-sentence narratives with varied content.

2. Lead sentence fallback: Returns first N sentences.
   Best for: short narratives (< 3 sentences), or when TF-IDF is unavailable.

We do NOT use a neural abstractive model (BART, T5) here by default —
they require GPU for acceptable latency in production. The TextRank
approach produces good extractive summaries at sub-millisecond speed.
"""

import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.utils.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DisasterSummarizer:
    """
    Extractive summarizer for NOAA disaster narratives.

    Primary method: TextRank (sentence-level graph ranking).
    Fallback: Lead-sentence extraction.
    """

    def __init__(self, max_sentences: int = 3) -> None:
        """
        Args:
            max_sentences: Maximum sentences to include in summary.
        """
        self.max_sentences = max_sentences

    def summarize(self, text: str, max_sentences: int | None = None) -> str:
        """
        Summarize a single disaster narrative.

        Args:
            text: EVENT_NARRATIVE or COMBINED_NARRATIVE string.
            max_sentences: Override default max_sentences for this call.

        Returns:
            Summarized text string. Empty string if input is empty.
        """
        n = max_sentences or self.max_sentences
        if not text or not text.strip():
            return ""

        sentences = self._split_sentences(text)
        if len(sentences) <= n:
            # Text is already short enough — return as-is
            return text.strip()

        try:
            return self._textrank_summarize(sentences, n)
        except Exception as exc:
            logger.debug("TextRank failed (%s), using lead sentences.", exc)
            return self._lead_sentence_fallback(sentences, n)

    def summarize_batch(
        self, texts: list[str], max_sentences: int | None = None
    ) -> list[str]:
        """
        Summarize a batch of narratives.

        Args:
            texts: List of narrative strings.
            max_sentences: Override for all items in batch.

        Returns:
            List of summary strings.
        """
        return [self.summarize(t, max_sentences) for t in texts]

    # ── TextRank ──────────────────────────────────────────────────────────────

    def _textrank_summarize(self, sentences: list[str], n: int) -> str:
        """
        TextRank extractive summarization.

        Algorithm:
        1. Vectorize sentences with TF-IDF
        2. Build similarity matrix: sim[i][j] = cosine(sentence_i, sentence_j)
        3. Treat as a graph: nodes = sentences, edges = similarity scores
        4. Run PageRank on the graph to score each sentence by "centrality"
        5. Select top-n sentences by score, preserving original order

        Why preserve original order?
        Disaster narratives are written chronologically: cause → event → damage.
        Reordering by score breaks the narrative coherence.
        """
        if len(sentences) < 2:
            return sentences[0] if sentences else ""

        # Build sentence TF-IDF matrix
        # min_df=1 because we're working on a single document's sentences
        tfidf = TfidfVectorizer(
            min_df=1,
            stop_words="english",
            ngram_range=(1, 1),
        )
        try:
            tfidf_matrix = tfidf.fit_transform(sentences)
        except ValueError:
            # All sentences are stop words — use fallback
            return self._lead_sentence_fallback(sentences, n)

        # Similarity matrix: (n_sentences × n_sentences)
        sim_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

        # Zero out self-similarity (diagonal)
        np.fill_diagonal(sim_matrix, 0.0)

        # PageRank-style scoring via power iteration
        scores = self._pagerank(sim_matrix, damping=0.85, max_iter=100, tol=1e-6)

        # Select top-n indices, then sort by original position
        top_indices = sorted(
            np.argsort(scores)[::-1][:n],
            key=lambda i: i,  # Preserve narrative order
        )

        return " ".join(sentences[i] for i in top_indices)

    def _pagerank(
        self,
        matrix: np.ndarray,
        damping: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> np.ndarray:
        """
        Simple PageRank via power iteration on a similarity matrix.

        Args:
            matrix:   Square similarity matrix, non-negative.
            damping:  PageRank damping factor (0.85 is the standard value).
            max_iter: Maximum iterations.
            tol:      Convergence tolerance.

        Returns:
            np.ndarray of scores, one per sentence.
        """
        n = matrix.shape[0]

        # Normalize rows to get transition probabilities
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1   # Avoid division by zero for isolated nodes
        transition = matrix / row_sums

        # Initialize uniform scores
        scores = np.ones(n) / n

        for _ in range(max_iter):
            prev_scores = scores.copy()
            scores = (1 - damping) / n + damping * transition.T @ scores
            if np.linalg.norm(scores - prev_scores, 1) < tol:
                break

        return scores

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _lead_sentence_fallback(self, sentences: list[str], n: int) -> str:
        """Return first n sentences as a simple fallback summary."""
        return " ".join(sentences[:n])

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _split_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences using simple punctuation rules.

        We avoid NLTK/spaCy sentence splitting here to keep this module
        dependency-free. NOAA narratives use consistent punctuation —
        splitting on '.', '!', '?' with length filtering is sufficient.
        """
        # Split on sentence-ending punctuation
        raw = re.split(r"(?<=[.!?])\s+", text.strip())

        # Filter out fragments (< 10 chars) and empty strings
        sentences = [s.strip() for s in raw if len(s.strip()) >= 10]
        return sentences if sentences else [text.strip()]