"""
Risk Categorizer — Tax Intelligence Platform

Maps deviation scores (0–100) to risk categories A through E,
each with a label, colour, and emoji, using the central
RISK_CATEGORIES configuration.
"""

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from config.settings import RISK_CATEGORIES

logger = logging.getLogger(__name__)


class RiskCategorizer:
    """
    Categorize citizens into risk bands based on their deviation score.

    Categories (from config):
        A (0–20):  Tax Compliant         🟢
        B (21–40): Needs Review          🔵
        C (41–60): Suspicious            🟡
        D (61–80): Likely Tax Evader     🟠
        E (81–100): Confirmed Tax Dev.   🔴
    """

    def __init__(self) -> None:
        """Initialize with risk categories from central config."""
        self._categories = dict(RISK_CATEGORIES)
        # Pre-sort by lower bound for efficient lookup
        self._sorted_keys = sorted(
            self._categories.keys(),
            key=lambda k: self._categories[k]["range"][0],
        )

    def categorize(self, deviation_score: float) -> Dict[str, Any]:
        """
        Categorize a single deviation score.

        Parameters
        ----------
        deviation_score : float
            Deviation score in [0, 100].

        Returns
        -------
        dict
            Keys: category, label, color, emoji, score.
        """
        score = float(np.clip(deviation_score, 0, 100))

        for key in self._sorted_keys:
            lo, hi = self._categories[key]["range"]
            if lo <= score <= hi:
                cat = self._categories[key]
                return {
                    "category": key,
                    "label": cat["label"],
                    "color": cat["color"],
                    "emoji": cat["emoji"],
                    "score": round(score, 2),
                }

        # Fallback: highest category if exactly 100 falls through
        last_key = self._sorted_keys[-1]
        cat = self._categories[last_key]
        return {
            "category": last_key,
            "label": cat["label"],
            "color": cat["color"],
            "emoji": cat["emoji"],
            "score": round(score, 2),
        }

    def categorize_batch(self, scores: np.ndarray) -> pd.DataFrame:
        """
        Categorize an array of deviation scores in batch.

        Parameters
        ----------
        scores : np.ndarray
            1-D array of deviation scores (0–100).

        Returns
        -------
        pd.DataFrame
            Columns: score, category, label, color, emoji.
        """
        scores = np.asarray(scores, dtype=float)
        results: List[Dict[str, Any]] = []

        for s in scores:
            results.append(self.categorize(s))

        df = pd.DataFrame(results)
        logger.info("Batch categorized %d scores", len(df))
        return df

    def get_category_info(self, category_key: str) -> Dict[str, Any]:
        """
        Return metadata for a specific category key.

        Parameters
        ----------
        category_key : str
            One of 'A', 'B', 'C', 'D', 'E'.

        Returns
        -------
        dict
            Category metadata including range, label, color, emoji.

        Raises
        ------
        KeyError
            If the category key is not recognized.
        """
        key = category_key.upper()
        if key not in self._categories:
            raise KeyError(
                f"Unknown risk category '{key}'. "
                f"Valid keys: {list(self._categories.keys())}"
            )
        return dict(self._categories[key])

    def get_all_categories(self) -> Dict[str, Dict[str, Any]]:
        """
        Return the full risk-category configuration.

        Returns
        -------
        dict
            Mapping of category key to metadata dict.
        """
        return {k: dict(v) for k, v in self._categories.items()}

    @staticmethod
    def score_to_priority(deviation_score: float) -> int:
        """
        Map deviation score to investigation priority (1 = highest).

        Parameters
        ----------
        deviation_score : float
            Score in [0, 100].

        Returns
        -------
        int
            Priority level 1–5 (1 = most urgent).
        """
        score = float(np.clip(deviation_score, 0, 100))
        if score >= 81:
            return 1
        if score >= 61:
            return 2
        if score >= 41:
            return 3
        if score >= 21:
            return 4
        return 5
