"""
predict.py — Model Prediction Module
========================================
Loads a trained model and generates predictions for a given ticker.
Returns the prediction signal (UP/DOWN), confidence, and top features.

Usage:
    from app.ml.predict import predict_ticker
    result = predict_ticker("AAPL")
    # result = {"signal": "UP", "confidence": 0.73, "top_features": [...]}
"""

import logging
import os
from datetime import date

import joblib
import numpy as np
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.features.builder import load_price_data, load_sentiment_data
from app.features.technical import compute_indicators
from app.models import Prediction

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "trained_models"
)


def load_model(model_version: str = "sentiment_v1") -> tuple:
    """
    Load a saved model from disk.

    Args:
        model_version: Version string (matches the .joblib filename).

    Returns:
        Tuple of (model, feature_names).
    """
    model_path = os.path.join(MODELS_DIR, f"{model_version}.joblib")

    # Fall back to baseline if sentiment model doesn't exist
    if not os.path.exists(model_path):
        fallback = os.path.join(MODELS_DIR, "baseline_v1.joblib")
        if os.path.exists(fallback):
            logger.warning(
                f"Model '{model_version}' not found, falling back to baseline_v1"
            )
            model_path = fallback
            model_version = "baseline_v1"
        else:
            raise FileNotFoundError(
                f"No trained model found. Run training first: "
                f"python -m scripts.train_model"
            )

    data = joblib.load(model_path)
    logger.info(f"Loaded model: {model_version}")
    return data["model"], data["feature_names"]


def predict_ticker(
    ticker: str,
    model_version: str = "sentiment_v1",
    save_to_db: bool = True,
) -> dict:
    """
    Generate a prediction for a ticker using the most recent data.

    Steps:
      1. Load the trained model
      2. Get the latest price data and compute indicators
      3. Build feature vector for the most recent day
      4. Predict UP/DOWN with confidence
      5. Extract top contributing features
      6. Optionally save prediction to DB

    Args:
        ticker: Stock symbol (e.g. "AAPL").
        model_version: Which model to use.
        save_to_db: Whether to store the prediction in MySQL.

    Returns:
        dict: {signal, confidence, top_features, date, model_version}
    """
    # Step 1: Load model
    model, feature_names = load_model(model_version)

    # Step 2: Get price data and compute indicators
    df = load_price_data(ticker)
    if df.empty:
        raise ValueError(f"No price data for {ticker}")

    df = compute_indicators(df)

    # Step 3: Optionally merge sentiment (if model expects it)
    if any("sentiment" in f for f in feature_names):
        sentiment_df = load_sentiment_data(ticker)
        if not sentiment_df.empty:
            df = df.merge(sentiment_df, on="date", how="left")
            for col in ["sentiment_compound", "sentiment_positive", "sentiment_negative"]:
                if col in df.columns:
                    df[col] = df[col].ffill().fillna(0.0)

    # Step 4: Get the latest row with all features available
    available = [f for f in feature_names if f in df.columns]

    if len(available) != len(feature_names):
        missing = set(feature_names) - set(available)
        logger.warning(f"Missing features: {missing} — filling with 0")
        for col in missing:
            df[col] = 0.0
        available = feature_names

    df_clean = df.dropna(subset=available)

    if df_clean.empty:
        raise ValueError(f"No complete data rows for prediction on {ticker}")

    latest = df_clean.iloc[-1]
    feature_vector = latest[feature_names].values.reshape(1, -1)

    # Step 5: Predict
    prediction = model.predict(feature_vector)[0]
    probabilities = model.predict_proba(feature_vector)[0]

    signal = "UP" if prediction == 1 else "DOWN"
    confidence = float(probabilities[prediction])

    # Step 6: Top contributing features (by importance × value)
    importances = model.feature_importances_
    top_features = []
    for name, imp in sorted(
        zip(feature_names, importances), key=lambda x: x[1], reverse=True
    )[:5]:
        top_features.append({
            "name": name,
            "importance": round(float(imp), 4),
            "value": round(float(latest[name]), 4) if name in latest.index else None,
        })

    prediction_date = latest["date"] if "date" in latest.index else date.today()

    result = {
        "ticker": ticker,
        "signal": signal,
        "confidence": round(confidence, 4),
        "top_features": top_features,
        "date": str(prediction_date),
        "model_version": model_version,
    }

    logger.info(
        f"Prediction for {ticker}: {signal} "
        f"(confidence: {confidence:.2%})"
    )

    # Step 7: Save to DB
    if save_to_db:
        _save_prediction(result)

    return result


def _save_prediction(result: dict) -> None:
    """Store a prediction in the predictions table."""
    db: Session = SessionLocal()
    try:
        import json

        # Check for existing prediction (upsert logic)
        existing = db.query(Prediction).filter(
            Prediction.ticker == result["ticker"],
            Prediction.date == result["date"],
            Prediction.model_version == result["model_version"],
        ).first()

        if existing:
            existing.signal_dir = result["signal"]
            existing.confidence = result["confidence"]
            existing.features_json = json.dumps(result["top_features"])
        else:
            pred = Prediction(
                ticker=result["ticker"],
                date=result["date"],
                model_version=result["model_version"],
                signal_dir=result["signal"],
                confidence=result["confidence"],
                features_json=json.dumps(result["top_features"]),
            )
            db.add(pred)

        db.commit()
        logger.info(f"Prediction saved to DB for {result['ticker']}")

    except Exception as e:
        logger.error(f"Error saving prediction: {e}")
        db.rollback()
    finally:
        db.close()
