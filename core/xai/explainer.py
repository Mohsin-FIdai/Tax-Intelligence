"""
Explainable AI — SHAP-based model explanations with graceful fallbacks.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class ModelExplainer:
    """Wraps SHAP to provide explanations for tree-based models.

    Falls back to native feature importance when SHAP is unavailable or fails.
    """

    def __init__(self, model: Any, feature_names: list[str]):
        self.model = model
        self.feature_names = list(feature_names)
        self._shap_available = False
        self._explainer = None

        try:
            import shap
            self._explainer = shap.TreeExplainer(model)
            self._shap_available = True
        except Exception:
            pass

    def explain_prediction(self, X_single: np.ndarray | pd.DataFrame) -> dict:
        """Explain a single prediction.

        Returns
        -------
        dict with ``shap_values``, ``feature_contributions`` (sorted),
        ``top_positive_factors``, ``top_negative_factors``, ``base_value``.
        """
        if isinstance(X_single, pd.DataFrame):
            X_single = X_single.values
        if X_single.ndim == 1:
            X_single = X_single.reshape(1, -1)

        if self._shap_available and self._explainer is not None:
            try:
                import shap
                sv = self._explainer.shap_values(X_single)
                # Handle multi-output (classification): take class 1
                if isinstance(sv, list):
                    sv = sv[1] if len(sv) > 1 else sv[0]
                shap_vals = sv[0] if sv.ndim > 1 else sv
                base_value = self._explainer.expected_value
                if isinstance(base_value, (list, np.ndarray)):
                    base_value = base_value[1] if len(base_value) > 1 else base_value[0]
            except Exception:
                shap_vals = self._fallback_importance()
                base_value = 0.5
        else:
            shap_vals = self._fallback_importance()
            base_value = 0.5

        # Build contributions list
        contributions = []
        for i, fname in enumerate(self.feature_names):
            val = float(shap_vals[i]) if i < len(shap_vals) else 0.0
            fval = float(X_single[0][i]) if i < X_single.shape[1] else 0.0
            contributions.append({
                "feature": fname,
                "shap_value": round(val, 4),
                "feature_value": round(fval, 2),
                "direction": "positive" if val > 0 else "negative",
            })

        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        return {
            "shap_values": [c["shap_value"] for c in contributions],
            "feature_contributions": contributions,
            "top_positive_factors": [c for c in contributions if c["shap_value"] > 0][:5],
            "top_negative_factors": [c for c in contributions if c["shap_value"] < 0][:5],
            "base_value": float(base_value),
        }

    def global_importance(self, X: np.ndarray | pd.DataFrame) -> pd.DataFrame:
        """Compute global feature importance using mean |SHAP values|."""
        if isinstance(X, pd.DataFrame):
            X = X.values

        if self._shap_available and self._explainer is not None:
            try:
                sv = self._explainer.shap_values(X[:min(500, len(X))])
                if isinstance(sv, list):
                    sv = sv[1] if len(sv) > 1 else sv[0]
                mean_abs = np.mean(np.abs(sv), axis=0)
            except Exception:
                mean_abs = self._fallback_importance()
        else:
            mean_abs = self._fallback_importance()

        imp_df = pd.DataFrame({
            "feature": self.feature_names[:len(mean_abs)],
            "importance": mean_abs[:len(self.feature_names)],
        })
        imp_df = imp_df.sort_values("importance", ascending=False).reset_index(drop=True)
        imp_df["importance_pct"] = (
            imp_df["importance"] / imp_df["importance"].sum() * 100
        ).round(2)
        return imp_df

    def get_waterfall_data(self, X_single: np.ndarray | pd.DataFrame) -> dict:
        """Prepare data for a waterfall plot."""
        explanation = self.explain_prediction(X_single)
        top = explanation["feature_contributions"][:10]
        return {
            "base_value": explanation["base_value"],
            "features": [c["feature"] for c in top],
            "values": [c["shap_value"] for c in top],
            "feature_values": [c["feature_value"] for c in top],
        }

    def _fallback_importance(self) -> np.ndarray:
        """Use the model's built-in feature_importances_ as a fallback."""
        if hasattr(self.model, "feature_importances_"):
            imp = self.model.feature_importances_
            return imp / (imp.sum() + 1e-10)
        return np.ones(len(self.feature_names)) / len(self.feature_names)
