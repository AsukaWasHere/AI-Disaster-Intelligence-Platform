# Example: train_classifier.py (entry point script, not a new file)
# Run as: python -m scripts.train_classifier

from src.utils.merge_features import load_and_merge
from src.models.classification.random_forest import DisasterRandomForestClassifier
from src.models.classification.xgboost_clf import DisasterXGBoostClassifier
from src.models.classification.evaluator import evaluate
import pandas as pd
from pathlib import Path

processed = Path("data/processed/")

# Load targets
y_train = pd.read_parquet(processed / "y_clf_train.parquet")["EVENT_TYPE_ENCODED"].values
y_test  = pd.read_parquet(processed / "y_clf_test.parquet")["EVENT_TYPE_ENCODED"].values

# Merge structured + TF-IDF features
X_train = load_and_merge("train")   # returns sparse csr_matrix
X_test  = load_and_merge("test")

# Train RandomForest
rf = DisasterRandomForestClassifier()
rf.fit(X_train, y_train)
rf.save_model()

# Evaluate
y_pred_rf = rf.model.predict(X_test)          # raw int labels
evaluate(y_test, y_pred_rf, rf.label_encoder, model_name="random_forest")

# Train XGBoost
xgb = DisasterXGBoostClassifier()
xgb.fit(X_train, y_train, use_early_stopping=True)
xgb.save_model()

y_pred_xgb = xgb.model.predict(X_test)
evaluate(y_test, y_pred_xgb, xgb.label_encoder, model_name="xgboost_clf")