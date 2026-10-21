"""
validation.py — Chronological Walk-Forward Validation Engine
============================================================
Implements rigorous time-series cross-validation without look-ahead bias:
  - Expanding-window walk-forward validation (Train expands, Test shifts forward)
  - Rolling-window walk-forward validation (Fixed train window)
  - Strict chronological ordering — NO random shuffling
  - Embargo/purge period between train and test to prevent autocorrelation leakage
  - Automatic evaluation of baselines:
      1. Naive Majority-Class Baseline (zero-rule predictor)
      2. Simple Logistic Regression Baseline
      3. Main Model (XGBoost)
  - Full metrics suite: Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, Brier Score,
    Class Balance, and Confusion Matrix across all folds.
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Generator, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    precision_recall_curve,
    auc,
    brier_score_loss,
    confusion_matrix,
)
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class FoldSplit:
    fold_index: int
    train_indices: np.ndarray
    test_indices: np.ndarray
    train_start_date: Optional[date] = None
    train_end_date: Optional[date] = None
    test_start_date: Optional[date] = None
    test_end_date: Optional[date] = None


@dataclass
class ValidationSummary:
    validation_type: str
    n_folds: int
    model_name: str
    feature_names: list[str]
    dataset_start: str
    dataset_end: str
    test_start: str
    test_end: str
    total_samples: int
    train_samples_avg: float
    test_samples_total: int
    mean_accuracy: float
    std_accuracy: float
    mean_precision: float
    mean_recall: float
    mean_f1: float
    mean_roc_auc: float
    mean_pr_auc: float
    mean_brier_score: float
    majority_baseline_accuracy: float
    simple_baseline_accuracy: float
    class_balance: dict
    fold_metrics: list[dict] = field(default_factory=list)


class WalkForwardValidator:
    """
    Time-series cross-validator that respects temporal order and tests predictive reliability.
    """

    def __init__(
        self,
        n_splits: int = 5,
        min_train_ratio: float = 0.5,
        embargo_days: int = 1,
        mode: str = "expanding",
    ):
        """
        Args:
            n_splits: Number of walk-forward folds (default 5).
            min_train_ratio: Fraction of the dataset reserved for the initial train fold (default 0.50).
            embargo_days: Gap between train and test to prevent label overlap / autocorrelation leak (default 1).
            mode: 'expanding' (train size grows) or 'rolling' (fixed-size train window).
        """
        self.n_splits = n_splits
        self.min_train_ratio = min_train_ratio
        self.embargo_days = embargo_days
        self.mode = mode

    def split(
        self, df: pd.DataFrame, date_column: str = "date"
    ) -> Generator[FoldSplit, None, None]:
        """
        Generate chronological train/test index splits.
        """
        n = len(df)
        if n < 50:
            raise ValueError(f"Insufficient samples for walk-forward validation: {n} < 50")

        dates = df[date_column].values if date_column in df.columns else None

        min_train_size = int(n * self.min_train_ratio)
        remaining_samples = n - min_train_size - (self.n_splits * self.embargo_days)
        test_size = max(10, remaining_samples // self.n_splits)

        for fold in range(self.n_splits):
            if self.mode == "expanding":
                train_start = 0
                train_end = min_train_size + fold * test_size
            else:  # rolling
                train_start = fold * test_size
                train_end = min_train_size + fold * test_size

            test_start = train_end + self.embargo_days
            test_end = min(n, test_start + test_size)

            if test_start >= n:
                break

            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(test_start, test_end)

            split = FoldSplit(
                fold_index=fold + 1,
                train_indices=train_idx,
                test_indices=test_idx,
                train_start_date=dates[train_start] if dates is not None else None,
                train_end_date=dates[train_end - 1] if dates is not None else None,
                test_start_date=dates[test_start] if dates is not None else None,
                test_end_date=dates[test_end - 1] if dates is not None else None,
            )
            yield split


def compute_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    """
    Compute comprehensive binary classification metrics.
    """
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.5

    try:
        precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_prob)
        pr_auc = float(auc(recall_curve, precision_curve))
    except Exception:
        pr_auc = float(np.mean(y_true))

    try:
        brier = float(brier_score_loss(y_true, y_prob))
    except Exception:
        brier = 0.25

    cm = confusion_matrix(y_true, y_pred).tolist()

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": cm,
    }


def evaluate_baselines(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
) -> dict:
    """
    Fit and evaluate two essential baselines:
      1. Naive Majority Class (predicts the most frequent train label)
      2. Standard Logistic Regression (scaled strictly on train fold)
    """
    # 1. Majority class baseline
    pos_count = int(np.sum(y_train == 1))
    neg_count = int(np.sum(y_train == 0))
    majority_class = 1 if pos_count >= neg_count else 0
    majority_preds = np.full_like(y_test, fill_value=majority_class)
    majority_acc = float(accuracy_score(y_test, majority_preds))

    # 2. Simple Logistic Regression baseline
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    lr = LogisticRegression(max_iter=500, random_state=42)
    lr.fit(X_train_scaled, y_train)
    lr_preds = lr.predict(X_test_scaled)
    lr_probs = lr.predict_proba(X_test_scaled)[:, 1]

    lr_metrics = compute_classification_metrics(y_test, lr_preds, lr_probs)

    return {
        "majority_class": majority_class,
        "majority_accuracy": round(majority_acc, 4),
        "simple_baseline_accuracy": lr_metrics["accuracy"],
        "simple_baseline_f1": lr_metrics["f1"],
        "simple_baseline_roc_auc": lr_metrics["roc_auc"],
    }
