"""
Supervised Risk Classification Module — Tax Intelligence Platform

Ensemble of XGBoost and RandomForest classifiers that predicts
tax-evasion risk categories with rule-based label generation,
stratified cross-validation, and averaged feature importance.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

from config.settings import XGBOOST_PARAMS, RF_PARAMS

logger = logging.getLogger(__name__)

# Ensemble weights for prediction blending
_WEIGHT_XGB = 0.60
_WEIGHT_RF = 0.40

# Risk label thresholds (used in rule-based label generation)
_RISK_LABELS = {0: "low", 1: "medium", 2: "high"}


class RiskClassifier:
    """
    Ensemble risk classifier combining XGBoost and RandomForest.

    Supports:
    - Automatic rule-based label generation from features
    - Stratified k-fold cross-validation
    - Probability-based prediction blending
    - Averaged feature importance from both models
    """

    def __init__(self) -> None:
        """Initialize the ensemble classifier with config parameters."""
        self._xgb = XGBClassifier(**XGBOOST_PARAMS)
        self._rf = RandomForestClassifier(**RF_PARAMS)
        self._scaler = StandardScaler()
        self._is_fitted = False
        self._feature_names: List[str] = []
        self._n_classes: int = 3

    # ------------------------------------------------------------------ #
    #  Label generation                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_labels(features_df: pd.DataFrame) -> pd.Series:
        """
        Generate training labels from a rule-based heuristic.

        Rules
        -----
        High risk (2):
            - declared_income < estimated_net_worth × 0.1 AND tax_paid == 0
            - OR filing_status_encoded == 0 AND total_property_value > 5_000_000
        Medium risk (1):
            - declared_income < estimated_net_worth × 0.3
            - OR utility_to_income_ratio > 1.0
            - OR (foreign_travel_count >= 3 AND filing_status_encoded < 1)
        Low risk (0):
            - All others

        Parameters
        ----------
        features_df : pd.DataFrame
            Feature DataFrame produced by FeatureEngineer.

        Returns
        -------
        pd.Series
            Integer labels: 0=low, 1=medium, 2=high.
        """
        n = len(features_df)
        labels = pd.Series(np.zeros(n, dtype=int), index=features_df.index)

        # Compute estimated net worth proxy from assets
        net_worth = (
            features_df.get("total_vehicle_value", pd.Series(0, index=features_df.index)).fillna(0)
            + features_df.get("total_property_value", pd.Series(0, index=features_df.index)).fillna(0)
            + features_df.get("total_share_value", pd.Series(0, index=features_df.index)).fillna(0)
        )

        income = features_df.get("declared_income", pd.Series(0, index=features_df.index)).fillna(0)
        tax_paid = features_df.get("tax_paid", pd.Series(0, index=features_df.index)).fillna(0)
        filing = features_df.get("filing_status_encoded", pd.Series(0, index=features_df.index)).fillna(0)
        prop_val = features_df.get("total_property_value", pd.Series(0, index=features_df.index)).fillna(0)
        util_ratio = features_df.get("utility_to_income_ratio", pd.Series(0, index=features_df.index)).fillna(0)
        travel_ct = features_df.get("foreign_travel_count", pd.Series(0, index=features_df.index)).fillna(0)

        # ── Medium risk (1) ──
        medium_mask = (
            ((net_worth > 0) & (income < net_worth * 0.3))
            | (util_ratio > 1.0)
            | ((travel_ct >= 3) & (filing < 1.0))
        )
        labels[medium_mask] = 1

        # ── High risk (2) — stricter, overrides medium ──
        high_mask = (
            ((net_worth > 0) & (income < net_worth * 0.1) & (tax_paid <= 0))
            | ((filing == 0) & (prop_val > 5_000_000))
        )
        labels[high_mask] = 2

        counts = labels.value_counts().sort_index()
        logger.info("Generated labels — %s", dict(counts))
        return labels

    # ------------------------------------------------------------------ #
    #  Training                                                            #
    # ------------------------------------------------------------------ #

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv_folds: int = 5,
    ) -> Dict:
        """
        Train both models and return cross-validated metrics.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix (numeric only).
        y : pd.Series
            Integer risk labels (0, 1, 2).
        cv_folds : int
            Number of stratified CV folds (default 5).

        Returns
        -------
        dict
            Dictionary with keys: accuracy, precision, recall, f1,
            cv_scores, classification_report.
        """
        logger.info(
            "Training RiskClassifier on %d samples × %d features",
            *X.shape,
        )
        self._feature_names = list(X.columns)
        self._n_classes = int(y.nunique())

        X_arr = self._preprocess(X, fit=True)
        y_arr = y.values.astype(int)

        # ── Cross-validation on XGBoost ──
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        cv_results = cross_validate(
            XGBClassifier(**XGBOOST_PARAMS),
            X_arr,
            y_arr,
            cv=skf,
            scoring=["accuracy", "f1_weighted"],
            return_train_score=False,
        )

        # ── Full-data fit for both models ──
        self._xgb.fit(X_arr, y_arr)
        self._rf.fit(X_arr, y_arr)
        self._is_fitted = True

        # ── Evaluation on training set (for reporting) ──
        y_pred = self._predict_internal(X_arr)
        y_proba = self._predict_proba_internal(X_arr)

        report_str = classification_report(
            y_arr, y_pred, target_names=["low", "medium", "high"], zero_division=0
        )

        metrics = {
            "accuracy": float(accuracy_score(y_arr, y_pred)),
            "precision": float(precision_score(y_arr, y_pred, average="weighted", zero_division=0)),
            "recall": float(recall_score(y_arr, y_pred, average="weighted", zero_division=0)),
            "f1": float(f1_score(y_arr, y_pred, average="weighted", zero_division=0)),
            "cv_accuracy_mean": float(cv_results["test_accuracy"].mean()),
            "cv_accuracy_std": float(cv_results["test_accuracy"].std()),
            "cv_f1_mean": float(cv_results["test_f1_weighted"].mean()),
            "cv_f1_std": float(cv_results["test_f1_weighted"].std()),
            "classification_report": report_str,
            "n_samples": int(len(y_arr)),
            "n_features": int(X_arr.shape[1]),
            "label_distribution": dict(pd.Series(y_arr).value_counts().sort_index()),
        }

        logger.info(
            "Training complete — CV Accuracy: %.3f ± %.3f, CV F1: %.3f ± %.3f",
            metrics["cv_accuracy_mean"],
            metrics["cv_accuracy_std"],
            metrics["cv_f1_mean"],
            metrics["cv_f1_std"],
        )
        return metrics

    # ------------------------------------------------------------------ #
    #  Prediction                                                          #
    # ------------------------------------------------------------------ #

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict risk labels using the weighted ensemble.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.

        Returns
        -------
        np.ndarray
            Predicted labels: 0=low, 1=medium, 2=high.
        """
        self._check_fitted()
        X_arr = self._preprocess(X, fit=False)
        return self._predict_internal(X_arr)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict class probabilities using the weighted ensemble.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.

        Returns
        -------
        np.ndarray
            Array of shape (n_samples, n_classes) with probabilities.
        """
        self._check_fitted()
        X_arr = self._preprocess(X, fit=False)
        return self._predict_proba_internal(X_arr)

    def get_feature_importance(self) -> pd.DataFrame:
        """
        Return averaged feature importance from both models.

        Returns
        -------
        pd.DataFrame
            Columns: feature, xgb_importance, rf_importance,
            avg_importance. Sorted descending by avg_importance.
        """
        self._check_fitted()

        xgb_imp = self._xgb.feature_importances_
        rf_imp = self._rf.feature_importances_

        # Normalize each to sum to 1
        xgb_imp = xgb_imp / (xgb_imp.sum() + 1e-12)
        rf_imp = rf_imp / (rf_imp.sum() + 1e-12)

        avg_imp = _WEIGHT_XGB * xgb_imp + _WEIGHT_RF * rf_imp

        df = pd.DataFrame(
            {
                "feature": self._feature_names,
                "xgb_importance": xgb_imp,
                "rf_importance": rf_imp,
                "avg_importance": avg_imp,
            }
        )
        return df.sort_values("avg_importance", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------------ #
    #  Properties                                                          #
    # ------------------------------------------------------------------ #

    @property
    def xgb_model(self) -> XGBClassifier:
        """Return the underlying XGBoost model (e.g. for SHAP)."""
        return self._xgb

    @property
    def rf_model(self) -> RandomForestClassifier:
        """Return the underlying RandomForest model."""
        return self._rf

    @property
    def feature_names(self) -> List[str]:
        """Return the feature names used during training."""
        return list(self._feature_names)

    @property
    def is_fitted(self) -> bool:
        """Return whether the classifier has been trained."""
        return self._is_fitted

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _check_fitted(self) -> None:
        """Raise if the classifier hasn't been trained yet."""
        if not self._is_fitted:
            raise RuntimeError(
                "RiskClassifier has not been trained. Call train() first."
            )

    def _preprocess(self, X: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """
        Convert DataFrame to scaled numpy array.

        Parameters
        ----------
        X : pd.DataFrame
            Raw feature matrix.
        fit : bool
            If True, fit the scaler; otherwise just transform.

        Returns
        -------
        np.ndarray
            Scaled feature array.
        """
        arr = X.values.astype(np.float64)
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        if fit:
            return self._scaler.fit_transform(arr)
        return self._scaler.transform(arr)

    def _predict_internal(self, X_scaled: np.ndarray) -> np.ndarray:
        """Predict labels from already-scaled array."""
        proba = self._predict_proba_internal(X_scaled)
        return proba.argmax(axis=1)

    def _predict_proba_internal(self, X_scaled: np.ndarray) -> np.ndarray:
        """Predict blended probabilities from already-scaled array."""
        proba_xgb = self._xgb.predict_proba(X_scaled)
        proba_rf = self._rf.predict_proba(X_scaled)
        return _WEIGHT_XGB * proba_xgb + _WEIGHT_RF * proba_rf
