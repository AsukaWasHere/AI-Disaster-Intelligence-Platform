"""
exceptions.py
-------------
Custom exception hierarchy for the AI Disaster Intelligence Platform.

DESIGN:
  All exceptions inherit from DisasterPlatformError.
  This means a single except DisasterPlatformError catches everything,
  while specific subclasses allow targeted handling.

  The API layer converts these to HTTP error responses with appropriate
  status codes (400 for invalid input, 404 for missing models, 500 for
  internal prediction failures).
"""


class DisasterPlatformError(Exception):
    """
    Base exception for all platform-specific errors.
    Catch this to handle all project errors in one block.
    """


class DataLoadError(DisasterPlatformError):
    """
    Raised when raw or processed data cannot be read or parsed.

    Examples:
      - Raw CSV file not found at expected path
      - Parquet file is corrupted or has unexpected schema
      - Expected column missing from loaded DataFrame
    """


class FeatureEngineeringError(DisasterPlatformError):
    """
    Raised when a feature transformation step fails.

    Examples:
      - KMeans clustering fails due to insufficient data
      - A required column is absent from the clean DataFrame
      - Log transformation receives negative input
    """


class ModelNotFoundError(DisasterPlatformError):
    """
    Raised when a serialized model file cannot be located.

    Examples:
      - random_forest.pkl missing from models/classification/
      - label_encoder.pkl not found after pipeline has been run
      - TF-IDF vectorizer .pkl not present at expected path

    HTTP equivalent: 404 Not Found
    """


class PredictionError(DisasterPlatformError):
    """
    Raised when model inference fails at runtime.

    Examples:
      - predict() called on an untrained model
      - Model internal error during forward pass
      - NaN values in prediction output

    HTTP equivalent: 500 Internal Server Error
    """


class InvalidInputError(DisasterPlatformError):
    """
    Raised when API or function input fails validation.

    Examples:
      - Feature matrix has wrong number of columns
      - Input text is None where a string is required
      - Prediction requested for 0 samples
      - Risk score weights don't include required keys

    HTTP equivalent: 400 Bad Request
    """


class ConfigurationError(DisasterPlatformError):
    """
    Raised when a required configuration key is missing or invalid.

    Examples:
      - config.yaml missing a required section
      - Invalid database connection string
      - Model parameter has wrong type
    """