"""
train_baseline.py — XGBoost Baseline Model Training
======================================================
Trains an XGBoost classifier on price + technical features only.
Incorporates:
  - Chronological time-series validation
  - Probability calibration (Platt/Sigmoid scaling)
  - SHAP TreeExplainer for local & global interpretability
  - Naive majority-class & simple regression baselines
  - Full experiment tracking and artifact persistence
"""

import logging
import os
from typing import Optional

import joblib
import numpy as np
from xgboost import XGBClassifier

from app.config import TICKERS
from app.features.builder import build_feature_dataframe, build_multi_ticker_matrix
from app.ml.calibration import ProbabilityCalibrator
from app.ml.evaluate import evaluate_model, save_metrics
from app.ml.shap_explainer import SHAPExplainer
from app.ml.validation import WalkForwardValidator

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "trained_models"
)


def train_baseline(
    ticker: Optional[str] = None,
    model_version: str = "baseline_v1",
    run_walk_forward: bool = False,
    confidence_threshold: float = 0.55,
) -> tuple:
    """
    Train the XGBoost baseline model on price + technical features.

    Args:
        ticker: Single ticker or None for multi-ticker pooled model.
        model_version: Identifier for saved artifact.
        run_walk_forward: If True, executes 5-fold expanding walk-forward validation.
        confidence_threshold: Threshold for abstention / conviction.

    Returns:
        Tuple of (trained_model, metrics_dict).
    """
    logger.info(f"Training baseline model: {model_version} (ticker: {ticker or 'ALL'})")

    dataset_period = {}
    if ticker:
        df_clean, feature_names = build_feature_dataframe(ticker, include_sentiment=False)
        dataset_period["dataset_start"] = df_clean["date"].iloc[0]
        dataset_period["dataset_end"] = df_clean["date"].iloc[-1]

        # 80/20 chronological split
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
            TICKERS, include_sentiment=False
        )
        dataset_period["train_samples"] = len(X_train)
        dataset_period["test_samples"] = len(X_test)

    # Class balance adjustment
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

    # Fit probability calibration on training/validation split
    calibrator = ProbabilityCalibrator(
        method="sigmoid", confidence_threshold=confidence_threshold
    )
    # Split train fold 80/20 for calibration fitting to prevent target leak
    cal_split = int(len(X_train) * 0.8)
    if cal_split > 30:
        base_for_cal = XGBClassifier(**params)
        base_for_cal.fit(X_train[:cal_split], y_train[:cal_split], verbose=False)
        calibrator.fit_calibrator(base_for_cal, X_train[cal_split:], y_train[cal_split:])
    else:
        calibrator.fit_calibrator(model, X_test, y_test)

    # Initialize SHAP explainer
    explainer = SHAPExplainer(model, feature_names)

    # Optional Walk-Forward Validation
    wf_results = []
    if run_walk_forward and ticker:
        logger.info("Executing 5-fold expanding walk-forward cross-validation...")
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

    # Final holdout evaluation
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

    # Save model artifact
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

    # Persist to database
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
