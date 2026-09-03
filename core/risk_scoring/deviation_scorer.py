"""
Tax Compliance Deviation Scorer — Tax Intelligence Platform

Computes a composite deviation score (0–100) reflecting the gap
between a citizen's declared tax position and their estimated
economic activity / lifestyle, using configurable component weights.
"""

import logging
from typing import Any, Dict, List

import numpy as np

from config.settings import DEVIATION_WEIGHTS

logger = logging.getLogger(__name__)


class DeviationScorer:
    """
    Compute a Tax Compliance Deviation Score for a citizen.

    Components (weights from config/settings.py DEVIATION_WEIGHTS):
        - income_networth_gap: 30 %
        - tax_gap:             25 %
        - lifestyle_gap:       20 %
        - anomaly_score:       15 %
        - filing_penalty:      10 %

    The final score is in [0, 100]. Higher = greater deviation from
    expected tax compliance.
    """

    def __init__(self) -> None:
        """Initialize with deviation weights from central config."""
        self._weights = dict(DEVIATION_WEIGHTS)

    def score(self, citizen_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate the deviation score for a single citizen.

        Parameters
        ----------
        citizen_features : dict
            Must contain keys produced by FeatureEngineer plus
            ``estimated_net_worth`` (from NetWorthEstimator) and
            optionally ``anomaly_suspicion`` (from AnomalyDetector).

            Key subset:
                - declared_income (float)
                - tax_paid (float)
                - estimated_net_worth (float)
                - total_vehicle_value, total_property_value (float)
                - avg_monthly_electricity, avg_monthly_gas (float)
                - total_utility_spend (float)
                - foreign_travel_count, business_class_trips (int)
                - filing_status_encoded (float: 0 / 0.5 / 1)
                - anomaly_suspicion (float, 0–100, optional)

        Returns
        -------
        dict
            Keys:
                - deviation_score (float, 0–100)
                - component_scores (dict of component → 0–100)
                - component_weighted (dict of component → weighted contribution)
                - explanation (list of human-readable strings)
        """
        components: Dict[str, float] = {}
        explanations: List[str] = []

        # ── 1. Income–Net-Worth Gap (30 %) ──
        components["income_networth_gap"], expl = self._income_networth_gap(
            citizen_features
        )
        explanations.extend(expl)

        # ── 2. Tax Gap (25 %) ──
        components["tax_gap"], expl = self._tax_gap(citizen_features)
        explanations.extend(expl)

        # ── 3. Lifestyle Gap (20 %) ──
        components["lifestyle_gap"], expl = self._lifestyle_gap(citizen_features)
        explanations.extend(expl)

        # ── 4. Anomaly Score (15 %) ──
        components["anomaly_score"], expl = self._anomaly_component(citizen_features)
        explanations.extend(expl)

        # ── 5. Filing Penalty (10 %) ──
        components["filing_penalty"], expl = self._filing_penalty(citizen_features)
        explanations.extend(expl)

        # ── Weighted combination ──
        weighted: Dict[str, float] = {}
        total = 0.0
        for key, raw_score in components.items():
            w = self._weights.get(key, 0.0)
            contrib = raw_score * w
            weighted[key] = round(contrib, 2)
            total += contrib

        deviation_score = float(np.clip(total, 0.0, 100.0))

        result = {
            "deviation_score": round(deviation_score, 2),
            "component_scores": {k: round(v, 2) for k, v in components.items()},
            "component_weighted": weighted,
            "explanation": explanations,
        }

        logger.debug("Deviation score: %.1f", deviation_score)
        return result

    # ------------------------------------------------------------------ #
    #  Component scorers (each returns 0–100 + explanations)               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _income_networth_gap(
        data: Dict[str, Any],
    ) -> tuple:
        """
        Score the gap between declared income and estimated net worth.

        A citizen declaring PKR 500K income but owning PKR 50M in assets
        shows a significant deviation.

        Returns (score: float, explanations: list[str]).
        """
        income = float(data.get("declared_income", 0) or 0)
        net_worth = float(data.get("estimated_net_worth", 0) or 0)
        explanations: List[str] = []

        if net_worth <= 0:
            return 0.0, explanations

        # Ratio of income to net worth; healthy is >= 0.10 (10 %)
        ratio = income / net_worth if net_worth > 0 else 1.0

        if ratio >= 0.20:
            score = 0.0
        elif ratio >= 0.10:
            # Linear interpolation 0→50 as ratio goes from 0.20→0.10
            score = (0.20 - ratio) / 0.10 * 50.0
        elif ratio >= 0.03:
            # 50→85
            score = 50.0 + (0.10 - ratio) / 0.07 * 35.0
        else:
            # 85→100
            score = 85.0 + (0.03 - max(ratio, 0)) / 0.03 * 15.0

        score = float(np.clip(score, 0, 100))

        if score > 50:
            explanations.append(
                f"Declared income (PKR {income:,.0f}) is only {ratio:.1%} "
                f"of estimated net worth (PKR {net_worth:,.0f})"
            )
        return score, explanations

    @staticmethod
    def _tax_gap(data: Dict[str, Any]) -> tuple:
        """
        Score the gap between expected and actual tax paid.

        Expected tax is approximated using Pakistan's progressive
        tax brackets at ~15% effective rate.

        Returns (score: float, explanations: list[str]).
        """
        income = float(data.get("declared_income", 0) or 0)
        tax_paid = float(data.get("tax_paid", 0) or 0)
        net_worth = float(data.get("estimated_net_worth", 0) or 0)
        explanations: List[str] = []

        # Estimate what reasonable income should be from net worth
        imputed_income = max(income, net_worth * 0.08)

        if imputed_income <= 600_000:
            # Below taxable threshold
            return 0.0, explanations

        # Approximate expected tax (progressive ~ 15 % average for high earners)
        if imputed_income <= 1_200_000:
            expected_tax = (imputed_income - 600_000) * 0.05
        elif imputed_income <= 2_400_000:
            expected_tax = 30_000 + (imputed_income - 1_200_000) * 0.10
        elif imputed_income <= 3_600_000:
            expected_tax = 150_000 + (imputed_income - 2_400_000) * 0.15
        elif imputed_income <= 6_000_000:
            expected_tax = 330_000 + (imputed_income - 3_600_000) * 0.20
        else:
            expected_tax = 810_000 + (imputed_income - 6_000_000) * 0.25

        if expected_tax <= 0:
            return 0.0, explanations

        gap_ratio = 1.0 - min(tax_paid / expected_tax, 1.0)
        score = gap_ratio * 100.0

        if score > 40:
            explanations.append(
                f"Tax paid (PKR {tax_paid:,.0f}) is {gap_ratio:.0%} below "
                f"expected tax (PKR {expected_tax:,.0f})"
            )
        return float(np.clip(score, 0, 100)), explanations

    @staticmethod
    def _lifestyle_gap(data: Dict[str, Any]) -> tuple:
        """
        Score lifestyle indicators that exceed declared income.

        Checks utility spending, travel patterns, and vehicle ownership
        against declared income.

        Returns (score: float, explanations: list[str]).
        """
        income = float(data.get("declared_income", 0) or 0)
        explanations: List[str] = []
        sub_scores: List[float] = []

        # Utility vs income
        utility_spend = float(data.get("total_utility_spend", 0) or 0)
        if income > 0 and utility_spend > 0:
            util_ratio = utility_spend / income
            if util_ratio > 0.5:
                u_score = min((util_ratio - 0.5) / 0.5 * 80 + 20, 100)
                sub_scores.append(u_score)
                explanations.append(
                    f"Annual utility spend (PKR {utility_spend:,.0f}) is "
                    f"{util_ratio:.0%} of declared income"
                )
            else:
                sub_scores.append(0.0)
        elif utility_spend > 600_000 and income <= 0:
            sub_scores.append(90.0)
            explanations.append(
                f"High utility spend (PKR {utility_spend:,.0f}) with no declared income"
            )
        else:
            sub_scores.append(0.0)

        # Travel vs income
        travel_count = int(data.get("foreign_travel_count", 0) or 0)
        biz_class = int(data.get("business_class_trips", 0) or 0)
        if travel_count > 0:
            travel_cost_est = travel_count * 300_000 + biz_class * 450_000
            if income > 0:
                travel_ratio = travel_cost_est / income
                if travel_ratio > 0.3:
                    t_score = min((travel_ratio - 0.3) / 0.7 * 80 + 20, 100)
                    sub_scores.append(t_score)
                    explanations.append(
                        f"Estimated travel cost (PKR {travel_cost_est:,.0f}) "
                        f"is {travel_ratio:.0%} of declared income"
                    )
                else:
                    sub_scores.append(0.0)
            elif travel_count >= 2:
                sub_scores.append(70.0)
            else:
                sub_scores.append(0.0)
        else:
            sub_scores.append(0.0)

        # Vehicle value vs income
        vehicle_val = float(data.get("total_vehicle_value", 0) or 0)
        if income > 0 and vehicle_val > income * 3:
            v_ratio = vehicle_val / income
            v_score = min((v_ratio - 3) / 7 * 80 + 20, 100)
            sub_scores.append(v_score)
            explanations.append(
                f"Vehicle assets (PKR {vehicle_val:,.0f}) exceed "
                f"{v_ratio:.1f}× declared income"
            )
        else:
            sub_scores.append(0.0)

        score = float(np.mean(sub_scores)) if sub_scores else 0.0
        return float(np.clip(score, 0, 100)), explanations

    @staticmethod
    def _anomaly_component(data: Dict[str, Any]) -> tuple:
        """
        Pass through the ML anomaly suspicion percentage.

        Returns (score: float, explanations: list[str]).
        """
        anomaly = float(data.get("anomaly_suspicion", 0) or 0)
        explanations: List[str] = []
        score = float(np.clip(anomaly, 0, 100))
        if score > 50:
            explanations.append(
                f"ML anomaly model flagged citizen at {score:.0f}% suspicion"
            )
        return score, explanations

    @staticmethod
    def _filing_penalty(data: Dict[str, Any]) -> tuple:
        """
        Penalize for non-filing or late filing.

        Filing status encoding: 0=non-filer, 0.5=late, 1=filed.

        Returns (score: float, explanations: list[str]).
        """
        filing = float(data.get("filing_status_encoded", 0) or 0)
        explanations: List[str] = []

        if filing >= 1.0:
            score = 0.0
        elif filing >= 0.5:
            score = 40.0
            explanations.append("Tax return filed late")
        else:
            score = 100.0
            explanations.append("No tax return filed (non-filer)")

        return score, explanations
