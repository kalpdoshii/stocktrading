"""
calibration.py — Probability Calibration & Low-Confidence Abstention
===================================================================
Enforces reliable probability estimation for trading signals:
  - Calibrates tree model outputs using Sigmoid (Platt) or Isotonic scaling
  - Evaluates Brier score loss and Expected Calibration Error (ECE)
  - Computes points for reliability diagrams (Calibration Curves)
  - Implements configurable low-confidence abstention:
      When conviction is low (e.g. calibrated P between 0.45 and 0.55),
      the model abstains by issuing a 'HOLD' signal rather than forcing
      a low-confidence speculative trade.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import brier_score_loss

logger = logging.getLogger(__name__)


@dataclass
class CalibrationMetrics:
    brier_score: float
    expected_calibration_error: float
    prob_true: list[float]
    prob_pred: list[float]
    method: str
    is_calibrated: bool


class ProbabilityCalibrator:
    """
    Calibrates classifier probabilities and applies abstention thresholds.
    """

    def __init__(
        self,
        method: str = "sigmoid",
        confidence_threshold: float = 0.55,
        n_bins: int = 5,
    ):
        """
        Args:
            method: 'sigmoid' (Platt scaling) or 'isotonic' (non-parametric monotonic).
            confidence_threshold: Minimum calibrated confidence required to emit UP/DOWN.
                                  If calibrated prob is within [1 - threshold, threshold], signal is HOLD.
            n_bins: Number of bins for reliability diagram.
        """
        self.method = method
        self.confidence_threshold = confidence_threshold
        self.n_bins = n_bins
        self.calibrated_model: Optional[CalibratedClassifierCV] = None

    def fit_calibrator(self, base_estimator, X_val: np.ndarray, y_val: np.ndarray):
        """
        Fit calibrator using base estimator and cross-validation on validation/train data.
        """
        if len(np.unique(y_val)) < 2:
            logger.warning("Validation set has only one class; calibration skipped.")
            return self

        cv_splits = 3 if len(y_val) >= 30 else 2
        try:
            self.calibrated_model = CalibratedClassifierCV(
                estimator=base_estimator,
                method=self.method,
                cv=cv_splits,
            )
            self.calibrated_model.fit(X_val, y_val)
            logger.info(f"Fitted {self.method} probability calibrator on {len(X_val)} samples (cv={cv_splits}).")
        except Exception as e:
            logger.error(f"Error fitting calibrator: {e}. Falling back to uncalibrated base model.")
            self.calibrated_model = None

        return self

    def predict_calibrated_proba(self, base_estimator, X: np.ndarray) -> np.ndarray:
        """
        Predict calibrated probability of class 1 (UP).
        """
        if self.calibrated_model is not None:
            return self.calibrated_model.predict_proba(X)[:, 1]
        return base_estimator.predict_proba(X)[:, 1]

    def evaluate_calibration(
        self, y_true: np.ndarray, y_prob: np.ndarray
    ) -> CalibrationMetrics:
        """
        Compute Brier score, ECE, and reliability curve.
        """
        brier = float(brier_score_loss(y_true, y_prob))

        try:
            prob_true, prob_pred = calibration_curve(
                y_true, y_prob, n_bins=self.n_bins, strategy="uniform"
            )
            # Expected Calibration Error (ECE)
            bin_weights = np.histogram(y_prob, bins=self.n_bins, range=(0, 1))[0] / len(y_prob)
            ece = float(np.sum(bin_weights[:len(prob_true)] * np.abs(prob_true - prob_pred)))
            true_list = [round(float(p), 4) for p in prob_true]
            pred_list = [round(float(p), 4) for p in prob_pred]
        except Exception as e:
            logger.warning(f"Could not compute calibration curve: {e}")
            ece = 0.0
            true_list = []
            pred_list = []

        return CalibrationMetrics(
            brier_score=round(brier, 4),
            expected_calibration_error=round(ece, 4),
            prob_true=true_list,
            prob_pred=pred_list,
            method=self.method,
            is_calibrated=self.calibrated_model is not None,
        )

    def decide_signal_with_abstention(
        self,
        raw_prob_up: float,
        calibrated_prob_up: float,
        threshold: Optional[float] = None,
    ) -> Tuple[str, float]:
        """
        Determine trading signal with explicit low-confidence abstention.

        Returns:
            Tuple of (signal: 'UP' | 'DOWN' | 'HOLD', confidence: float)
        """
        tau = threshold if threshold is not None else self.confidence_threshold
        prob = calibrated_prob_up

        if prob >= tau:
            signal = "UP"
            confidence = prob
        elif prob <= (1.0 - tau):
            signal = "DOWN"
            confidence = 1.0 - prob
        else:
            signal = "HOLD"
            # In abstention, report max distance from uncertainty (0.5)
            confidence = max(prob, 1.0 - prob)

        return signal, round(float(confidence), 4)
