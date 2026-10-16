"""
train_baseline.py — XGBoost Baseline Model Training
======================================================
Trains an XGBoost classifier on price + technical features only.
This is the baseline model (no sentiment data).

The model predicts next-day stock movement:
  1 = UP (next close > today's close)
  0 = DOWN (next close <= today's close)

Usage:
    from app.ml.train_baseline import train_baseline
    model, metrics = train_baseline("AAPL")
    model, metrics = train_baseline()  # all tickers combined
"""

import logging
import os

import joblib
from xgboost import XGBClassifier

from app.config import TICKERS
from app.features.builder import build_feature_matrix, build_multi_ticker_matrix
from app.ml.evaluate import evaluate_model, save_metrics

logger = logging.getLogger(__name__)

# Directory to save trained models
MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "trained_models"
)


def train_baseline(
    ticker: str | None = None,
    model_version: str = "baseline_v1",
) -> tuple:
    """
    Train the XGBoost baseline model on price + technical features.

    Args:
        ticker: Single ticker to train on. If None, trains on all tickers.
        model_version: Version string for saving (default "baseline_v1").

    Returns:
        Tuple of (trained_model, metrics_dict).
    """
    logger.info(f"Training baseline model: {model_version}")
    logger.info(f"Ticker: {ticker or 'ALL (' + ', '.join(TICKERS) + ')'}")

    # Build feature matrix
    if ticker:
        X_train, X_test, y_train, y_test, feature_names = build_feature_matrix(
            ticker, include_sentiment=False
        )
    else:
        X_train, X_test, y_train, y_test, feature_names = build_multi_ticker_matrix(
            TICKERS, include_sentiment=False
        )

    logger.info(f"Features: {feature_names}")
    logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")
    logger.info(f"Class balance (train): UP={y_train.sum()}, DOWN={len(y_train) - y_train.sum()}")

    # ---- Train XGBoost Classifier ----
    # Hyperparameters kept simple for a student project
    # scale_pos_weight helps with class imbalance if present
    n_positive = y_train.sum()
    n_negative = len(y_train) - n_positive
    scale_weight = n_negative / max(n_positive, 1)

    model = XGBClassifier(
        n_estimators=200,          # number of trees
        max_depth=5,               # tree depth (prevents overfitting)
        learning_rate=0.05,        # slow learning for better generalization
        subsample=0.8,             # use 80% of data per tree
        colsample_bytree=0.8,     # use 80% of features per tree
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

    # ---- Evaluate ----
    metrics = evaluate_model(model, X_test, y_test)

    # ---- Save model ----
    os.makedirs(MODELS_DIR, exist_ok=True)
    model_path = os.path.join(MODELS_DIR, f"{model_version}.joblib")
    joblib.dump(
        {"model": model, "feature_names": feature_names},
        model_path,
    )
    logger.info(f"Model saved to {model_path}")

    # ---- Save metrics to DB ----
    save_metrics(metrics, model_version, ticker)

    # ---- Log feature importance ----
    importances = model.feature_importances_
    feat_imp = sorted(
        zip(feature_names, importances),
        key=lambda x: x[1],
        reverse=True,
    )
    logger.info("\nTop Feature Importances:")
    for name, imp in feat_imp[:10]:
        logger.info(f"  {name:<20} {imp:.4f}")

    return model, metrics
