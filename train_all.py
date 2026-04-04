from src.models.classification.random_forest import DisasterRandomForestClassifier
from src.models.regression.xgboost_reg import DisasterXGBoostRegressor
import pandas as pd

# Load processed data
X_train = pd.read_parquet("data/processed/X_train.parquet")
y_clf = pd.read_parquet("data/processed/y_clf_train.parquet")
y_reg = pd.read_parquet("data/processed/y_reg_train.parquet")

# Train classification
clf = DisasterRandomForestClassifier()
clf.fit(X_train, y_clf)
clf.save_model("models/classification/random_forest.pkl")

# Train regression
reg = DisasterXGBoostRegressor()
reg.fit(X_train, y_reg)
reg.save_model("models/regression/xgboost_regressor.pkl")

print("Models trained and saved!")