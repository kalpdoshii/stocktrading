"""
predictions.py — Prediction API Endpoints
=============================================
GET /api/predict/{ticker}      → latest prediction for a ticker
GET /api/metrics/compare       → baseline vs sentiment model comparison
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import TICKERS
from app.models import Prediction, ModelMetric

router = APIRouter(tags=["Predictions"])


@router.get("/predict/{ticker}")
def get_prediction(ticker: str, db: Session = Depends(get_db)):
    """
    Get the latest prediction for a ticker.
    If no stored prediction exists, generate one on the fly.
    """
    ticker = ticker.upper()

    if ticker not in TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not configured")

    # Try to get stored prediction first
    prediction = (
        db.query(Prediction)
        .filter(Prediction.ticker == ticker)
        .order_by(Prediction.date.desc())
        .first()
    )

    if prediction:
        import json
        features = prediction.features_json
        if isinstance(features, str):
            features = json.loads(features)

        return {
            "ticker": ticker,
            "date": str(prediction.date),
            "signal": prediction.signal_dir,
            "confidence": prediction.confidence,
            "model_version": prediction.model_version,
            "top_features": features,
        }

    # If no stored prediction, try generating one
    try:
        from app.ml.predict import predict_ticker
        result = predict_ticker(ticker)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate prediction: {str(e)}"
        )


@router.get("/predict-history/{ticker}")
def get_prediction_history(
    ticker: str,
    model_version: str = "sentiment_v1",
    limit: int = 30,
    db: Session = Depends(get_db),
):
    """Return recent prediction signals and confidence values."""
    ticker = ticker.upper()
    if ticker not in TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not configured")

    predictions = (
        db.query(Prediction)
        .filter(
            Prediction.ticker == ticker,
            Prediction.model_version == model_version,
        )
        .order_by(Prediction.date.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )

    generated_prediction = None
    if not predictions:
        try:
            from app.ml.predict import predict_ticker
            generated_prediction = predict_ticker(ticker, model_version=model_version)
            predictions = (
                db.query(Prediction)
                .filter(
                    Prediction.ticker == ticker,
                    Prediction.model_version == model_version,
                )
                .order_by(Prediction.date.desc())
                .limit(max(1, min(limit, 100)))
                .all()
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not generate prediction: {e}")

    history = [
        {
            "date": str(prediction.date),
            "signal": prediction.signal_dir,
            "confidence": prediction.confidence,
        }
        for prediction in reversed(predictions)
    ]
    if not history and generated_prediction:
        history = [{
            "date": generated_prediction["date"],
            "signal": generated_prediction["signal"],
            "confidence": generated_prediction["confidence"],
        }]

    return {
        "ticker": ticker,
        "model_version": model_version,
        "history": history,
    }


@router.get("/metrics/compare")
def compare_metrics(db: Session = Depends(get_db)):
    """
    Get side-by-side comparison of baseline vs sentiment model metrics.
    Returns metrics for both models and the delta (improvement).
    """
    baseline = (
        db.query(ModelMetric)
        .filter(ModelMetric.model_version == "baseline_v1")
        .order_by(ModelMetric.train_date.desc())
        .first()
    )

    sentiment = (
        db.query(ModelMetric)
        .filter(ModelMetric.model_version == "sentiment_v1")
        .order_by(ModelMetric.train_date.desc())
        .first()
    )

    def _to_dict(m):
        if not m:
            return None
        return {
            "model_version": m.model_version,
            "accuracy": m.accuracy,
            "precision": m.precision_score,
            "recall": m.recall_score,
            "f1": m.f1_score,
            "roc_auc": m.roc_auc,
            "ticker": m.ticker,
            "train_date": str(m.train_date) if m.train_date else None,
        }

    result = {
        "baseline": _to_dict(baseline),
        "sentiment": _to_dict(sentiment),
    }

    # Compute deltas if both exist
    if baseline and sentiment:
        result["deltas"] = {
            "accuracy": (sentiment.accuracy or 0) - (baseline.accuracy or 0),
            "precision": (sentiment.precision_score or 0) - (baseline.precision_score or 0),
            "recall": (sentiment.recall_score or 0) - (baseline.recall_score or 0),
            "f1": (sentiment.f1_score or 0) - (baseline.f1_score or 0),
            "roc_auc": (sentiment.roc_auc or 0) - (baseline.roc_auc or 0),
        }

    return result
