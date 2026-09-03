"""
Net Worth Estimator — Tax Intelligence Platform

Estimates a citizen's net worth using weighted asset categories
defined in the central configuration. Provides a breakdown by
category and a confidence score based on data completeness.
"""

import logging
from typing import Any, Dict, List

from config.settings import NET_WORTH_WEIGHTS

logger = logging.getLogger(__name__)

# Thresholds for utility-lifestyle and travel imputation
_UTILITY_ANNUAL_UPPER_CLASS = 600_000       # PKR per year
_UTILITY_ANNUAL_MIDDLE_CLASS = 240_000
_UTILITY_LIFESTYLE_MULTIPLIER = 15          # annual utility → implied lifestyle worth
_TRAVEL_TRIP_VALUE_ESTIMATE = 300_000       # PKR per international trip
_BANKING_BALANCE_MULTIPLIER = 2.0           # avg balance → implied liquid worth


class NetWorthEstimator:
    """
    Estimate net worth from citizen data using weighted asset categories.

    Weights (from config/settings.py NET_WORTH_WEIGHTS):
        - vehicle:           1.0
        - property:          1.0
        - business:          0.8
        - utility_lifestyle: 0.3
        - travel:            0.2
        - banking:           0.5
    """

    def __init__(self) -> None:
        """Initialize with weights from central config."""
        self._weights = dict(NET_WORTH_WEIGHTS)

    def estimate(self, citizen_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate net worth for a single citizen.

        Parameters
        ----------
        citizen_data : dict
            Citizen feature dictionary. Expected keys:
                - total_vehicle_value (float)
                - total_property_value (float)
                - total_share_value (float)
                - business_count (int)
                - avg_monthly_electricity (float)
                - avg_monthly_gas (float)
                - total_utility_spend (float)
                - foreign_travel_count (int)
                - business_class_trips (int)
                - avg_bank_balance (float)

        Returns
        -------
        dict
            Keys:
                - estimated_net_worth (float): total estimated worth
                - breakdown (dict): per-category estimated value and weight
                - confidence (float): 0-1 confidence based on data completeness
                - data_sources_present (list): which data sources had values
        """
        breakdown: Dict[str, Dict[str, float]] = {}
        sources_present: List[str] = []
        total_possible_sources = 6  # vehicle, property, business, utility, travel, banking

        # ── 1. Vehicle assets ──
        vehicle_raw = float(citizen_data.get("total_vehicle_value", 0) or 0)
        vehicle_weighted = vehicle_raw * self._weights["vehicle"]
        breakdown["vehicle"] = {
            "raw_value": vehicle_raw,
            "weight": self._weights["vehicle"],
            "weighted_value": vehicle_weighted,
        }
        if vehicle_raw > 0:
            sources_present.append("vehicle")

        # ── 2. Property assets ──
        property_raw = float(citizen_data.get("total_property_value", 0) or 0)
        property_weighted = property_raw * self._weights["property"]
        breakdown["property"] = {
            "raw_value": property_raw,
            "weight": self._weights["property"],
            "weighted_value": property_weighted,
        }
        if property_raw > 0:
            sources_present.append("property")

        # ── 3. Business / share ownership ──
        share_value = float(citizen_data.get("total_share_value", 0) or 0)
        business_count = int(citizen_data.get("business_count", 0) or 0)
        # If share_value is missing but businesses exist, impute modestly
        business_raw = share_value if share_value > 0 else business_count * 500_000
        business_weighted = business_raw * self._weights["business"]
        breakdown["business"] = {
            "raw_value": business_raw,
            "weight": self._weights["business"],
            "weighted_value": business_weighted,
        }
        if business_raw > 0:
            sources_present.append("business")

        # ── 4. Utility-lifestyle indicator ──
        annual_utility = float(citizen_data.get("total_utility_spend", 0) or 0)
        if annual_utility <= 0:
            monthly_elec = float(citizen_data.get("avg_monthly_electricity", 0) or 0)
            monthly_gas = float(citizen_data.get("avg_monthly_gas", 0) or 0)
            annual_utility = (monthly_elec + monthly_gas) * 12

        utility_raw = annual_utility * _UTILITY_LIFESTYLE_MULTIPLIER
        utility_weighted = utility_raw * self._weights["utility_lifestyle"]
        breakdown["utility_lifestyle"] = {
            "raw_value": utility_raw,
            "annual_utility_spend": annual_utility,
            "weight": self._weights["utility_lifestyle"],
            "weighted_value": utility_weighted,
        }
        if annual_utility > 0:
            sources_present.append("utility")

        # ── 5. Travel indicator ──
        foreign_trips = int(citizen_data.get("foreign_travel_count", 0) or 0)
        biz_class = int(citizen_data.get("business_class_trips", 0) or 0)
        # Business-class trips valued higher
        travel_raw = (
            (foreign_trips - biz_class) * _TRAVEL_TRIP_VALUE_ESTIMATE
            + biz_class * _TRAVEL_TRIP_VALUE_ESTIMATE * 2.5
        )
        travel_raw = max(travel_raw, 0.0)
        travel_weighted = travel_raw * self._weights["travel"]
        breakdown["travel"] = {
            "raw_value": travel_raw,
            "foreign_trips": foreign_trips,
            "business_class_trips": biz_class,
            "weight": self._weights["travel"],
            "weighted_value": travel_weighted,
        }
        if foreign_trips > 0:
            sources_present.append("travel")

        # ── 6. Banking indicator ──
        avg_balance = float(citizen_data.get("avg_bank_balance", 0) or 0)
        banking_raw = avg_balance * _BANKING_BALANCE_MULTIPLIER
        banking_weighted = banking_raw * self._weights["banking"]
        breakdown["banking"] = {
            "raw_value": banking_raw,
            "avg_balance": avg_balance,
            "weight": self._weights["banking"],
            "weighted_value": banking_weighted,
        }
        if avg_balance > 0:
            sources_present.append("banking")

        # ── Total estimated net worth ──
        estimated_net_worth = sum(
            cat["weighted_value"] for cat in breakdown.values()
        )

        # ── Confidence score (0-1) ──
        confidence = self._compute_confidence(
            sources_present, total_possible_sources, breakdown
        )

        result = {
            "estimated_net_worth": round(estimated_net_worth, 2),
            "breakdown": breakdown,
            "confidence": round(confidence, 3),
            "data_sources_present": sources_present,
        }

        logger.debug(
            "Net worth estimate: PKR %.0f (confidence %.1f%%)",
            estimated_net_worth,
            confidence * 100,
        )
        return result

    @staticmethod
    def _compute_confidence(
        sources: List[str],
        total_sources: int,
        breakdown: Dict[str, Dict[str, float]],
    ) -> float:
        """
        Compute a confidence score for the net worth estimate.

        Combines data completeness (how many sources contributed)
        with value diversity (are we relying on a single source?).

        Parameters
        ----------
        sources : list of str
            Data sources that had non-zero values.
        total_sources : int
            Total possible data source count.
        breakdown : dict
            Per-category breakdown.

        Returns
        -------
        float
            Confidence in [0, 1].
        """
        if not sources:
            return 0.0

        # Component 1: data completeness (0-1)
        completeness = len(sources) / total_sources

        # Component 2: value diversity (Herfindahl-like)
        values = [
            cat["weighted_value"]
            for cat in breakdown.values()
            if cat["weighted_value"] > 0
        ]
        total = sum(values)
        if total > 0 and len(values) > 1:
            shares = [v / total for v in values]
            hhi = sum(s ** 2 for s in shares)
            diversity = 1.0 - hhi  # lower HHI = more diverse = higher confidence
        else:
            diversity = 0.0

        # Weighted combination
        confidence = 0.6 * completeness + 0.4 * diversity
        return min(confidence, 1.0)
