"""
dependencies.py
---------------
Model loading, caching, and FastAPI dependency injection.

All models are loaded once at startup into module-level singletons.
Route handlers call get_*() functions which return the cached instances.
This avoids reloading multi-MB models on every request.
"""

import joblib
from pathlib import Path
from functools import lru_cache

from src.models.classification.random_forest  import DisasterRandomForestClassifier
from src.models.classification.xgboost_clf    import DisasterXGBoostClassifier
from src.models.regression.linear             import DisasterLinearRegressor
from src.models.regression.xgboost_reg        import DisasterXGBoostRegressor
from src.models.nlp.nlp_processing            import NLPProcessor
from src.models.nlp.keyword_extractor         import KeywordExtractor
from src.models.nlp.summarizer                import DisasterSummarizer
from src.utils.config                         import CONFIG
from src.utils.logger                         import get_logger
from src.utils.exceptions                     import ModelNotFoundError

logger = get_logger(__name__)

# ── Module-level singletons (populated at startup) ────────────────────────────

_clf_rf:     DisasterRandomForestClassifier | None = None
_clf_xgb:    DisasterXGBoostClassifier      | None = None
_reg_linear: DisasterLinearRegressor        | None = None
_reg_xgb:    DisasterXGBoostRegressor       | None = None
_nlp:        NLPProcessor                   | None = None
_keywords:   KeywordExtractor               | None = None
_summarizer: DisasterSummarizer             | None = None


def load_all_models() -> None:
    """
    Load every model into memory at API startup.
    Called once from the FastAPI lifespan context manager in main.py.
    Safe to call multiple times — skips already-loaded models.
    """
    global _clf_rf, _clf_xgb, _reg_linear, _reg_xgb, _nlp, _keywords, _summarizer

    model_dir = Path("models")

    # ── Classification ────────────────────────────────────────────────────────
    rf_path = model_dir / "classification" / "random_forest.pkl"
    if rf_path.exists():
        _clf_rf = DisasterRandomForestClassifier.load_model(str(rf_path))
        logger.info("Loaded RandomForest classifier.")
    else:
        logger.warning("RandomForest model not found at %s — skipping.", rf_path)

    xgb_clf_path = model_dir / "classification" / "xgboost_clf.pkl"
    if xgb_clf_path.exists():
        _clf_xgb = DisasterXGBoostClassifier.load_model(str(xgb_clf_path))
        logger.info("Loaded XGBoost classifier.")
    else:
        logger.warning("XGBoost classifier not found at %s — skipping.", xgb_clf_path)

    # ── Regression ────────────────────────────────────────────────────────────
    linear_path = model_dir / "regression" / "linear_regressor.pkl"
    if linear_path.exists():
        _reg_linear = DisasterLinearRegressor.load_model(str(linear_path))
        logger.info("Loaded Linear regressor.")
    else:
        logger.warning("Linear regressor not found at %s — skipping.", linear_path)

    xgb_reg_path = model_dir / "regression" / "xgboost_regressor.pkl"
    if xgb_reg_path.exists():
        _reg_xgb = DisasterXGBoostRegressor.load_model(str(xgb_reg_path))
        logger.info("Loaded XGBoost regressor.")
    else:
        logger.warning("XGBoost regressor not found at %s — skipping.", xgb_reg_path)

    # ── NLP ───────────────────────────────────────────────────────────────────
    try:
        _nlp = NLPProcessor()
        logger.info("Loaded NLP processor (TF-IDF vectorizer).")
    except Exception as exc:
        logger.warning("NLP processor unavailable: %s", exc)

    _keywords  = KeywordExtractor(use_tfidf=(_nlp is not None))
    _summarizer = DisasterSummarizer(max_sentences=3)
    logger.info("Keyword extractor and summarizer ready.")


# ── Dependency getters (injected into route handlers via Depends) ─────────────

def get_classifier() -> DisasterXGBoostClassifier | DisasterRandomForestClassifier:
    """
    Return the best available classifier.
    Prefers XGBoost; falls back to RandomForest.
    Raises ModelNotFoundError if neither is loaded.
    """
    if _clf_xgb is not None:
        return _clf_xgb
    if _clf_rf is not None:
        return _clf_rf
    raise ModelNotFoundError(
        "No classification model loaded. Run the training pipeline first."
    )


def get_regressor() -> DisasterXGBoostRegressor | DisasterLinearRegressor:
    """
    Return the best available regressor.
    Prefers XGBoost; falls back to Linear.
    """
    if _reg_xgb is not None:
        return _reg_xgb
    if _reg_linear is not None:
        return _reg_linear
    raise ModelNotFoundError(
        "No regression model loaded. Run the training pipeline first."
    )


def get_nlp_processor() -> NLPProcessor | None:
    return _nlp


def get_keyword_extractor() -> KeywordExtractor:
    if _keywords is None:
        return KeywordExtractor(use_tfidf=False)
    return _keywords


def get_summarizer() -> DisasterSummarizer:
    if _summarizer is None:
        return DisasterSummarizer()
    return _summarizer


@lru_cache(maxsize=1)
def get_config() -> dict:
    """Return the loaded config (cached after first call)."""
    return CONFIG