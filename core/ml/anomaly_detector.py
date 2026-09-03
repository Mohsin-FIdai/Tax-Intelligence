"""
Ensemble Anomaly Detection Module — Tax Intelligence Platform

Combines IsolationForest, Local Outlier Factor, and One-Class SVM
into a weighted ensemble for robust anomaly detection on taxpayer
feature data.
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

from config.settings import ISO_FOREST_PARAMS

logger = logging.getLogger(__name__)

# Ensemble weights
_WEIGHT_IFOREST = 0.50
_WEIGHT_LOF = 0.30
_WEIGHT_SVM = 0.20


class AnomalyDetector:
    """
    Weighted ensemble anomaly detector.

    Models
    ------
    - IsolationForest (50 % weight): tree-based, fast, handles high dim.
    - LocalOutlierFactor (30 % weight): density-based, finds local anomalies.
    - OneClassSVM (20 % weight): margin-based, captures non-linear boundaries.

    All models are preceded by StandardScaler normalization.
    """

    def __init__(self) -> None:
        """Initialize the three anomaly detection models and scaler."""
        self._scaler = StandardScaler()

        # IsolationForest — parameters from central config
        self._iforest = IsolationForest(**ISO_FOREST_PARAMS)

        # LOF — contamination must match IsolationForest for consistency
        self._lof = LocalOutlierFactor(
            n_neighbors=20,
            contamination=ISO_FOREST_PARAMS.get("contamination", 0.15),
            novelty=True,  # enables predict() and score_samples() on new data
        )

        # OneClassSVM — RBF kernel
        self._svm = OneClassSVM(
            kernel="rbf",
            gamma="scale",
            nu=ISO_FOREST_PARAMS.get("contamination", 0.15),
        )

        self._is_fitted = False
        self._feature_names: list = []

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def fit(self, X: pd.DataFrame) -> 'AnomalyDetector':
        """Fit the anomaly detection models to the data."""
        self._n_samples = len(X)
        self._use_fast_only = self._n_samples > 20000
        
        try:
            from core.compute.compute_backend import get_compute_backend
            from config.settings import COMPUTE_DEVICE
            backend = get_compute_backend(COMPUTE_DEVICE)
            if backend.is_gpu():
                self._use_fast_only = False
        except ImportError:
            pass

        logger.info(f"Fitting Anomaly Models on {self._n_samples} records")
        self._feature_names = list(X.columns)
        X_scaled = self._scaler.fit_transform(X)

        self._iforest.fit(X_scaled)

        if not self._use_fast_only:
            self._lof.fit(X_scaled)
            self._svm.fit(X_scaled)

        self._is_fitted = True
        logger.info("AnomalyDetector fit complete")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict anomaly labels using weighted ensemble voting.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.

        Returns
        -------
        np.ndarray
            Array of labels: -1 for anomaly, 1 for normal.
        """
        self._check_fitted()
        X_scaled = self._scale(X)

        # Each model returns -1 (anomaly) or 1 (normal)
        pred_if = self._iforest.predict(X_scaled)
        pred_lof = self._lof.predict(X_scaled)
        pred_svm = self._svm.predict(X_scaled)

        # Weighted vote: convert labels to 0/1 (anomaly=0, normal=1)
        vote = (
            _WEIGHT_IFOREST * (pred_if == -1).astype(float)
            + _WEIGHT_LOF * (pred_lof == -1).astype(float)
            + _WEIGHT_SVM * (pred_svm == -1).astype(float)
        )

        # If combined anomaly weight >= 0.5, classify as anomaly
        labels = np.where(vote >= 0.5, -1, 1)
        n_anomalies = int((labels == -1).sum())
        logger.info(
            "Predicted %d anomalies out of %d samples (%.1f%%)",
            n_anomalies,
            len(labels),
            100.0 * n_anomalies / max(len(labels), 1),
        )
        return labels

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """
        Compute raw weighted anomaly scores.

        Lower (more negative) values indicate stronger anomalies.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.

        Returns
        -------
        np.ndarray
            Weighted average of per-model anomaly scores.
        """
        self._check_fitted()
        X_scaled = self._scale(X)

        # score_samples returns negative values; more negative = more anomalous
        scores_if = self._iforest.score_samples(X_scaled)
        norm_if = self._minmax_normalize(scores_if)

        if getattr(self, '_use_fast_only', False):
            return norm_if

        scores_lof = self._lof.score_samples(X_scaled)
        scores_svm = self._svm.score_samples(X_scaled)

        # Normalize each to [0, 1] range before weighting
        norm_lof = self._minmax_normalize(scores_lof)
        norm_svm = self._minmax_normalize(scores_svm)

        combined = (
            _WEIGHT_IFOREST * norm_if
            + _WEIGHT_LOF * norm_lof
            + _WEIGHT_SVM * norm_svm
        )
        return combined

    def get_suspicion_percentage(self, X: pd.DataFrame) -> np.ndarray:
        """
        Convert ensemble anomaly scores to 0–100 suspicion percentage.

        Higher value = more suspicious.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.

        Returns
        -------
        np.ndarray
            Suspicion percentages in [0, 100].
        """
        combined = self.score_samples(X)
        # combined is in [0, 1] where 0 = most anomalous
        # Invert so that higher = more suspicious
        suspicion = (1.0 - combined) * 100.0
        return np.clip(suspicion, 0.0, 100.0)

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _check_fitted(self) -> None:
        """Raise if models have not been fitted."""
        if not self._is_fitted:
            raise RuntimeError(
                "AnomalyDetector has not been fitted. Call fit() first."
            )

    def _validate_and_convert(self, X: pd.DataFrame) -> np.ndarray:
        """
        Validate input and convert to numpy array.

        Replaces inf with NaN, then fills NaN with 0.
        """
        arr = X.values.astype(np.float64)
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        return arr

    def _scale(self, X: pd.DataFrame) -> np.ndarray:
        """Scale features using the already-fitted StandardScaler."""
        X_arr = self._validate_and_convert(X)
        return self._scaler.transform(X_arr)

    @staticmethod
    def _minmax_normalize(scores: np.ndarray) -> np.ndarray:
        """
        Normalize an array to [0, 1] using min-max scaling.

        If all values are equal, returns array of 0.5.
        """
        s_min = scores.min()
        s_max = scores.max()
        if s_max - s_min < 1e-12:
            return np.full_like(scores, 0.5)
        return (scores - s_min) / (s_max - s_min)
