"""
train_sentiment.py — XGBoost Model with Sentiment Features
=============================================================
Retrains the XGBoost classifier with sentiment features added
to the price + technical feature set.

This model should outperform the baseline — the improvement is
a key result for the project report.

Usage:
    from app.ml.train_sentiment import train_sentiment
    model, metrics = train_sentiment("AAPL")
"""

import logging
import os

import joblib
from xgboost import XGBClassifier

from app.config import TICKERS
from app.features.builder import build_feature_matrix, build_multi_ticker_matrix
from app.ml.evaluate import evaluate_model, save_metrics

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "trained_models"
)


def train_sentiment(
    ticker: str | None = None,
    model_version: str = "sentiment_v1",
) -> tuple:
    """
    Train XGBoost model with price + technical + sentiment features.

    Args:
        ticker: Single ticker or None for all tickers combined.
        model_version: Version string for saving.

    Returns:
        Tuple of (trained_model, metrics_dict).
    """
    logger.info(f"Training sentiment-augmented model: {model_version}")
    logger.info(f"Ticker: {ticker or 'ALL (' + ', '.join(TICKERS) + ')'}")

    # Build feature matrix WITH sentiment features
    if ticker:
        X_train, X_test, y_train, y_test, feature_names = build_feature_matrix(
            ticker, include_sentiment=True
        )
    else:
        X_train, X_test, y_train, y_test, feature_names = build_multi_ticker_matrix(
            TICKERS, include_sentiment=True
        )

    logger.info(f"Features ({len(feature_names)}): {feature_names}")
    logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")

    # Handle class imbalance
    n_positive = y_train.sum()
    n_negative = len(y_train) - n_positive
    scale_weight = n_negative / max(n_positive, 1)

    # Train XGBoost — same hyperparams as baseline for fair comparison
    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_weight,
        random_state=42,
        use_label_encoder=False,
        eval_metric="logloss",
        verbosity=0,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Evaluate
    metrics = evaluate_model(model, X_test, y_test)

    # Save model
    os.makedirs(MODELS_DIR, exist_ok=True)
    model_path = os.path.join(MODELS_DIR, f"{model_version}.joblib")
    joblib.dump(
        {"model": model, "feature_names": feature_names},
        model_path,
    )
    logger.info(f"Model saved to {model_path}")

    # Save metrics to DB
    save_metrics(metrics, model_version, ticker)

    # Log feature importances — especially interesting to see where
    # sentiment ranks vs. technical indicators
    importances = model.feature_importances_
    feat_imp = sorted(
        zip(feature_names, importances),
        key=lambda x: x[1],
        reverse=True,
    )
    logger.info("\nFeature Importances (sentiment model):")
    for name, imp in feat_imp:
        marker = " ← SENTIMENT" if "sentiment" in name else ""
        logger.info(f"  {name:<25} {imp:.4f}{marker}")

    return model, metrics
