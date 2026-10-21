"""
predict.py — Model Prediction Module with Calibration & SHAP
============================================================
Generates stock direction predictions using calibrated probabilities,
configurable low-confidence abstention, and true SHAP feature attributions:
  - Loads trained model, calibrator, and feature definitions
  - Computes raw and calibrated confidence
  - Applies configurable threshold (e.g. 0.55): emits 'HOLD' when conviction is low
  - Calculates local SHAP Shapley values for the specific decision
  - Persists prediction with SHAP and calibration metadata to MySQL
"""

import json
import logging
import os
from datetime import date
from typing import Optional, Tuple

import joblib
import numpy as np
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.features.builder import load_price_data, load_sentiment_data
from app.features.technical import compute_indicators
from app.ml.calibration import ProbabilityCalibrator
from app.ml.shap_explainer import SHAPExplainer
from app.models import Prediction

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "trained_models"
)


def load_model_artifact(model_version: str = "sentiment_v1") -> Tuple[object, list, Optional[object]]:
    """
    Load a saved model artifact, returning (model, feature_names, calibrator).
    Maintains backward compatibility with legacy .joblib files.
    """
    model_path = os.path.join(MODELS_DIR, f"{model_version}.joblib")

    if not os.path.exists(model_path):
        fallback = os.path.join(MODELS_DIR, "baseline_v1.joblib")
        if os.path.exists(fallback):
            logger.warning(f"Model '{model_version}' not found, falling back to baseline_v1")
            model_path = fallback
            model_version = "baseline_v1"
        else:
            raise FileNotFoundError(
                f"No trained model found. Run training first: python -m scripts.train_model"
            )

    data = joblib.load(model_path)
    model = data.get("model") if isinstance(data, dict) else data
    feature_names = data.get("feature_names", []) if isinstance(data, dict) else []
    calibrator = data.get("calibrator", None) if isinstance(data, dict) else None

    logger.info(f"Loaded model: {model_version} (calibrated: {calibrator is not None})")
    return model, feature_names, calibrator


def load_model(model_version: str = "sentiment_v1") -> tuple:
    """Legacy helper returning (model, feature_names)."""
    model, feature_names, _ = load_model_artifact(model_version)
    return model, feature_names


def predict_ticker(
    ticker: str,
    model_version: str = "sentiment_v1",
    confidence_threshold: float = 0.55,
    save_to_db: bool = True,
) -> dict:
    """
    Generate a prediction for a ticker using the latest data, calibrated confidence,
    and SHAP local feature attributions.

    Returns:
        dict: {
            ticker, signal (UP/DOWN/HOLD), confidence, raw_confidence,
            is_calibrated, top_features (with SHAP values), date, model_version
        }
    """
    # Step 1: Load model and calibrator
    model, feature_names, calibrator = load_model_artifact(model_version)

    # Step 2: Load price and indicators
    df = load_price_data(ticker)
    if df.empty:
        raise ValueError(f"No price data for {ticker}")

    df = compute_indicators(df)

    # Step 3: Merge sentiment if expected
    if any("sentiment" in f for f in feature_names):
        sentiment_df = load_sentiment_data(ticker)
        if not sentiment_df.empty:
            df = df.merge(sentiment_df, on="date", how="left")
            for col in ["sentiment_compound", "sentiment_positive", "sentiment_negative"]:
                if col in df.columns:
                    df[col] = df[col].ffill().fillna(0.0)

    # Step 4: Ensure all required features are present
    available = [f for f in feature_names if f in df.columns]
    if len(available) != len(feature_names):
        missing = set(feature_names) - set(available)
        logger.warning(f"Missing features: {missing} — filling with 0.0")
        for col in missing:
            df[col] = 0.0
        available = feature_names

    df_clean = df.dropna(subset=available)
    if df_clean.empty:
        raise ValueError(f"No complete data rows for prediction on {ticker}")

    latest = df_clean.iloc[-1]
    feature_vector = latest[feature_names].values.reshape(1, -1)
    raw_dict = {name: float(latest[name]) for name in feature_names if name in latest.index}

    # Step 5: Probabilities & Decision with Abstention
    raw_probs = model.predict_proba(feature_vector)[0]
    raw_prob_up = float(raw_probs[1])

    if calibrator is not None:
        try:
            calibrated_prob_up = float(calibrator.predict_calibrated_proba(model, feature_vector)[0])
            is_calibrated = True
        except Exception as e:
            logger.warning(f"Calibrator prediction failed ({e}); using raw probability.")
            calibrated_prob_up = raw_prob_up
            is_calibrated = False
    else:
        calibrated_prob_up = raw_prob_up
        is_calibrated = False

    cal_engine = ProbabilityCalibrator(confidence_threshold=confidence_threshold)
    signal, final_confidence = cal_engine.decide_signal_with_abstention(
        raw_prob_up=raw_prob_up,
        calibrated_prob_up=calibrated_prob_up,
        threshold=confidence_threshold,
    )

    # Raw confidence for tracking
    raw_confidence = max(raw_prob_up, 1.0 - raw_prob_up)

    # Step 6: SHAP Local Feature Attribution
    shap_explainer = SHAPExplainer(model, feature_names)
    shap_result = shap_explainer.explain_instance(
        feature_vector=feature_vector,
        feature_values_dict=raw_dict,
        top_k=5,
    )

    prediction_date = latest["date"] if "date" in latest.index else date.today()

    result = {
        "ticker": ticker,
        "signal": signal,
        "confidence": round(final_confidence, 4),
        "raw_confidence": round(raw_confidence, 4),
        "calibrated_confidence": round(calibrated_prob_up if signal == "UP" else (1 - calibrated_prob_up), 4),
        "is_calibrated": is_calibrated,
        "confidence_threshold": confidence_threshold,
        "top_features": shap_result["top_features"],
        "shap_values": shap_result["all_shap_values"],
        "base_value": shap_result["base_value"],
        "date": str(prediction_date),
        "model_version": model_version,
    }

    logger.info(
        f"Prediction for {ticker}: {signal} (confidence: {final_confidence:.2%}, "
        f"calibrated: {is_calibrated}, SHAP top: {shap_result['top_features'][0]['name']})"
    )

    if save_to_db:
        _save_prediction(result)

    return result


def _save_prediction(result: dict) -> None:
    """Store prediction with SHAP and calibration data in MySQL."""
    db: Session = SessionLocal()
    try:
        existing = db.query(Prediction).filter(
            Prediction.ticker == result["ticker"],
            Prediction.date == result["date"],
            Prediction.model_version == result["model_version"],
        ).first()

        if existing:
            existing.signal_dir = result["signal"]
            existing.confidence = result["confidence"]
            existing.raw_confidence = result.get("raw_confidence")
            existing.calibrated_confidence = result.get("calibrated_confidence")
            existing.is_calibrated = 1 if result.get("is_calibrated") else 0
            existing.features_json = result["top_features"]
            existing.shap_values_json = result.get("shap_values")
        else:
            pred = Prediction(
                ticker=result["ticker"],
                date=result["date"],
                model_version=result["model_version"],
                signal_dir=result["signal"],
                confidence=result["confidence"],
                raw_confidence=result.get("raw_confidence"),
                calibrated_confidence=result.get("calibrated_confidence"),
                is_calibrated=1 if result.get("is_calibrated") else 0,
                features_json=result["top_features"],
                shap_values_json=result.get("shap_values"),
            )
            db.add(pred)

        db.commit()
        logger.info(f"Prediction saved to DB for {result['ticker']}")
    except Exception as e:
        logger.error(f"Error saving prediction: {e}")
        db.rollback()
    finally:
        db.close()
