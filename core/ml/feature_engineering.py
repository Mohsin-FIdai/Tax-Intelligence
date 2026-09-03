"""
Feature Engineering Module — Tax Intelligence Platform

Extracts 25+ features from citizen profiles across multiple data sources
for use in anomaly detection and risk classification models.
"""

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config.settings import ANOMALY_RATE, TAX_FILING_RATE

logger = logging.getLogger(__name__)

# Luxury travel destinations for flagging
LUXURY_DESTINATIONS = [
    "United Kingdom", "UK", "France", "Germany", "Italy", "Spain",
    "Switzerland", "Maldives", "Dubai", "UAE", "United States", "USA",
    "Canada", "Australia", "Singapore", "Malaysia", "Thailand",
    "Turkey", "Greece", "Japan",
]

BUSINESS_CLASS_LABELS = ["business", "first", "business class", "first class"]


class FeatureEngineer:
    """
    Extracts and engineers features from multiple citizen data sources
    for downstream ML models.

    Produces a clean DataFrame with 25+ engineered features covering:
    - Income and tax metrics
    - Vehicle asset indicators
    - Property asset indicators
    - Utility lifestyle indicators
    - Travel behavior indicators
    - Business ownership indicators
    - Banking activity indicators
    - Graph-derived centrality metrics (optional)
    - Derived ratio features
    """

    def __init__(self) -> None:
        """Initialize the FeatureEngineer with default column mappings."""
        self._feature_columns: List[str] = []

    @property
    def feature_columns(self) -> List[str]:
        """Return the list of feature column names produced by the last extraction."""
        return list(self._feature_columns)

    def extract_features(
        self,
        citizens_df: pd.DataFrame,
        vehicles_df: pd.DataFrame,
        properties_df: pd.DataFrame,
        utilities_df: pd.DataFrame,
        travel_df: pd.DataFrame,
        business_df: pd.DataFrame,
        banking_df: pd.DataFrame,
        graph_metrics: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Extract and engineer features from all citizen data sources.

        Parameters
        ----------
        citizens_df : pd.DataFrame
            Core citizen records with columns like citizen_id, cnic,
            declared_income, tax_paid, filing_status, phone_count, etc.
        vehicles_df : pd.DataFrame
            Vehicle registrations with citizen_id, vehicle_value.
        properties_df : pd.DataFrame
            Property ownership with citizen_id, property_value.
        utilities_df : pd.DataFrame
            Utility bills with citizen_id, electricity_bill, gas_bill,
            month columns.
        travel_df : pd.DataFrame
            Travel records with citizen_id, destination, travel_class,
            travel_type (domestic/international).
        business_df : pd.DataFrame
            Business registrations with citizen_id, role
            (owner/director/shareholder), share_value.
        banking_df : pd.DataFrame
            Banking activity with citizen_id, monthly_transactions,
            avg_balance.
        graph_metrics : pd.DataFrame, optional
            Knowledge-graph centrality metrics with citizen_id,
            degree_centrality, betweenness_centrality.

        Returns
        -------
        pd.DataFrame
            Feature matrix indexed by citizen_id with 25+ columns,
            all missing values handled.
        """
        logger.info("Starting feature extraction for %d citizens", len(citizens_df))

        # Start with base citizen features
        features = self._extract_citizen_base(citizens_df)

        # Merge each data source
        features = self._merge_vehicle_features(features, vehicles_df)
        features = self._merge_property_features(features, properties_df)
        features = self._merge_utility_features(features, utilities_df)
        features = self._merge_travel_features(features, travel_df)
        features = self._merge_business_features(features, business_df)
        features = self._merge_banking_features(features, banking_df)

        # Optional graph metrics
        if graph_metrics is not None and not graph_metrics.empty:
            features = self._merge_graph_metrics(features, graph_metrics)
        else:
            features["graph_degree_centrality"] = 0.0
            features["graph_betweenness"] = 0.0

        # Derived ratio features
        features = self._compute_derived_ratios(features)

        # Fill any remaining NaN values
        features = features.fillna(0.0)

        # Record feature columns (exclude citizen_id)
        self._feature_columns = [
            c for c in features.columns if c != "citizen_id"
        ]

        logger.info(
            "Feature extraction complete: %d citizens × %d features",
            len(features),
            len(self._feature_columns),
        )
        return features

    # ------------------------------------------------------------------ #
    #  Private helpers for each data source                                #
    # ------------------------------------------------------------------ #

    def _extract_citizen_base(self, citizens_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract base features from the citizens table.

        Includes declared_income, tax_paid, phone_count, and
        filing_status_encoded.
        """
        base = citizens_df[["citizen_id"]].copy()

        # Declared income
        if "declared_income" in citizens_df.columns:
            base["declared_income"] = pd.to_numeric(
                citizens_df["declared_income"], errors="coerce"
            ).fillna(0).astype(float)
        else:
            base["declared_income"] = 0.0

        # Tax paid
        if "tax_paid" in citizens_df.columns:
            base["tax_paid"] = pd.to_numeric(
                citizens_df["tax_paid"], errors="coerce"
            ).fillna(0).astype(float)
        else:
            base["tax_paid"] = 0.0

        # Phone / SIM count
        if "phone_count" in citizens_df.columns:
            base["phone_count"] = (
                citizens_df["phone_count"].fillna(1).astype(int)
            )
        elif "phone" in citizens_df.columns:
            base["phone_count"] = 1
        else:
            base["phone_count"] = 1

        # Filing status encoded: 0=non-filer, 0.5=late, 1=filed
        base["filing_status_encoded"] = self._encode_filing_status(citizens_df)

        return base

    @staticmethod
    def _encode_filing_status(citizens_df: pd.DataFrame) -> pd.Series:
        """
        Encode filing_status column to numeric values.

        Mapping:
            'filed' / 'filer' / True / 1 -> 1.0
            'late' / 'late_filer'         -> 0.5
            'non-filer' / False / 0 / NaN -> 0.0
        """
        if "filing_status" not in citizens_df.columns:
            return pd.Series(0.0, index=citizens_df.index)

        status = citizens_df["filing_status"].astype(str).str.lower().str.strip()
        encoded = pd.Series(0.0, index=citizens_df.index)
        encoded[status.isin(["filed", "filer", "true", "1", "yes"])] = 1.0
        encoded[status.isin(["late", "late_filer", "late_filed"])] = 0.5
        return encoded

    @staticmethod
    def _merge_vehicle_features(
        features: pd.DataFrame, vehicles_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregate vehicle data per citizen: total value, count, max value.
        """
        if vehicles_df is None or vehicles_df.empty:
            features["total_vehicle_value"] = 0.0
            features["vehicle_count"] = 0
            features["max_vehicle_value"] = 0.0
            return features

        value_col = _find_column(vehicles_df, [
            "vehicle_value", "market_value", "value", "price",
            "estimated_value", "amount", "vehicle_price", "vehicle_market_value"
        ])

        if value_col is None:
            # No value column found — still count vehicles per citizen
            agg = (
                vehicles_df.groupby("citizen_id")
                .size()
                .reset_index(name="vehicle_count")
            )
            agg["total_vehicle_value"] = 0.0
            agg["max_vehicle_value"] = 0.0
        else:
            vehicles_df[value_col] = pd.to_numeric(vehicles_df[value_col], errors="coerce").fillna(0)
            agg = (
                vehicles_df.groupby("citizen_id")[value_col]
                .agg(
                    total_vehicle_value="sum",
                    vehicle_count="count",
                    max_vehicle_value="max",
                )
                .reset_index()
            )

        features = features.merge(agg, on="citizen_id", how="left")
        for col in ["total_vehicle_value", "vehicle_count", "max_vehicle_value"]:
            features[col] = features[col].fillna(0)
        features["vehicle_count"] = features["vehicle_count"].astype(int)
        return features

    @staticmethod
    def _merge_property_features(
        features: pd.DataFrame, properties_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregate property data per citizen: total value, count.
        """
        if properties_df is None or properties_df.empty:
            features["total_property_value"] = 0.0
            features["property_count"] = 0
            return features

        value_col = _find_column(properties_df, [
            "property_value", "value", "estimated_value", "price",
            "amount", "plot_value", "house_value", "market_value"
        ])

        if value_col is None:
            agg = (
                properties_df.groupby("citizen_id")
                .size()
                .reset_index(name="property_count")
            )
            agg["total_property_value"] = 0.0
        else:
            properties_df[value_col] = pd.to_numeric(properties_df[value_col], errors="coerce").fillna(0)
            agg = (
                properties_df.groupby("citizen_id")[value_col]
                .agg(total_property_value="sum", property_count="count")
                .reset_index()
            )

        features = features.merge(agg, on="citizen_id", how="left")
        features["total_property_value"] = features["total_property_value"].fillna(0)
        features["property_count"] = features["property_count"].fillna(0).astype(int)
        return features

    @staticmethod
    def _merge_utility_features(
        features: pd.DataFrame, utilities_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregate utility bills per citizen: average monthly electricity,
        gas, and total annual utility spend.
        """
        if utilities_df is None or utilities_df.empty:
            features["avg_monthly_electricity"] = 0.0
            features["avg_monthly_gas"] = 0.0
            features["total_utility_spend"] = 0.0
            return features

        elec_col = _find_column(
            utilities_df, ["electricity_bill", "electricity", "electric_bill", "electricity_amount", "monthly_electricity_bill_(pkr)", "monthly_electricity_bill"]
        )
        gas_col = _find_column(
            utilities_df, ["gas_bill", "gas", "gas_amount", "monthly_gas_bill_(pkr)", "monthly_gas_bill"]
        )
        bill_col = _find_column(
            utilities_df, ["monthly_bill_pkr", "monthly_bill", "bill_amount", "bill"]
        )

        agg_dict: Dict[str, tuple] = {}
        if elec_col:
            agg_dict["avg_monthly_electricity"] = (elec_col, "mean")
        if gas_col:
            agg_dict["avg_monthly_gas"] = (gas_col, "mean")
        if bill_col and not elec_col:
            agg_dict["avg_monthly_electricity"] = (bill_col, "mean")

        if not agg_dict:
            features["avg_monthly_electricity"] = 0.0
            features["avg_monthly_gas"] = 0.0
            features["total_utility_spend"] = 0.0
            return features

        agg = utilities_df.groupby("citizen_id").agg(**agg_dict).reset_index()

        features = features.merge(agg, on="citizen_id", how="left")

        if "avg_monthly_electricity" not in features.columns:
            features["avg_monthly_electricity"] = 0.0
        if "avg_monthly_gas" not in features.columns:
            features["avg_monthly_gas"] = 0.0

        features["avg_monthly_electricity"] = pd.to_numeric(features["avg_monthly_electricity"], errors="coerce").fillna(0)
        features["avg_monthly_gas"] = pd.to_numeric(features["avg_monthly_gas"], errors="coerce").fillna(0)

        # Annual utility spend = (avg electricity + avg gas) × 12
        features["total_utility_spend"] = (
            features["avg_monthly_electricity"] + features["avg_monthly_gas"]
        ) * 12

        return features

    @staticmethod
    def _merge_travel_features(
        features: pd.DataFrame, travel_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregate travel records per citizen: international trip count,
        business-class trip count, luxury destination count.
        """
        if travel_df is None or travel_df.empty:
            features["foreign_travel_count"] = 0
            features["business_class_trips"] = 0
            features["luxury_destination_count"] = 0
            return features

        travel = travel_df.copy()

        # --- foreign travel count ---
        type_col = _find_column(travel, ["travel_type", "trip_type", "type", "international"])
        if type_col:
            intl_mask = travel[type_col].astype(str).str.lower().isin(
                ["international", "foreign", "intl", "true", "1", "yes"]
            )
        else:
            # Fallback: assume all are international
            intl_mask = pd.Series(True, index=travel.index)

        intl_counts = (
            travel[intl_mask]
            .groupby("citizen_id")
            .size()
            .reset_index(name="foreign_travel_count")
        )

        # --- business / first class trips ---
        class_col = _find_column(travel, ["travel_class", "class", "cabin_class", "ticket_class"])
        if class_col:
            biz_mask = travel[class_col].astype(str).str.lower().isin(BUSINESS_CLASS_LABELS)
            biz_counts = (
                travel[biz_mask]
                .groupby("citizen_id")
                .size()
                .reset_index(name="business_class_trips")
            )
        else:
            biz_counts = pd.DataFrame(columns=["citizen_id", "business_class_trips"])

        # --- luxury destination count ---
        dest_col = _find_column(travel, ["destination", "country", "destination_country"])
        if dest_col:
            lux_lower = [d.lower() for d in LUXURY_DESTINATIONS]
            lux_mask = travel[dest_col].astype(str).str.lower().isin(lux_lower)
            lux_counts = (
                travel[lux_mask]
                .groupby("citizen_id")
                .size()
                .reset_index(name="luxury_destination_count")
            )
        else:
            lux_counts = pd.DataFrame(columns=["citizen_id", "luxury_destination_count"])

        # Merge all travel features
        for df_agg, col_name in [
            (intl_counts, "foreign_travel_count"),
            (biz_counts, "business_class_trips"),
            (lux_counts, "luxury_destination_count"),
        ]:
            if not df_agg.empty:
                features = features.merge(df_agg, on="citizen_id", how="left")
            if col_name not in features.columns:
                features[col_name] = 0
            features[col_name] = features[col_name].fillna(0).astype(int)

        return features

    @staticmethod
    def _merge_business_features(
        features: pd.DataFrame, business_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregate business records per citizen: business count,
        directorship count, total share value.
        """
        if business_df is None or business_df.empty:
            features["business_count"] = 0
            features["directorship_count"] = 0
            features["total_share_value"] = 0.0
            return features

        biz = business_df.copy()

        # Total businesses owned
        biz_count = (
            biz.groupby("citizen_id").size().reset_index(name="business_count")
        )

        # Directorship count
        role_col = _find_column(biz, ["role", "position", "designation"])
        if role_col:
            dir_mask = biz[role_col].astype(str).str.lower().isin(
                ["director", "board member", "board_member", "directorship"]
            )
            dir_count = (
                biz[dir_mask]
                .groupby("citizen_id")
                .size()
                .reset_index(name="directorship_count")
            )
        else:
            dir_count = pd.DataFrame(columns=["citizen_id", "directorship_count"])

        # Total share value / turnover
        share_col = _find_column(biz, ["annual_turnover_pkr", "annual_turnover", "turnover", "share_value", "shares_value", "investment_value", "equity_value", "annual_revenue"])
        if share_col:
            share_agg = (
                biz.groupby("citizen_id")[share_col]
                .sum()
                .reset_index(name="total_share_value")
            )
        else:
            share_agg = pd.DataFrame(columns=["citizen_id", "total_share_value"])

        for df_agg, col_name, default in [
            (biz_count, "business_count", 0),
            (dir_count, "directorship_count", 0),
            (share_agg, "total_share_value", 0.0),
        ]:
            if not df_agg.empty:
                features = features.merge(df_agg, on="citizen_id", how="left")
            if col_name not in features.columns:
                features[col_name] = default
            features[col_name] = features[col_name].fillna(default)

        features["business_count"] = features["business_count"].astype(int)
        features["directorship_count"] = features["directorship_count"].astype(int)
        return features

    @staticmethod
    def _merge_banking_features(
        features: pd.DataFrame, banking_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregate banking data per citizen: average monthly transactions,
        average bank balance.
        """
        if banking_df is None or banking_df.empty:
            features["avg_monthly_transactions"] = 0.0
            features["avg_bank_balance"] = 0.0
            return features

        txn_col = _find_column(
            banking_df, ["monthly_expenditure_pkr", "monthly_expenditure", "monthly_transactions", "transactions", "txn_count", "transaction_count"]
        )
        bal_col = _find_column(
            banking_df, ["annual_expenditure_pkr", "annual_expenditure", "avg_balance", "average_balance", "balance", "bank_balance"]
        )

        agg_dict: Dict[str, tuple] = {}
        if txn_col:
            agg_dict["avg_monthly_transactions"] = (txn_col, "mean")
        if bal_col:
            agg_dict["avg_bank_balance"] = (bal_col, "mean")

        if agg_dict:
            agg = banking_df.groupby("citizen_id").agg(**agg_dict).reset_index()
            features = features.merge(agg, on="citizen_id", how="left")

        if "avg_monthly_transactions" not in features.columns:
            features["avg_monthly_transactions"] = 0.0
        if "avg_bank_balance" not in features.columns:
            features["avg_bank_balance"] = 0.0

        features["avg_monthly_transactions"] = features["avg_monthly_transactions"].fillna(0)
        features["avg_bank_balance"] = features["avg_bank_balance"].fillna(0)
        return features

    @staticmethod
    def _merge_graph_metrics(
        features: pd.DataFrame, graph_metrics: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge knowledge-graph centrality metrics.
        """
        gm = graph_metrics.copy()

        deg_col = _find_column(gm, ["degree_centrality", "degree"])
        bet_col = _find_column(gm, ["betweenness_centrality", "betweenness"])

        rename_map = {}
        if deg_col and deg_col != "graph_degree_centrality":
            rename_map[deg_col] = "graph_degree_centrality"
        if bet_col and bet_col != "graph_betweenness":
            rename_map[bet_col] = "graph_betweenness"

        if rename_map:
            gm = gm.rename(columns=rename_map)

        merge_cols = ["citizen_id"]
        if "graph_degree_centrality" in gm.columns:
            merge_cols.append("graph_degree_centrality")
        if "graph_betweenness" in gm.columns:
            merge_cols.append("graph_betweenness")

        features = features.merge(gm[merge_cols], on="citizen_id", how="left")

        if "graph_degree_centrality" not in features.columns:
            features["graph_degree_centrality"] = 0.0
        if "graph_betweenness" not in features.columns:
            features["graph_betweenness"] = 0.0

        features["graph_degree_centrality"] = features["graph_degree_centrality"].fillna(0)
        features["graph_betweenness"] = features["graph_betweenness"].fillna(0)
        return features

    @staticmethod
    def _compute_derived_ratios(features: pd.DataFrame) -> pd.DataFrame:
        """
        Compute derived ratio features that capture tax compliance gaps.
        """
        # Total tangible assets
        total_assets = (
            features.get("total_vehicle_value", 0)
            + features.get("total_property_value", 0)
            + features.get("total_share_value", 0)
        )

        # income_to_asset_ratio = declared_income / total_assets
        features["income_to_asset_ratio"] = np.where(
            total_assets > 0,
            features["declared_income"] / total_assets,
            0.0,
        )
        # Cap at 1.0 for normalization friendliness
        features["income_to_asset_ratio"] = features["income_to_asset_ratio"].clip(upper=1.0)

        # tax_to_income_ratio = tax_paid / declared_income
        features["tax_to_income_ratio"] = np.where(
            features["declared_income"] > 0,
            features["tax_paid"] / features["declared_income"],
            0.0,
        )
        features["tax_to_income_ratio"] = features["tax_to_income_ratio"].clip(upper=1.0)

        # utility_to_income_ratio = total_utility_spend / declared_income
        features["utility_to_income_ratio"] = np.where(
            features["declared_income"] > 0,
            features["total_utility_spend"] / features["declared_income"],
            0.0,
        )
        # Cap at 5.0 (utilities > 5× income is extreme)
        features["utility_to_income_ratio"] = features["utility_to_income_ratio"].clip(upper=5.0)

        return features

    def get_feature_matrix(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Return only the numeric feature columns (exclude citizen_id).

        Parameters
        ----------
        features_df : pd.DataFrame
            Full feature DataFrame produced by extract_features().

        Returns
        -------
        pd.DataFrame
            Numeric-only feature matrix suitable for ML models.
        """
        cols = [c for c in features_df.columns if c != "citizen_id"]
        return features_df[cols].astype(float)


# ────────────────────────────────────────────────────────────────────── #
#  Module-level utility                                                  #
# ────────────────────────────────────────────────────────────────────── #


def _find_column(
    df: pd.DataFrame, candidates: List[str]
) -> Optional[str]:
    """
    Return the first column name in *candidates* that exists in *df*.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to search.
    candidates : list of str
        Possible column names, in order of preference.

    Returns
    -------
    str or None
        The first matching column name, or ``None`` if none match.
    """
    for col in candidates:
        if col in df.columns:
            return col
    return None
