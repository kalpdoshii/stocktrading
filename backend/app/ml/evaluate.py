"""
evaluate.py — Model Evaluation Metrics
=========================================
Computes classification metrics and stores them in the model_metrics table.
Also provides comparison utilities for baseline vs. sentiment models.

Usage:
    from app.ml.evaluate import evaluate_model, save_metrics
    metrics = evaluate_model(model, X_test, y_test)
    save_metrics(metrics, model_version="baseline_v1", ticker="AAPL")
"""

import logging
from typing import Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
)
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ModelMetric

logger = logging.getLogger(__name__)


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    """
    Evaluate a trained model on test data.

    Args:
        model: Trained sklearn-compatible classifier (e.g. XGBClassifier).
        X_test: Test feature matrix.
        y_test: Test labels (0 or 1).

    Returns:
        dict with keys: accuracy, precision, recall, f1, roc_auc,
        classification_report, confusion_matrix.
    """
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]  # probability of class 1

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "report": classification_report(y_test, y_pred, target_names=["DOWN", "UP"]),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }

    # Print a nice summary
    logger.info("\n" + "=" * 50)
    logger.info("MODEL EVALUATION RESULTS")
    logger.info("=" * 50)
    logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
    logger.info(f"  Precision: {metrics['precision']:.4f}")
    logger.info(f"  Recall:    {metrics['recall']:.4f}")
    logger.info(f"  F1 Score:  {metrics['f1']:.4f}")
    logger.info(f"  ROC AUC:   {metrics['roc_auc']:.4f}")
    logger.info("\n" + metrics["report"])

    return metrics


def save_metrics(
    metrics: dict,
    model_version: str,
    ticker: Optional[str] = None,
) -> None:
    """
    Save evaluation metrics to the model_metrics table in MySQL.

    Args:
        metrics: dict from evaluate_model().
        model_version: e.g. "baseline_v1" or "sentiment_v1".
        ticker: Stock symbol, or None if metrics are for all tickers combined.
    """
    db: Session = SessionLocal()
    try:
        record = ModelMetric(
            model_version=model_version,
            ticker=ticker,
            accuracy=metrics["accuracy"],
            precision_score=metrics["precision"],
            recall_score=metrics["recall"],
            f1_score=metrics["f1"],
            roc_auc=metrics["roc_auc"],
        )
        db.add(record)
        db.commit()
        logger.info(
            f"Saved metrics for model '{model_version}' "
            f"(ticker: {ticker or 'ALL'}) to DB"
        )
    except Exception as e:
        logger.error(f"Error saving metrics: {e}")
        db.rollback()
    finally:
        db.close()


def compare_models(version_a: str, version_b: str) -> dict:
    """
    Load metrics for two model versions and return a comparison dict.

    Args:
        version_a: First model version (e.g. "baseline_v1")
        version_b: Second model version (e.g. "sentiment_v1")

    Returns:
        dict with side-by-side metrics and deltas.
    """
    db: Session = SessionLocal()
    try:
        metrics_a = (
            db.query(ModelMetric)
            .filter(ModelMetric.model_version == version_a)
            .order_by(ModelMetric.train_date.desc())
            .first()
        )
        metrics_b = (
            db.query(ModelMetric)
            .filter(ModelMetric.model_version == version_b)
            .order_by(ModelMetric.train_date.desc())
            .first()
        )

        if not metrics_a or not metrics_b:
            logger.warning("One or both model versions not found in DB")
            return {}

        comparison = {
            "models": [version_a, version_b],
            "accuracy": [metrics_a.accuracy, metrics_b.accuracy],
            "precision": [metrics_a.precision_score, metrics_b.precision_score],
            "recall": [metrics_a.recall_score, metrics_b.recall_score],
            "f1": [metrics_a.f1_score, metrics_b.f1_score],
            "roc_auc": [metrics_a.roc_auc, metrics_b.roc_auc],
            "deltas": {
                "accuracy": (metrics_b.accuracy or 0) - (metrics_a.accuracy or 0),
                "precision": (metrics_b.precision_score or 0) - (metrics_a.precision_score or 0),
                "recall": (metrics_b.recall_score or 0) - (metrics_a.recall_score or 0),
                "f1": (metrics_b.f1_score or 0) - (metrics_a.f1_score or 0),
                "roc_auc": (metrics_b.roc_auc or 0) - (metrics_a.roc_auc or 0),
            },
        }

        # Print comparison
        logger.info("\n" + "=" * 60)
        logger.info(f"MODEL COMPARISON: {version_a} vs {version_b}")
        logger.info("=" * 60)
        logger.info(f"{'Metric':<12} {version_a:<15} {version_b:<15} {'Delta':<10}")
        logger.info("-" * 52)
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
            a_val = comparison[metric][0] or 0
            b_val = comparison[metric][1] or 0
            delta = comparison["deltas"][metric]
            sign = "+" if delta >= 0 else ""
            logger.info(
                f"{metric:<12} {a_val:<15.4f} {b_val:<15.4f} {sign}{delta:.4f}"
            )

        return comparison

    finally:
        db.close()
