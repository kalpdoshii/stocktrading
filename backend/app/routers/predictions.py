"""
predictions.py — Prediction & Model Research API Endpoints
===========================================================
GET /api/predict/{ticker}          → latest calibrated prediction with SHAP
GET /api/predict-history/{ticker}  → recent prediction confidence history
GET /api/metrics/compare           → rigorous baseline vs. sentiment comparison
GET /api/ml/experiments            → historical experiment runs
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import TICKERS
from app.models import Prediction, ModelMetric, ExperimentRecord

router = APIRouter(tags=["Predictions"])


@router.get("/predict/{ticker}")
def get_prediction(
    ticker: str,
    threshold: float = 0.55,
    model_version: str = "sentiment_v1",
    force_refresh: bool = False,
    db: Session = Depends(get_db),
):
    """
    Get the latest prediction for a ticker.
    Supports probability calibration, low-confidence abstention ('HOLD'), and SHAP attributions.
    """
    ticker = ticker.upper()
    if ticker not in TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not configured")

    if not force_refresh:
        prediction = (
            db.query(Prediction)
            .filter(Prediction.ticker == ticker, Prediction.model_version == model_version)
            .order_by(Prediction.date.desc())
            .first()
        )

        if prediction:
            import json
            features = prediction.features_json
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except Exception:
                    pass

            shap_vals = prediction.shap_values_json
            if isinstance(shap_vals, str):
                try:
                    shap_vals = json.loads(shap_vals)
                except Exception:
                    pass

            return {
                "ticker": ticker,
                "date": str(prediction.date),
                "signal": prediction.signal_dir,
                "confidence": prediction.confidence,
                "raw_confidence": prediction.raw_confidence or prediction.confidence,
                "calibrated_confidence": prediction.calibrated_confidence or prediction.confidence,
                "is_calibrated": bool(prediction.is_calibrated),
                "model_version": prediction.model_version,
                "confidence_threshold": threshold,
                "top_features": features or [],
                "shap_values": shap_vals or {},
            }

    try:
        from app.ml.predict import predict_ticker
        result = predict_ticker(
            ticker, model_version=model_version, confidence_threshold=threshold, save_to_db=True
        )
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

    history = [
        {
            "date": str(prediction.date),
            "signal": prediction.signal_dir,
            "confidence": prediction.confidence,
            "raw_confidence": prediction.raw_confidence or prediction.confidence,
            "calibrated_confidence": prediction.calibrated_confidence or prediction.confidence,
            "is_calibrated": bool(prediction.is_calibrated),
        }
        for prediction in reversed(predictions)
    ]

    return {
        "ticker": ticker,
        "model_version": model_version,
        "history": history,
    }


@router.get("/metrics/compare")
def compare_metrics(db: Session = Depends(get_db)):
    """
    Get side-by-side comparison of baseline vs sentiment model metrics,
    including majority-class baselines, probability calibration (Brier score),
    class balance, and sample date alignment.
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

    def _to_dict(m: Optional[ModelMetric]):
        if not m:
            return None
        return {
            "model_version": m.model_version,
            "ticker": m.ticker,
            "accuracy": m.accuracy,
            "precision": m.precision_score,
            "recall": m.recall_score,
            "f1": m.f1_score,
            "roc_auc": m.roc_auc,
            "pr_auc": m.pr_auc,
            "brier_score": m.brier_score,
            "majority_baseline_accuracy": m.majority_baseline_accuracy,
            "simple_baseline_accuracy": m.simple_baseline_accuracy,
            "dataset_period": {
                "start": str(m.dataset_start) if m.dataset_start else None,
                "end": str(m.dataset_end) if m.dataset_end else None,
                "test_start": str(m.test_start) if m.test_start else None,
                "test_end": str(m.test_end) if m.test_end else None,
                "train_samples": m.train_samples,
                "test_samples": m.test_samples,
            },
            "class_balance": m.class_balance_json,
            "calibration": m.calibration_metrics_json,
            "top_shap_features": (m.feature_importances_json or [])[:5],
            "validation_type": m.validation_type,
            "train_date": str(m.train_date) if m.train_date else None,
        }

    base_dict = _to_dict(baseline)
    sent_dict = _to_dict(sentiment)

    deltas = {}
    if base_dict and sent_dict:
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "brier_score"]:
            b_val = base_dict.get(metric) or 0.0
            s_val = sent_dict.get(metric) or 0.0
            deltas[metric] = round(s_val - b_val, 4)

    return {
        "baseline": base_dict,
        "sentiment": sent_dict,
        "deltas": deltas,
    }


@router.get("/ml/experiments")
def list_experiments(limit: int = 20, db: Session = Depends(get_db)):
    """List historical machine learning experiments and artifact metadata."""
    records = (
        db.query(ExperimentRecord)
        .order_by(ExperimentRecord.created_at.desc())
        .limit(max(1, min(limit, 50)))
        .all()
    )
    items = []
    for r in records:
        items.append({
            "experiment_id": r.experiment_id,
            "model_version": r.model_version,
            "ticker": r.ticker,
            "validation_strategy": r.validation_strategy,
            "metrics": r.metrics_json,
            "baseline_metrics": r.baseline_metrics_json,
            "dataset_start": str(r.dataset_start) if r.dataset_start else None,
            "dataset_end": str(r.dataset_end) if r.dataset_end else None,
            "artifact_path": r.artifact_path,
            "created_at": str(r.created_at) if r.created_at else None,
        })
    return {"count": len(items), "experiments": items}
