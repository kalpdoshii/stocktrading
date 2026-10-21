"""
evaluate.py — Comprehensive Model Evaluation & Benchmark Engine
===============================================================
Computes classification metrics, probability calibration diagnostics,
baseline comparisons, and stores experiment records in MySQL:
  - Accuracy, Precision, Recall, F1-Score, ROC-AUC, PR-AUC
  - Brier Score & Expected Calibration Error (ECE)
  - Majority-Class (Zero-Rule) Baseline
  - Simple Logistic Regression Baseline
  - Class Balance analysis (Train vs. Test distributions)
  - Global SHAP feature importances
  - Persists metrics to model_metrics and experiment_records tables
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    auc,
    brier_score_loss,
    classification_report,
    confusion_matrix,
)
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ModelMetric, ExperimentRecord

logger = logging.getLogger(__name__)


def evaluate_model(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    calibrator: Optional[Any] = None,
    X_train: Optional[np.ndarray] = None,
    y_train: Optional[np.ndarray] = None,
    feature_names: Optional[List[str]] = None,
    explainer: Optional[Any] = None,
) -> dict:
    """
    Evaluate a trained model on test data with calibration, baselines, and SHAP.

    Returns:
        Dictionary containing all evaluation metrics, calibration diagnostics,
        and baseline comparisons.
    """
    # Raw probabilities
    raw_proba = model.predict_proba(X_test)[:, 1]

    # Calibrated probabilities if calibrator available
    if calibrator is not None:
        y_proba = calibrator.predict_calibrated_proba(model, X_test)
        is_calibrated = True
    else:
        y_proba = raw_proba
        is_calibrated = False

    y_pred = (y_proba >= 0.5).astype(int)

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1_val = float(f1_score(y_test, y_pred, zero_division=0))

    try:
        roc_auc = float(roc_auc_score(y_test, y_proba))
    except Exception:
        roc_auc = 0.5

    try:
        precision_curve, recall_curve, _ = precision_recall_curve(y_test, y_proba)
        pr_auc = float(auc(recall_curve, precision_curve))
    except Exception:
        pr_auc = float(np.mean(y_test))

    brier = float(brier_score_loss(y_test, y_proba))

    # Baselines
    majority_acc = None
    simple_acc = None
    if y_train is not None and X_train is not None:
        from app.ml.validation import evaluate_baselines
        base_results = evaluate_baselines(X_train, y_train, X_test, y_test)
        majority_acc = base_results["majority_accuracy"]
        simple_acc = base_results["simple_baseline_accuracy"]
    else:
        # Fallback to test majority class
        pos = int(np.sum(y_test == 1))
        neg = int(np.sum(y_test == 0))
        majority_acc = round(max(pos, neg) / len(y_test), 4)

    # Class balance
    test_pos = int(np.sum(y_test == 1))
    test_neg = int(np.sum(y_test == 0))
    class_balance = {
        "test": {
            "up_count": test_pos,
            "down_count": test_neg,
            "up_ratio": round(test_pos / len(y_test), 4) if len(y_test) else 0.0,
        }
    }
    if y_train is not None:
        tr_pos = int(np.sum(y_train == 1))
        tr_neg = int(np.sum(y_train == 0))
        class_balance["train"] = {
            "up_count": tr_pos,
            "down_count": tr_neg,
            "up_ratio": round(tr_pos / len(y_train), 4) if len(y_train) else 0.0,
        }

    # Calibration metrics
    calibration_info = {}
    if calibrator is not None:
        calib_diag = calibrator.evaluate_calibration(y_test, y_proba)
        calibration_info = {
            "brier_score": calib_diag.brier_score,
            "expected_calibration_error": calib_diag.expected_calibration_error,
            "prob_true": calib_diag.prob_true,
            "prob_pred": calib_diag.prob_pred,
            "method": calib_diag.method,
            "is_calibrated": True,
        }
    else:
        calibration_info = {
            "brier_score": round(brier, 4),
            "is_calibrated": False,
        }

    # SHAP global feature importances
    global_shap = []
    if explainer is not None:
        try:
            global_shap = explainer.compute_global_importance(X_test)
        except Exception as e:
            logger.warning(f"Could not compute SHAP global importance: {e}")

    metrics = {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1_val, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "majority_baseline_accuracy": majority_acc,
        "simple_baseline_accuracy": simple_acc,
        "class_balance": class_balance,
        "calibration": calibration_info,
        "global_shap": global_shap,
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "report": classification_report(y_test, y_pred, target_names=["DOWN", "UP"]),
    }

    logger.info("\n" + "=" * 55)
    logger.info("MODEL EVALUATION RESULTS")
    logger.info("=" * 55)
    maj_str = f"{majority_acc:.4f}" if majority_acc is not None else "N/A"
    sim_str = f"{simple_acc:.4f}" if simple_acc is not None else "N/A"
    logger.info(f"  Accuracy:                   {metrics['accuracy']:.4f}")
    logger.info(f"  Naive Majority Baseline:    {maj_str}")
    logger.info(f"  Logistic Regr Baseline:     {sim_str}")
    logger.info(f"  Precision:                  {metrics['precision']:.4f}")
    logger.info(f"  Recall:                     {metrics['recall']:.4f}")
    logger.info(f"  F1 Score:                   {metrics['f1']:.4f}")
    logger.info(f"  ROC AUC:                    {metrics['roc_auc']:.4f}")
    logger.info(f"  PR AUC:                     {metrics['pr_auc']:.4f}")
    logger.info(f"  Brier Score (Calibration):  {metrics['brier_score']:.4f}")
    logger.info("\n" + metrics["report"])

    return metrics


def save_metrics(
    metrics: dict,
    model_version: str,
    ticker: Optional[str] = None,
    dataset_period: Optional[dict] = None,
    feature_names: Optional[List[str]] = None,
    parameters: Optional[dict] = None,
    artifact_path: Optional[str] = None,
    validation_type: str = "walk_forward_cv",
) -> None:
    """
    Save evaluation metrics to model_metrics and log an experiment record.
    """
    db: Session = SessionLocal()
    try:
        ds_period = dataset_period or {}
        record = ModelMetric(
            model_version=model_version,
            ticker=ticker,
            accuracy=metrics.get("accuracy"),
            precision_score=metrics.get("precision"),
            recall_score=metrics.get("recall"),
            f1_score=metrics.get("f1"),
            roc_auc=metrics.get("roc_auc"),
            dataset_start=ds_period.get("dataset_start"),
            dataset_end=ds_period.get("dataset_end"),
            test_start=ds_period.get("test_start"),
            test_end=ds_period.get("test_end"),
            train_samples=ds_period.get("train_samples"),
            test_samples=ds_period.get("test_samples"),
            majority_baseline_accuracy=metrics.get("majority_baseline_accuracy"),
            simple_baseline_accuracy=metrics.get("simple_baseline_accuracy"),
            brier_score=metrics.get("brier_score"),
            pr_auc=metrics.get("pr_auc"),
            class_balance_json=metrics.get("class_balance"),
            calibration_metrics_json=metrics.get("calibration"),
            feature_importances_json=metrics.get("global_shap"),
            validation_type=validation_type,
        )
        db.add(record)

        # Log to experiment_records table
        exp_id = f"exp_{model_version}_{ticker or 'ALL'}_{uuid.uuid4().hex[:8]}"
        exp_record = ExperimentRecord(
            experiment_id=exp_id,
            model_name="XGBoost",
            model_version=model_version,
            ticker=ticker,
            validation_strategy=validation_type,
            dataset_start=ds_period.get("dataset_start"),
            dataset_end=ds_period.get("dataset_end"),
            parameters_json=parameters or {},
            feature_names_json=feature_names or [],
            metrics_json={
                "accuracy": metrics.get("accuracy"),
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1": metrics.get("f1"),
                "roc_auc": metrics.get("roc_auc"),
                "pr_auc": metrics.get("pr_auc"),
                "brier_score": metrics.get("brier_score"),
            },
            baseline_metrics_json={
                "majority_baseline_accuracy": metrics.get("majority_baseline_accuracy"),
                "simple_baseline_accuracy": metrics.get("simple_baseline_accuracy"),
            },
            artifact_path=artifact_path,
        )
        db.add(exp_record)
        db.commit()
        logger.info(f"Saved metrics & experiment record ({exp_id}) for '{model_version}'")

    except Exception as e:
        logger.error(f"Error saving metrics: {e}")
        db.rollback()
    finally:
        db.close()


def compare_models(version_a: str, version_b: str) -> dict:
    """
    Load metrics for two model versions and return a comprehensive comparison.
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

        def _get(obj, attr, default=0.0):
            val = getattr(obj, attr, None)
            return val if val is not None else default

        comparison = {
            "models": [version_a, version_b],
            "dataset_period": {
                version_a: {
                    "start": str(metrics_a.test_start) if metrics_a.test_start else None,
                    "end": str(metrics_a.test_end) if metrics_a.test_end else None,
                    "samples": metrics_a.test_samples,
                },
                version_b: {
                    "start": str(metrics_b.test_start) if metrics_b.test_start else None,
                    "end": str(metrics_b.test_end) if metrics_b.test_end else None,
                    "samples": metrics_b.test_samples,
                },
            },
            "accuracy": [_get(metrics_a, "accuracy"), _get(metrics_b, "accuracy")],
            "majority_baseline": [
                _get(metrics_a, "majority_baseline_accuracy"),
                _get(metrics_b, "majority_baseline_accuracy"),
            ],
            "simple_baseline": [
                _get(metrics_a, "simple_baseline_accuracy"),
                _get(metrics_b, "simple_baseline_accuracy"),
            ],
            "precision": [_get(metrics_a, "precision_score"), _get(metrics_b, "precision_score")],
            "recall": [_get(metrics_a, "recall_score"), _get(metrics_b, "recall_score")],
            "f1": [_get(metrics_a, "f1_score"), _get(metrics_b, "f1_score")],
            "roc_auc": [_get(metrics_a, "roc_auc"), _get(metrics_b, "roc_auc")],
            "pr_auc": [_get(metrics_a, "pr_auc"), _get(metrics_b, "pr_auc")],
            "brier_score": [_get(metrics_a, "brier_score"), _get(metrics_b, "brier_score")],
            "deltas": {
                "accuracy": _get(metrics_b, "accuracy") - _get(metrics_a, "accuracy"),
                "precision": _get(metrics_b, "precision_score") - _get(metrics_a, "precision_score"),
                "recall": _get(metrics_b, "recall_score") - _get(metrics_a, "recall_score"),
                "f1": _get(metrics_b, "f1_score") - _get(metrics_a, "f1_score"),
                "roc_auc": _get(metrics_b, "roc_auc") - _get(metrics_a, "roc_auc"),
                "pr_auc": _get(metrics_b, "pr_auc") - _get(metrics_a, "pr_auc"),
                "brier_score": _get(metrics_b, "brier_score") - _get(metrics_a, "brier_score"),
            },
            "class_balance": {
                version_a: metrics_a.class_balance_json,
                version_b: metrics_b.class_balance_json,
            },
            "calibration": {
                version_a: metrics_a.calibration_metrics_json,
                version_b: metrics_b.calibration_metrics_json,
            },
            "top_shap_features": {
                version_a: (metrics_a.feature_importances_json or [])[:5],
                version_b: (metrics_b.feature_importances_json or [])[:5],
            },
        }

        logger.info("\n" + "=" * 65)
        logger.info(f"MODEL COMPARISON: {version_a} vs {version_b}")
        logger.info("=" * 65)
        logger.info(f"{'Metric':<20} {version_a:<15} {version_b:<15} {'Delta':<10}")
        logger.info("-" * 62)
        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "brier_score"]:
            a_val = comparison[metric][0]
            b_val = comparison[metric][1]
            delta = comparison["deltas"][metric]
            sign = "+" if delta >= 0 else ""
            logger.info(f"{metric:<20} {a_val:<15.4f} {b_val:<15.4f} {sign}{delta:.4f}")

        return comparison

    finally:
        db.close()
