"""
test_ml_validation.py — Unit Tests for Priority 1: Reliable Machine Learning
=============================================================================
Tests chronological walk-forward validation, zero look-ahead bias,
probability calibration, low-confidence abstention, SHAP attributions,
and naive baselines.
"""

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBClassifier

from app.ml.calibration import ProbabilityCalibrator
from app.ml.evaluate import evaluate_model
from app.ml.shap_explainer import SHAPExplainer
from app.ml.validation import (
    WalkForwardValidator,
    compute_classification_metrics,
    evaluate_baselines,
)


@pytest.fixture
def synthetic_time_series():
    """Generates synthetic price data for temporal validation testing."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    X = np.random.randn(n, 5)
    # Target depends on first feature with some noise
    prob = 1 / (1 + np.exp(-X[:, 0]))
    y = (prob > 0.5).astype(int)

    df = pd.DataFrame(X, columns=[f"feat_{i}" for i in range(5)])
    df["date"] = dates
    df["target"] = y
    return df, [f"feat_{i}" for i in range(5)]


def test_walk_forward_chronological_ordering(synthetic_time_series):
    """Ensure walk-forward validation has zero shuffling and train strictly precedes test."""
    df, feature_names = synthetic_time_series
    validator = WalkForwardValidator(n_splits=4, min_train_ratio=0.5, embargo_days=2)

    fold_count = 0
    for fold in validator.split(df):
        fold_count += 1
        # 1. Train indices strictly precede test indices
        assert np.max(fold.train_indices) < np.min(fold.test_indices)
        # 2. Embargo gap is enforced
        assert np.min(fold.test_indices) - np.max(fold.train_indices) > 1
        # 3. No index overlap
        overlap = set(fold.train_indices).intersection(set(fold.test_indices))
        assert len(overlap) == 0

    assert fold_count == 4


def test_walk_forward_expanding_vs_rolling(synthetic_time_series):
    """Verify expanding window increases train size while rolling maintains fixed window."""
    df, _ = synthetic_time_series
    expanding = WalkForwardValidator(n_splits=3, mode="expanding")
    rolling = WalkForwardValidator(n_splits=3, mode="rolling")

    exp_train_sizes = [len(f.train_indices) for f in expanding.split(df)]
    roll_train_sizes = [len(f.train_indices) for f in rolling.split(df)]

    # Expanding window train size strictly increases
    assert exp_train_sizes[1] > exp_train_sizes[0]
    assert exp_train_sizes[2] > exp_train_sizes[1]

    # Rolling window train size stays constant
    assert roll_train_sizes[0] == roll_train_sizes[1] == roll_train_sizes[2]


def test_baselines_evaluation():
    """Verify naive majority baseline and logistic regression baseline."""
    np.random.seed(42)
    # Imbalanced training data: 80% positive (class 1)
    y_train = np.array([1] * 80 + [0] * 20)
    X_train = np.random.randn(100, 3)

    # Test data: 60% positive
    y_test = np.array([1] * 60 + [0] * 40)
    X_test = np.random.randn(100, 3)

    results = evaluate_baselines(X_train, y_train, X_test, y_test)

    # Majority class must be 1, and its accuracy on test set must be exactly 0.60
    assert results["majority_class"] == 1
    assert results["majority_accuracy"] == 0.60
    assert "simple_baseline_accuracy" in results
    assert 0.0 <= results["simple_baseline_accuracy"] <= 1.0


def test_probability_calibration_and_abstention():
    """Verify calibration metrics and low-confidence abstention state."""
    calibrator = ProbabilityCalibrator(confidence_threshold=0.60)

    # Test 1: High conviction UP
    sig, conf = calibrator.decide_signal_with_abstention(raw_prob_up=0.75, calibrated_prob_up=0.72)
    assert sig == "UP"
    assert conf >= 0.60

    # Test 2: High conviction DOWN
    sig, conf = calibrator.decide_signal_with_abstention(raw_prob_up=0.20, calibrated_prob_up=0.25)
    assert sig == "DOWN"
    assert conf >= 0.60

    # Test 3: Low conviction -> ABSTAIN / HOLD
    sig, conf = calibrator.decide_signal_with_abstention(raw_prob_up=0.52, calibrated_prob_up=0.53)
    assert sig == "HOLD"

    # Calibration diagnostics
    y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0])
    y_prob = np.array([0.9, 0.1, 0.8, 0.7, 0.2, 0.3, 0.85, 0.15])
    diag = calibrator.evaluate_calibration(y_true, y_prob)
    assert diag.brier_score < 0.15  # Well-calibrated probabilities have low Brier score


def test_shap_explainer_attribution():
    """Verify that SHAP TreeExplainer produces exact local attributions and directions."""
    np.random.seed(42)
    X = np.random.randn(100, 4)
    # Feature 0 strongly drives class 1
    y = (X[:, 0] > 0).astype(int)
    feature_names = ["momentum", "rsi", "volatility", "sentiment"]

    model = XGBClassifier(n_estimators=15, max_depth=3, random_state=42)
    model.fit(X, y)

    explainer = SHAPExplainer(model, feature_names)

    # Explain an instance with high momentum
    high_mom_sample = np.array([[2.5, 0.1, -0.5, 0.8]])
    explanation = explainer.explain_instance(high_mom_sample, top_k=3)

    assert "base_value" in explanation
    assert len(explanation["top_features"]) == 3
    # Top feature should be momentum because of ground truth data generation
    assert explanation["top_features"][0]["name"] == "momentum"
    assert explanation["top_features"][0]["direction"] == "BULLISH"
    assert explanation["top_features"][0]["shap_value"] > 0

    # Global importance
    global_imp = explainer.compute_global_importance(X)
    assert len(global_imp) == 4
    assert global_imp[0]["feature"] == "momentum"
