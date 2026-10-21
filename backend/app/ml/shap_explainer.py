"""
shap_explainer.py — SHAP-based Model Interpretability
======================================================
Computes mathematically sound feature attributions using SHAP TreeExplainer:
  - Local explanation: Exact Shapley attribution for an individual prediction
    (direction and magnitude of each feature pushing toward UP or DOWN).
  - Global importance: Mean absolute SHAP values across an evaluation sample,
    identifying which features truly drive model decisions.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import shap

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """
    Computes local and global explanations for tree models using shap.TreeExplainer.
    """

    def __init__(self, model: Any, feature_names: List[str]):
        """
        Args:
            model: Trained tree-based model (e.g. XGBClassifier).
            feature_names: Names corresponding to columns in feature vectors.
        """
        self.model = model
        self.feature_names = feature_names
        try:
            self.explainer = shap.TreeExplainer(model)
            logger.info("Initialized shap.TreeExplainer successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize TreeExplainer: {e}. Falling back to default Explainer.")
            self.explainer = shap.Explainer(model)

    def explain_instance(
        self,
        feature_vector: np.ndarray,
        feature_values_dict: Optional[Dict[str, float]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Compute local SHAP explanation for a single prediction.

        Args:
            feature_vector: 1D array of shape (n_features,) or 2D (1, n_features).
            feature_values_dict: Optional map of feature name -> raw unscaled value.
            top_k: Number of top driving features to return.

        Returns:
            Dict containing base_value, list of top contributing features with SHAP impact.
        """
        vec = np.asarray(feature_vector).reshape(1, -1)
        shap_values = self.explainer.shap_values(vec)

        # In binary classification, some SHAP versions return list [neg, pos] or 2D array
        if isinstance(shap_values, list) and len(shap_values) == 2:
            values = shap_values[1][0]
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            values = shap_values[0, :, 1]
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 2:
            values = shap_values[0]
        else:
            values = np.asarray(shap_values).flatten()

        expected_value = self.explainer.expected_value
        if isinstance(expected_value, (list, np.ndarray)) and len(expected_value) > 1:
            base_val = float(expected_value[1])
        elif isinstance(expected_value, (float, int, np.floating)):
            base_val = float(expected_value)
        else:
            base_val = 0.0

        # Sort features by absolute impact
        feature_impacts = []
        for i, name in enumerate(self.feature_names):
            sv = float(values[i])
            val = None
            if feature_values_dict and name in feature_values_dict:
                val = feature_values_dict[name]
            else:
                val = float(vec[0, i])

            feature_impacts.append({
                "name": name,
                "shap_value": round(sv, 4),
                "absolute_impact": round(abs(sv), 4),
                "value": round(float(val), 4) if val is not None else None,
                "direction": "BULLISH" if sv > 0 else "BEARISH",
            })

        feature_impacts.sort(key=lambda x: x["absolute_impact"], reverse=True)

        for rank, item in enumerate(feature_impacts[:top_k], start=1):
            item["rank"] = rank

        return {
            "base_value": round(base_val, 4),
            "top_features": feature_impacts[:top_k],
            "all_shap_values": {
                item["name"]: item["shap_value"] for item in feature_impacts
            },
        }

    def compute_global_importance(
        self, X_sample: np.ndarray, max_samples: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Compute global feature importance as mean absolute SHAP value across samples.
        """
        X = np.asarray(X_sample)
        if len(X) > max_samples:
            indices = np.random.RandomState(42).choice(len(X), size=max_samples, replace=False)
            X = X[indices]

        shap_values = self.explainer.shap_values(X)

        if isinstance(shap_values, list) and len(shap_values) == 2:
            matrix = shap_values[1]
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            matrix = shap_values[:, :, 1]
        else:
            matrix = np.asarray(shap_values)

        mean_abs = np.mean(np.abs(matrix), axis=0)

        global_list = []
        for i, name in enumerate(self.feature_names):
            global_list.append({
                "feature": name,
                "mean_abs_shap": round(float(mean_abs[i]), 4),
            })

        global_list.sort(key=lambda x: x["mean_abs_shap"], reverse=True)
        return global_list
