"""
train_sentiment.py — XGBoost Model with Sentiment Features
=============================================================
Retrains the XGBoost classifier with FinBERT daily sentiment scores
added to price + technical indicators.
Incorporates:
  - Strict alignment with baseline dataset to ensure identical test periods
  - Probability calibration and Brier score tracking
  - SHAP TreeExplainer to compare technical vs. sentiment feature importance
  - Naive majority-class and regression baselines
  - Persists full experiment metadata
"""

import logging
import os
from typing import Optional

import joblib
import numpy as np
from xgboost import XGBClassifier

from app.config import TICKERS
from app.features.builder import build_feature_dataframe, build_multi_ticker_matrix, build_aligned_paired_matrices
from app.ml.calibration import ProbabilityCalibrator
from app.ml.evaluate import evaluate_model, save_metrics, compare_models
from app.ml.shap_explainer import SHAPExplainer
from app.ml.validation import WalkForwardValidator

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "trained_models"
)


def train_sentiment(
    ticker: Optional[str] = None,
    model_version: str = "sentiment_v1",
    run_walk_forward: bool = False,
    confidence_threshold: float = 0.55,
) -> tuple:
    """
    Train XGBoost model with price + technical + sentiment features.

    Args:
        ticker: Single ticker or None for all tickers.
        model_version: Version identifier.
        run_walk_forward: Whether to run walk-forward validation across folds.
        confidence_threshold: Threshold for abstention / conviction.

    Returns:
        Tuple of (trained_model, metrics_dict).
    """
    logger.info(f"Training sentiment-augmented model: {model_version} (ticker: {ticker or 'ALL'})")

    dataset_period = {}
    if ticker:
        df_clean, feature_names = build_feature_dataframe(ticker, include_sentiment=True)
        dataset_period["dataset_start"] = df_clean["date"].iloc[0]
        dataset_period["dataset_end"] = df_clean["date"].iloc[-1]

        split_idx = int(len(df_clean) * 0.8)
        train_df = df_clean.iloc[:split_idx]
        test_df = df_clean.iloc[split_idx:]

        X_train = train_df[feature_names].values
        y_train = train_df["target"].values
        X_test = test_df[feature_names].values
        y_test = test_df["target"].values

        dataset_period["test_start"] = test_df["date"].iloc[0]
        dataset_period["test_end"] = test_df["date"].iloc[-1]
        dataset_period["train_samples"] = len(train_df)
        dataset_period["test_samples"] = len(test_df)
    else:
        X_train, X_test, y_train, y_test, feature_names = build_multi_ticker_matrix(
            TICKERS, include_sentiment=True
        )
        dataset_period["train_samples"] = len(X_train)
        dataset_period["test_samples"] = len(X_test)

    n_pos = int(np.sum(y_train == 1))
    n_neg = int(len(y_train) - n_pos)
    scale_weight = float(n_neg / max(n_pos, 1))

    params = {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": scale_weight,
        "random_state": 42,
        "eval_metric": "logloss",
    }

    model = XGBClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Probability calibrator
    calibrator = ProbabilityCalibrator(
        method="sigmoid", confidence_threshold=confidence_threshold
    )
    cal_split = int(len(X_train) * 0.8)
    if cal_split > 30:
        base_for_cal = XGBClassifier(**params)
        base_for_cal.fit(X_train[:cal_split], y_train[:cal_split], verbose=False)
        calibrator.fit_calibrator(base_for_cal, X_train[cal_split:], y_train[cal_split:])
    else:
        calibrator.fit_calibrator(model, X_test, y_test)

    explainer = SHAPExplainer(model, feature_names)

    # Optional walk-forward validation
    wf_results = []
    if run_walk_forward and ticker:
        logger.info("Executing 5-fold expanding walk-forward cross-validation with sentiment...")
        validator = WalkForwardValidator(n_splits=5, min_train_ratio=0.5, embargo_days=1)
        for fold in validator.split(df_clean):
            X_tr = df_clean.iloc[fold.train_indices][feature_names].values
            y_tr = df_clean.iloc[fold.train_indices]["target"].values
            X_te = df_clean.iloc[fold.test_indices][feature_names].values
            y_te = df_clean.iloc[fold.test_indices]["target"].values

            fold_model = XGBClassifier(**params)
            fold_model.fit(X_tr, y_tr, verbose=False)
            fold_metrics = evaluate_model(fold_model, X_te, y_te, X_train=X_tr, y_train=y_tr)
            wf_results.append({
                "fold": fold.fold_index,
                "train_dates": f"{fold.train_start_date} to {fold.train_end_date}",
                "test_dates": f"{fold.test_start_date} to {fold.test_end_date}",
                "accuracy": fold_metrics["accuracy"],
                "f1": fold_metrics["f1"],
                "roc_auc": fold_metrics["roc_auc"],
                "majority_baseline": fold_metrics["majority_baseline_accuracy"],
            })

    metrics = evaluate_model(
        model=model,
        X_test=X_test,
        y_test=y_test,
        calibrator=calibrator,
        X_train=X_train,
        y_train=y_train,
        feature_names=feature_names,
        explainer=explainer,
    )
    if wf_results:
        metrics["walk_forward_folds"] = wf_results

    os.makedirs(MODELS_DIR, exist_ok=True)
    model_path = os.path.join(MODELS_DIR, f"{model_version}.joblib")
    artifact_data = {
        "model": model,
        "calibrator": calibrator,
        "feature_names": feature_names,
        "parameters": params,
        "metrics": metrics,
        "dataset_period": dataset_period,
    }
    joblib.dump(artifact_data, model_path)
    logger.info(f"Model artifact saved to {model_path}")

    save_metrics(
        metrics=metrics,
        model_version=model_version,
        ticker=ticker,
        dataset_period=dataset_period,
        feature_names=feature_names,
        parameters=params,
        artifact_path=model_path,
        validation_type="walk_forward" if run_walk_forward else "chronological_holdout",
    )

    return model, metrics


def train_and_compare_models(ticker: str) -> dict:
    """
    Train baseline and sentiment models on the EXACT same dataset and identical test periods.
    Returns side-by-side comparison.
    """
    logger.info(f"Running synchronized paired training and comparison on {ticker}...")
    paired = build_aligned_paired_matrices(ticker, test_ratio=0.2)

    params = {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "logloss",
    }

    y_tr = paired["y_train"]
    y_te = paired["y_test"]
    n_pos = int(np.sum(y_tr == 1))
    scale_weight = float((len(y_tr) - n_pos) / max(n_pos, 1))
    params["scale_pos_weight"] = scale_weight

    # 1. Train Baseline
    model_base = XGBClassifier(**params)
    model_base.fit(paired["X_train_base"], y_tr, verbose=False)
    cal_base = ProbabilityCalibrator(method="sigmoid").fit_calibrator(
        model_base, paired["X_test_base"], y_te
    )
    metrics_base = evaluate_model(
        model=model_base,
        X_test=paired["X_test_base"],
        y_test=y_te,
        calibrator=cal_base,
        X_train=paired["X_train_base"],
        y_train=y_tr,
        feature_names=paired["baseline_features"],
    )

    # 2. Train Sentiment
    model_sent = XGBClassifier(**params)
    model_sent.fit(paired["X_train_sent"], y_tr, verbose=False)
    cal_sent = ProbabilityCalibrator(method="sigmoid").fit_calibrator(
        model_sent, paired["X_test_sent"], y_te
    )
    metrics_sent = evaluate_model(
        model=model_sent,
        X_test=paired["X_test_sent"],
        y_test=y_te,
        calibrator=cal_sent,
        X_train=paired["X_train_sent"],
        y_train=y_tr,
        feature_names=paired["sentiment_features"],
    )

    # Save artifacts
    joblib.dump(
        {"model": model_base, "calibrator": cal_base, "feature_names": paired["baseline_features"]},
        os.path.join(MODELS_DIR, "baseline_v1.joblib"),
    )
    joblib.dump(
        {"model": model_sent, "calibrator": cal_sent, "feature_names": paired["sentiment_features"]},
        os.path.join(MODELS_DIR, "sentiment_v1.joblib"),
    )

    period = {
        "dataset_start": paired["train_dates"][0],
        "dataset_end": paired["test_dates"][-1],
        "test_start": paired["test_dates"][0],
        "test_end": paired["test_dates"][-1],
        "train_samples": len(y_tr),
        "test_samples": len(y_te),
    }

    save_metrics(metrics_base, "baseline_v1", ticker=ticker, dataset_period=period, feature_names=paired["baseline_features"])
    save_metrics(metrics_sent, "sentiment_v1", ticker=ticker, dataset_period=period, feature_names=paired["sentiment_features"])

    return compare_models("baseline_v1", "sentiment_v1")
