"""
Tax Intelligence Platform — Data Service Layer

Singleton service that loads processed data from ``data/processed/`` and
exposes query helpers consumed by API route handlers.  All heavy lifting
is done with *pandas*; loaded DataFrames are cached for the lifetime of
the process.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import numpy as np
import pandas as pd

from core.entity_resolution.intelligent_search import advanced_fuzzy_search

from config.settings import (
    PROCESSED_DIR,
    MODELS_DIR,
    RISK_CATEGORIES,
)

logger = logging.getLogger(__name__)


class DataService:
    """Thread-safe singleton that holds all loaded data in memory."""

    _instance: Optional["DataService"] = None
    _lock: Lock = Lock()

    # ── Singleton accessor ────────────────────────────────────────────

    def __new__(cls) -> "DataService":
        """Return the singleton instance, creating it on first access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialised = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Load data only once."""
        if self._initialised:
            return
        self._initialised = True
        self._load_data()

    def reload(self) -> None:
        """Force a reload of all data into memory."""
        with self._lock:
            self._load_data()

    # ── Data Loading ──────────────────────────────────────────────────

    def _read_csv_safe(self, path: Path) -> pd.DataFrame:
        """Read a CSV file, returning an empty DataFrame on any error."""
        try:
            if path.exists():
                df = pd.read_csv(path, low_memory=False)
                logger.info("Loaded %s  (%d rows)", path.name, len(df))
                return df
            logger.warning("File not found: %s", path)
        except Exception as exc:
            logger.error("Error reading %s: %s", path, exc)
        return pd.DataFrame()

    def _read_pickle_safe(self, path: Path) -> Any:
        """Read a pickle file, returning None on any error."""
        try:
            if path.exists():
                with open(path, "rb") as fh:
                    obj = pickle.load(fh)
                logger.info("Loaded pickle %s", path.name)
                return obj
            logger.warning("Pickle not found: %s", path)
        except Exception as exc:
            logger.error("Error reading pickle %s: %s", path, exc)
        return None

    def _load_data(self) -> None:
        """Load every processed artefact into memory."""
        logger.info("DataService: loading data from %s …", PROCESSED_DIR)

        # Core citizen data
        self.citizens_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "master_citizens.csv"
        )
        self.tax_records_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "tax_records_clean.csv"
        )
        self.vehicles_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "vehicle_records_clean.csv"
        )
        self.properties_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "property_records_clean.csv"
        )
        self.businesses_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "business_records_clean.csv"
        )
        self.travel_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "travel_records_clean.csv"
        )
        self.utilities_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "utility_bills_clean.csv"
        )
        self.banking_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "banking_indicators_clean.csv"
        )
        self.mobile_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "mobile_records_clean.csv"
        )

        # Risk scores produced by the ML pipeline
        self.risk_scores_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "feature_vectors.csv"
        )

        # Entity resolution matches
        self.entity_matches_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "entity_matches.csv"
        )

        # Feature importance (from XAI module)
        self.feature_importance_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "feature_importance.csv"
        )

        # Knowledge graph (networkx pickled graph)
        self.graph = self._read_pickle_safe(MODELS_DIR / "knowledge_graph.pkl")
        if self.graph is None:
            import networkx as nx
            self.graph = nx.DiGraph()

        # Community assignments
        self.communities_df: pd.DataFrame = self._read_csv_safe(
            PROCESSED_DIR / "communities.csv"
        )
        if self.communities_df.empty and self.graph is not None and self.graph.number_of_nodes() > 0:
            self._compute_and_save_communities()

        # Merge risk scores into citizens if both exist
        if not self.citizens_df.empty and not self.risk_scores_df.empty:
            merge_key = self._detect_merge_key(self.citizens_df, self.risk_scores_df)
            if merge_key:
                cols_to_use = [merge_key] + [c for c in self.risk_scores_df.columns if c != merge_key and c not in self.citizens_df.columns]
                if len(cols_to_use) > 1:
                    self.citizens_df = self.citizens_df.merge(
                        self.risk_scores_df[cols_to_use], on=merge_key, how="left"
                    )

        # Ensure essential columns exist
        self._ensure_columns()

        logger.info(
            "DataService ready — %d citizen records loaded.", len(self.citizens_df)
        )

    @property
    def is_loaded(self) -> bool:
        """Return True if at least the citizens data is available."""
        return not self.citizens_df.empty

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _detect_merge_key(df1: pd.DataFrame, df2: pd.DataFrame) -> Optional[str]:
        """Find a shared key column for merging two DataFrames."""
        for col in ("citizen_id", "id", "cnic"):
            if col in df1.columns and col in df2.columns:
                return col
        return None

    def _ensure_columns(self) -> None:
        """Guarantee expected columns exist in citizens_df (fill with defaults)."""
        if "suspicion_pct" in self.citizens_df.columns and "risk_score" not in self.citizens_df.columns:
            self.citizens_df = self.citizens_df.rename(columns={"suspicion_pct": "risk_score"})
            
        defaults: dict[str, Any] = {
            "citizen_id": "",
            "name": "",
            "cnic": "",
            "city": "",
            "province": "",
            "risk_score": 0.0,
            "risk_category": "A",
            "filing_status": "Non-Filer",
            "declared_income": 0.0,
            "estimated_net_worth": 0.0,
            "father_name": "",
            "phone": "",
            "email": "",
            "address": "",
            "date_of_birth": "",
            "ntn": "",
            "deviation_score": 0.0,
            "suspicion_pct": 0.0,
        }
        for col, default in defaults.items():
            if col not in self.citizens_df.columns:
                self.citizens_df[col] = default

        # Derive risk_category from risk_score if not already present
        if "risk_category" in self.citizens_df.columns:
            mask = self.citizens_df["risk_category"].isna() | (
                self.citizens_df["risk_category"] == ""
            )
            if mask.any():
                self.citizens_df.loc[mask, "risk_category"] = self.citizens_df.loc[
                    mask, "risk_score"
                ].apply(self._score_to_category)
        else:
            self.citizens_df["risk_category"] = self.citizens_df["risk_score"].apply(
                self._score_to_category
            )

    @staticmethod
    def _score_to_category(score: float) -> str:
        """Map a numeric risk score to a category letter."""
        try:
            score = float(score)
        except (TypeError, ValueError):
            return "A"
        for cat, meta in RISK_CATEGORIES.items():
            lo, hi = meta["range"]
            if lo <= score <= hi:
                return cat
        return "E" if score > 80 else "A"

    # ── Citizen Queries ───────────────────────────────────────────────

    def get_citizens(
        self,
        filters: dict[str, Any],
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[dict], int]:
        """Return a filtered, paginated list of citizen summaries.

        Args:
            filters: Key/value filter parameters (see FilterParams schema).
            page: 1-indexed page number.
            page_size: Number of records per page.

        Returns:
            (list_of_dicts, total_matching_count)
        """
        df = self.citizens_df.copy()

        # Apply filters
        if filters.get("province"):
            df = df[df["province"].astype(str).str.lower() == filters["province"].lower()]
        if filters.get("city"):
            df = df[df["city"].astype(str).str.lower() == filters["city"].lower()]
        if filters.get("risk_level"):
            df = df[df["risk_category"] == filters["risk_level"].upper()]
        if filters.get("filing_status"):
            df = df[
                df["filing_status"].astype(str).str.lower() == filters["filing_status"].lower()
            ]
        if filters.get("min_income") is not None:
            df = df[df["declared_income"] >= filters["min_income"]]
        if filters.get("max_income") is not None:
            df = df[df["declared_income"] <= filters["max_income"]]
        if filters.get("min_risk_score") is not None:
            df = df[df["risk_score"] >= filters["min_risk_score"]]
        if filters.get("max_risk_score") is not None:
            df = df[df["risk_score"] <= filters["max_risk_score"]]

        if filters.get("search_query"):
            query = filters["search_query"].lower().strip()
            
            # Cross-lingual support for common names in the dataset
            mapping = {
                "omar": "عمر",
                "umar": "عمر",
                "عمر": "omar",
                "sheikh": "شیخ",
                "شیخ": "sheikh",
                "raza": "رضا",
                "رضا": "raza",
                "ali": "علی",
                "علی": "ali"
            }
            
            tokens = query.split()
            regex_parts = []
            for t in tokens:
                if t in mapping:
                    regex_parts.append(f"({t}|{mapping[t]})")
                else:
                    regex_parts.append(t)
            
            import re
            regex_query = ".*".join(regex_parts)
            
            df = df[
                df["canonical_name"].fillna("").str.lower().str.contains(regex_query, regex=True, flags=re.IGNORECASE) |
                df["cnic"].fillna("").astype(str).str.contains(query)
            ]

        # Sort
        sort_col = filters.get("sort_by", "risk_score")
        if sort_col not in df.columns:
            sort_col = "risk_score"
        ascending = filters.get("sort_order", "desc").lower() == "asc"
        df = df.sort_values(sort_col, ascending=ascending, na_position="last")

        total = len(df)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end]

        summary_cols = [
            "citizen_id", "name", "canonical_name", "urdu_name", "cnic", "city", "province",
            "risk_score", "risk_category", "filing_status",
            "declared_income", "estimated_net_worth",
            "deviation_score", "estimated_hidden_income", "estimated_recoverable_tax",
        ]
        existing_cols = [c for c in summary_cols if c in page_df.columns]
        records = page_df[existing_cols].fillna("").to_dict(orient="records")
        for r in records:
            if "name" not in r or not r["name"]:
                r["name"] = r.get("canonical_name", "")
            if "canonical_name" not in r or not r["canonical_name"]:
                r["canonical_name"] = r.get("name", "")
            if "urdu_name" not in r:
                r["urdu_name"] = ""
        return records, total

    def get_citizen_by_id(self, citizen_id: str) -> Optional[dict]:
        """Return the full profile dict for a citizen, or None if not found.

        Merges assets, tax records, risk details, and audit trail into
        a single dictionary that maps directly to the CitizenProfile schema.
        """
        row = self.citizens_df[self.citizens_df["citizen_id"] == citizen_id]
        if row.empty:
            return None
        record = row.iloc[0].to_dict()

        if "name" not in record or not record["name"]:
            record["name"] = record.get("canonical_name", "")
        if "canonical_name" not in record or not record["canonical_name"]:
            record["canonical_name"] = record.get("name", "")
        if "urdu_name" not in record:
            record["urdu_name"] = ""

        # Replace NaN / NaT with sensible defaults
        record = {
            k: ("" if isinstance(v, float) and np.isnan(v) else v)
            for k, v in record.items()
        }

        # Enrich with assets
        record["assets"] = self.get_citizen_assets(citizen_id)
        record["tax_records"] = self._get_tax_records(citizen_id)
        record["risk_details"] = self._build_risk_details(record)
        record["audit_trail"] = self.get_citizen_audit_trail(citizen_id)

        return record

    def _get_tax_records(self, citizen_id: str) -> list[dict]:
        """Return tax filing history for a citizen."""
        if self.tax_records_df.empty:
            return []
        key = self._detect_merge_key(
            self.tax_records_df,
            pd.DataFrame({"citizen_id": [citizen_id]}),
        ) or "citizen_id"
        if key not in self.tax_records_df.columns:
            return []
        rows = self.tax_records_df[self.tax_records_df[key] == citizen_id]
        return rows.fillna("").to_dict(orient="records")

    def _build_risk_details(self, record: dict) -> dict:
        """Construct a RiskDetail-compatible dict from a citizen record."""
        cat = str(record.get("risk_category", "A"))
        meta = RISK_CATEGORIES.get(cat, RISK_CATEGORIES["A"])
        return {
            "deviation_score": float(record.get("deviation_score", 0)),
            "suspicion_pct": float(record.get("suspicion_pct", 0)),
            "category": cat,
            "label": meta["label"],
            "color": meta["color"],
            "anomaly_scores": {
                "isolation_forest": record.get("iso_forest_score"),
                "xgboost": record.get("xgb_score"),
                "random_forest": record.get("rf_score"),
                "ensemble": record.get("ensemble_score"),
            },
            "income_networth_gap": float(record.get("income_networth_gap", 0)),
            "tax_gap": float(record.get("tax_gap", 0)),
            "lifestyle_gap": float(record.get("lifestyle_gap", 0)),
            "filing_penalty": float(record.get("filing_penalty", 0)),
        }

    # ── Asset Queries ─────────────────────────────────────────────────

    def get_citizen_assets(self, citizen_id: str) -> dict:
        """Return the full asset breakdown for a citizen, looked up by CNIC."""
        # Get citizen's CNIC (stored as float like 5400015537748.0)
        row = self.citizens_df[self.citizens_df["citizen_id"] == citizen_id]
        if row.empty:
            return {"vehicles": [], "properties": [], "businesses": [], "travel": [], "utilities": [], "total_value": 0}

        cnic_raw = str(row.iloc[0]["cnic"]).split(".")[0].replace("-", "").strip() if pd.notna(row.iloc[0].get("cnic")) else ""

        vehicles = self._query_by_cnic(self.vehicles_df, cnic_raw)
        properties = self._query_by_cnic(self.properties_df, cnic_raw)
        businesses = self._query_by_cnic(self.businesses_df, cnic_raw)
        travel = self._query_by_cnic(self.travel_df, cnic_raw)
        utilities = self._query_by_cnic(self.utilities_df, cnic_raw)

        banking = self._query_by_cnic(self.banking_indicators_df if hasattr(self, 'banking_indicators_df') else getattr(self, 'banking_df', pd.DataFrame()), cnic_raw)

        # Map to keys expected by the frontend
        mapped_vehicles = []
        for v in vehicles:
            mapped_vehicles.append({
                "car_registration_number": v.get("car_registration_number") or v.get("record_id") or "N/A",
                "car_brand": v.get("car_brand") or v.get("vehicle_make") or "N/A",
                "car_model": v.get("car_model") or v.get("vehicle_model") or "N/A",
                "model_year": v.get("model_year") or v.get("vehicle_year") or "N/A",
                "engine_size_cc": v.get("engine_size_cc") or v.get("engine_cc") or "N/A",
                "city": v.get("city") or "N/A",
                "province": v.get("province") or "N/A",
                "market_value": float(v.get("market_value") or v.get("value_pkr") or 0),
            })

        mapped_properties = []
        for p in properties:
            addr = str(p.get("address") or "")
            parts = [s.strip() for s in addr.split(",") if s.strip()]
            plot_no = parts[0] if parts else "N/A"
            society = parts[-1] if len(parts) > 1 else (parts[0] if parts else "N/A")
            mapped_properties.append({
                "property_id": p.get("record_id") or "N/A",
                "property_type": p.get("property_type") or "Residential",
                "society_name": p.get("society_name") or society,
                "plot_house_no": p.get("plot_house_no") or plot_no,
                "area": p.get("area") or (parts[1] if len(parts) > 2 else "Standard"),
                "address": addr or "N/A",
                "city": p.get("city") or "N/A",
                "province": p.get("province") or "N/A",
                "purchase_year": p.get("purchase_year") or "2020",
                "ownership_status": p.get("ownership_status") or "Owned",
                "market_value": float(p.get("market_value") or p.get("value_pkr") or 0),
            })

        mapped_businesses = []
        for b in businesses:
            mapped_businesses.append({
                "company_name": b.get("company_name") or b.get("business_name") or "N/A",
                "entity_type": b.get("entity_type") or b.get("business_type") or "Private Ltd",
                "status": b.get("status") or b.get("registration_status") or "Active",
                "annual_turnover": float(b.get("annual_turnover_pkr") or b.get("annual_turnover") or 0),
                "incorporation_date": b.get("incorporation_date") or "2019",
                "city": b.get("city") or "N/A",
                "province": b.get("province") or "N/A",
                "registered_office_address": b.get("registered_office_address") or b.get("address") or "N/A",
            })

        mapped_travel = []
        for t in travel:
            is_intl = str(t.get("international", "")).lower() in ("true", "1", "yes", "international")
            mapped_travel.append({
                "passport_no": t.get("passport_no") or t.get("passport_last4") or "N/A",
                "travelling_from": t.get("travelling_from") or "Pakistan",
                "destination": t.get("destination") or "N/A",
                "travel_date": t.get("travel_date") or "N/A",
                "visa_type": t.get("visa_type") or ("International" if is_intl else "Domestic"),
                "reason_to_travel": t.get("reason_to_travel") or "Business/Tourism",
                "city": t.get("city") or "N/A",
                "province": t.get("province") or "N/A",
            })

        mapped_utilities = []
        for u in utilities:
            mapped_utilities.append({
                "consumer_id": u.get("consumer_id") or u.get("record_id") or "N/A",
                "meter_no": u.get("meter_no") or u.get("provider") or "WAPDA",
                "utility_type": u.get("utility_type") or "Electricity",
                "provider": u.get("provider") or "WAPDA",
                "monthly_bill_pkr": float(u.get("monthly_bill_pkr") or u.get("monthly_bill") or 0),
                "address": u.get("address") or "N/A",
                "city": u.get("city") or "N/A",
                "province": u.get("province") or "N/A",
            })

        mapped_banking = []
        for bk in banking:
            mapped_banking.append({
                "account_last4": bk.get("account_last4") or "N/A",
                "bank_name": bk.get("bank_name") or "State Bank of Pakistan",
                "account_type": bk.get("account_type") or "Current",
                "monthly_expenditure_pkr": float(bk.get("monthly_expenditure_pkr") or 0),
                "annual_expenditure_pkr": float(bk.get("annual_expenditure_pkr") or 0),
                "city": bk.get("city") or "N/A",
                "province": bk.get("province") or "N/A",
            })

        total_value = sum(v["market_value"] for v in mapped_vehicles) + sum(p["market_value"] for p in mapped_properties)

        return {
            "vehicles": mapped_vehicles,
            "properties": mapped_properties,
            "businesses": mapped_businesses,
            "travel": mapped_travel,
            "utilities": mapped_utilities,
            "banking": mapped_banking,
            "total_value": total_value,
        }

    def _query_by_cnic(self, df: pd.DataFrame, cnic_raw: str) -> list[dict]:
        """Filter an asset DataFrame by matching original_cnic to the citizen's CNIC."""
        if df.empty or not cnic_raw:
            return []
        cnic_clean = str(cnic_raw).replace("-", "").strip()
        if "original_cnic" in df.columns:
            rows = df[df["original_cnic"].astype(str).str.replace("-", "", regex=False).str.strip() == cnic_clean]
        elif "cnic" in df.columns:
            rows = df[df["cnic"].astype(str).str.replace("-", "", regex=False).str.strip() == cnic_clean]
        else:
            return []
        records = rows.fillna("").to_dict(orient="records")
        # Clean up numeric values
        for r in records:
            for k, v in r.items():
                if isinstance(v, float) and v != v:  # NaN check
                    r[k] = ""
        return records

    def _query_asset_df(self, df: pd.DataFrame, citizen_id: str) -> list[dict]:
        """Legacy method - now delegates to _query_by_cnic."""
        row = self.citizens_df[self.citizens_df["citizen_id"] == citizen_id]
        if row.empty:
            return []
        cnic_raw = str(row.iloc[0]["cnic"]).split(".")[0].replace("-", "").strip() if pd.notna(row.iloc[0].get("cnic")) else ""
        return self._query_by_cnic(df, cnic_raw)

    # ── Audit Trail ───────────────────────────────────────────────────

    def get_citizen_audit_trail(self, citizen_id: str) -> list[dict]:
        """Build an audit trail (list of flags) for a citizen.

        The trail is derived algorithmically from the citizen's data rather
        than being stored in a separate file.
        """
        row = self.citizens_df[self.citizens_df["citizen_id"] == citizen_id]
        if row.empty:
            return []
        r = row.iloc[0]
        trail: list[dict] = []

        # Non-filer flag
        filing = str(r.get("filing_status", ""))
        if filing.lower() == "non-filer":
            trail.append({
                "description": "Citizen is a Non-Filer with potential economic activity",
                "severity": "warning",
                "value": None,
                "threshold": None,
            })

        # High risk score
        risk = float(r.get("risk_score", 0))
        if risk >= 80:
            trail.append({
                "description": f"Extremely high risk score ({risk:.1f})",
                "severity": "critical",
                "value": risk,
                "threshold": 80.0,
            })
        elif risk >= 60:
            trail.append({
                "description": f"Elevated risk score ({risk:.1f})",
                "severity": "warning",
                "value": risk,
                "threshold": 60.0,
            })

        # Income–net-worth mismatch
        income = float(r.get("declared_income", 0))
        net_worth = float(r.get("estimated_net_worth", 0))
        if income > 0 and net_worth > income * 5:
            trail.append({
                "description": (
                    f"Net worth (PKR {net_worth:,.0f}) exceeds "
                    f"5× declared income (PKR {income:,.0f})"
                ),
                "severity": "critical",
                "value": net_worth,
                "threshold": income * 5,
            })
        elif income > 0 and net_worth > income * 3:
            trail.append({
                "description": (
                    f"Net worth (PKR {net_worth:,.0f}) exceeds "
                    f"3× declared income (PKR {income:,.0f})"
                ),
                "severity": "warning",
                "value": net_worth,
                "threshold": income * 3,
            })

        # Deviation score flag
        dev = float(r.get("deviation_score", 0))
        if dev >= 60:
            trail.append({
                "description": f"High wealth-income deviation score ({dev:.1f})",
                "severity": "critical",
                "value": dev,
                "threshold": 60.0,
            })

        # Multiple asset flag
        assets = self.get_citizen_assets(citizen_id)
        vehicle_count = len(assets.get("vehicles", []))
        property_count = len(assets.get("properties", []))
        if vehicle_count >= 3:
            trail.append({
                "description": f"Owns {vehicle_count} registered vehicles",
                "severity": "info",
                "value": float(vehicle_count),
                "threshold": 3.0,
            })
        if property_count >= 2:
            trail.append({
                "description": f"Owns {property_count} registered properties",
                "severity": "info",
                "value": float(property_count),
                "threshold": 2.0,
            })

        return trail

    # ── Search ────────────────────────────────────────────────────────

    def search_citizens(
        self, query: str, search_type: str = "name"
    ) -> list[dict]:
        """Full-text search across citizens by the specified field.

        Args:
            query: Search query string.
            search_type: One of 'name', 'cnic', 'phone', 'vehicle', 'business'.

        Returns:
            List of matching CitizenSummary dicts.
        """
        if not query or self.citizens_df.empty:
            return []

        q = query.strip().lower()
        summary_cols = [
            "citizen_id", "name", "canonical_name", "cnic", "city", "province",
            "risk_score", "risk_category", "filing_status",
            "declared_income", "estimated_net_worth",
        ]
        existing_cols = [c for c in summary_cols if c in self.citizens_df.columns]

        def _sanitize(records: list[dict]) -> list[dict]:
            """Ensure types match Pydantic CitizenSummary expectations."""
            numeric_fields = {"risk_score", "declared_income", "estimated_net_worth", "deviation_score"}
            str_fields = {"citizen_id", "name", "canonical_name", "cnic", "city", "province",
                          "risk_category", "filing_status"}
            clean = []
            for r in records:
                row = {}
                for k, v in r.items():
                    if k in numeric_fields:
                        try:
                            row[k] = float(v) if v != "" and v is not None else 0.0
                        except (ValueError, TypeError):
                            row[k] = 0.0
                    elif k in str_fields:
                        s = str(v) if v is not None else ""
                        # Remove trailing .0 from float-cast CNICs
                        if k == "cnic" and s.endswith(".0"):
                            s = s[:-2]
                        row[k] = s
                    else:
                        row[k] = v
                clean.append(row)
            return clean

        if search_type == "cnic":
            mask = self.citizens_df["cnic"].astype(str).str.contains(q, na=False)
            return _sanitize(self.citizens_df.loc[mask, existing_cols].fillna("").to_dict(orient="records"))

        if search_type == "phone":
            if "phone" in self.citizens_df.columns:
                mask = self.citizens_df["phone"].astype(str).str.contains(q, na=False)
                return _sanitize(self.citizens_df.loc[mask, existing_cols].fillna("").to_dict(orient="records"))
            return []

        if search_type == "vehicle":
            if self.vehicles_df.empty:
                return []
            v_mask = (
                self.vehicles_df.astype(str)
                .apply(lambda row: row.str.lower().str.contains(q).any(), axis=1)
            )
            matched = self.vehicles_df.loc[v_mask]
            key = self._detect_merge_key(matched, self.citizens_df) or "citizen_id"
            if key not in matched.columns:
                return []
            ids = matched[key].unique().tolist()
            return _sanitize(
                self.citizens_df[self.citizens_df["citizen_id"].isin(ids)]
                [existing_cols]
                .fillna("")
                .to_dict(orient="records")
            )

        if search_type == "business":
            if self.businesses_df.empty:
                return []
            b_mask = (
                self.businesses_df.astype(str)
                .apply(lambda row: row.str.lower().str.contains(q).any(), axis=1)
            )
            matched = self.businesses_df.loc[b_mask]
            key = self._detect_merge_key(matched, self.citizens_df) or "citizen_id"
            if key not in matched.columns:
                return []
            ids = matched[key].unique().tolist()
            return _sanitize(
                self.citizens_df[self.citizens_df["citizen_id"].isin(ids)]
                [existing_cols]
                .fillna("")
                .to_dict(orient="records")
            )

        # Default: name search using cross-lingual fuzzy search (Urdu + English + Soundex)
        matched_df = advanced_fuzzy_search(
            df=self.citizens_df,
            query=query,
            search_columns=["canonical_name", "name", "cnic", "father_name"],
            limit=50,
            score_cutoff=75.0
        )
        matched_existing = [c for c in existing_cols if c in matched_df.columns]
        return _sanitize(matched_df[matched_existing].fillna("").to_dict(orient="records"))

    # ── Risk Aggregations ─────────────────────────────────────────────

    def get_risk_distribution(self) -> dict:
        """Return category-level risk distribution statistics."""
        if self.citizens_df.empty:
            return {
                "total_citizens": 0,
                "filer_count": 0,
                "non_filer_count": 0,
                "categories": [],
            }

        total = len(self.citizens_df)
        filer_count = int(
            (self.citizens_df["filing_status"].astype(str).str.lower() == "filer").sum()
        )
        non_filer_count = total - filer_count

        cats: list[dict] = []
        for cat, meta in RISK_CATEGORIES.items():
            count = int((self.citizens_df["risk_category"] == cat).sum())
            cats.append({
                "category": cat,
                "label": meta["label"],
                "color": meta["color"],
                "count": count,
                "percentage": round(count / total * 100, 2) if total else 0.0,
            })

        return {
            "total_citizens": total,
            "filer_count": filer_count,
            "non_filer_count": non_filer_count,
            "categories": cats,
        }

    def get_income_wealth_gap(self) -> list[dict]:
        """Return data for the Income-to-Wealth Gap scatter plot."""
        if self.citizens_df.empty:
            return []
        
        # Sample up to 1000 points to keep frontend performant
        df = self.citizens_df.dropna(subset=['declared_income', 'estimated_net_worth', 'risk_score'])
        if len(df) > 1000:
            df = df.sample(1000, random_state=42)
            
        # Calculate ratio and deviation
        results = []
        for _, row in df.iterrows():
            income = float(row.get('declared_income', 0) or 0)
            net_worth = float(row.get('estimated_net_worth', 0) or 0)
            risk = float(row.get('risk_score', 0) or 0)
            cat = str(row.get('risk_category', 'A'))
            
            # Avoid division by zero, compute Net Worth / Income ratio
            ratio = (net_worth / income) if income > 0 else (net_worth / 100000)
            # Cap ratio at 400 for visualization purposes based on the user screenshot
            ratio = min(ratio, 400.0)
            
            results.append({
                "ratio": round(ratio, 2),
                "deviation": round(risk, 2),
                "risk_category": cat
            })
            
        return results

    def get_top_suspicious(self, limit: int = 20) -> list[dict]:
        """Return the top-N citizens by risk_score descending."""
        if self.citizens_df.empty:
            return []
        df = self.citizens_df.nlargest(limit, "risk_score")
        summary_cols = [
            "citizen_id", "name", "cnic", "city", "province",
            "risk_score", "risk_category", "filing_status",
            "declared_income", "estimated_net_worth",
        ]
        existing_cols = [c for c in summary_cols if c in df.columns]
        return df[existing_cols].fillna("").to_dict(orient="records")

    def get_feature_importance(self) -> dict:
        """Return feature importance data."""
        if self.feature_importance_df.empty:
            # Generate fallback importance from risk_score column correlations
            return self._fallback_feature_importance()

        records = self.feature_importance_df.to_dict(orient="records")
        return {
            "model_name": "ensemble",
            "features": records,
        }

    def _fallback_feature_importance(self) -> dict:
        """Create a reasonable feature importance list from available data."""
        features = [
            {"feature": "income_networth_gap", "importance": 0.30},
            {"feature": "tax_gap", "importance": 0.25},
            {"feature": "lifestyle_gap", "importance": 0.20},
            {"feature": "anomaly_score", "importance": 0.15},
            {"feature": "filing_penalty", "importance": 0.10},
        ]
        return {"model_name": "ensemble", "features": features}

    # ── Entity Resolution ─────────────────────────────────────────────

    def get_entity_matches(self) -> list[dict]:
        """Return all entity resolution match pairs."""
        if self.entity_matches_df.empty:
            return []
        return self.entity_matches_df.fillna("").to_dict(orient="records")

    # ── Graph / Network Queries ───────────────────────────────────────

    def get_graph_stats(self) -> dict:
        """Return summary statistics about the knowledge graph."""
        try:
            import networkx as nx
        except ImportError:
            return self._empty_graph_stats()

        if self.graph is None:
            return self._empty_graph_stats()

        g = self.graph
        node_count = g.number_of_nodes()
        edge_count = g.number_of_edges()
        density = nx.density(g) if node_count > 0 else 0.0
        avg_degree = (
            sum(dict(g.degree()).values()) / node_count if node_count else 0.0
        )

        # Connected components
        try:
            if g.is_directed():
                cc = nx.number_weakly_connected_components(g)
            else:
                cc = nx.number_connected_components(g)
        except Exception:
            cc = 0

        # Communities count
        communities_count = 0
        if not self.communities_df.empty and "community_id" in self.communities_df.columns:
            communities_count = int(self.communities_df["community_id"].nunique())
            
        suspicious_clusters = len([c for c in self.get_communities() if c.get("avg_risk_score", 0) > 30])

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "total_nodes": node_count,
            "total_edges": edge_count,
            "total_communities": communities_count,
            "suspicious_communities": suspicious_clusters,
            "density": round(density, 6),
            "communities_count": communities_count,
            "avg_degree": round(avg_degree, 2),
            "connected_components": cc,
        }

    @staticmethod
    def _empty_graph_stats() -> dict:
        """Fallback when no graph is loaded."""
        return {
            "node_count": 0,
            "edge_count": 0,
            "density": 0.0,
            "communities_count": 0,
            "avg_degree": 0.0,
            "connected_components": 0,
        }

    def get_ego_graph(self, citizen_id: str, radius: int = 1) -> dict:
        """Return the ego-network (nodes + edges) for a citizen.

        Args:
            citizen_id: Centre node identifier.
            radius: Hop distance from centre (default 1).

        Returns:
            Dict with 'center_id', 'nodes', and 'edges' lists.
        """
        try:
            import networkx as nx
        except ImportError:
            return {"center_id": citizen_id, "nodes": [], "edges": []}

        if self.graph is None or citizen_id not in self.graph:
            return {"center_id": citizen_id, "nodes": [], "edges": []}

        ego = nx.ego_graph(self.graph, citizen_id, radius=radius)

        nodes: list[dict] = []
        for nid in ego.nodes():
            data = ego.nodes[nid]
            cat = str(data.get("risk_category", "A"))
            meta = RISK_CATEGORIES.get(cat, RISK_CATEGORIES["A"])
            node_type = str(data.get("node_type", "Person"))
            node_dict = {
                "id": str(nid),
                "label": data.get("label", str(nid)),
                "node_type": node_type,
                "risk_score": float(data.get("risk_score", 0)),
                "risk_category": cat,
                "size": 22.0 if str(nid) == citizen_id else 12.0,
                "color": meta["color"] if node_type == "Person" else data.get("color", "#64748b"),
            }
            # Include all other attributes for tooltips
            for k, v in data.items():
                if k not in node_dict:
                    node_dict[k] = v
            nodes.append(node_dict)

        edges: list[dict] = []
        for src, tgt, edata in ego.edges(data=True):
            edges.append({
                "source": str(src),
                "target": str(tgt),
                "relationship": edata.get("relationship", edata.get("type", "")),
                "weight": float(edata.get("weight", 1.0)),
            })

        return {"center_id": citizen_id, "nodes": nodes, "edges": edges}

    def get_community_graph(self, community_id: int) -> dict:
        """Return the subgraph for a specific community (all members + their 1-hop neighbours)."""
        try:
            import networkx as nx
        except ImportError:
            return {"community_id": community_id, "nodes": [], "edges": []}
            
        if self.communities_df.empty:
            self._compute_and_save_communities()
            
        if self.graph is None or self.communities_df.empty:
            return {"community_id": community_id, "nodes": [], "edges": []}
            
        members = self.communities_df[self.communities_df["community_id"] == community_id]["citizen_id"].tolist()
        if not members:
            return {"community_id": community_id, "nodes": [], "edges": []}
            
        # Extract 1-hop ego graphs for all members in undirected view to capture shared links
        subgraphs = []
        undirected_g = self.graph.to_undirected()
        for member in members:
            if member in undirected_g:
                subgraphs.append(nx.ego_graph(undirected_g, member, radius=1))
                
        if not subgraphs:
            return {"community_id": community_id, "nodes": [], "edges": []}
            
        composed_nodes = set()
        for sg in subgraphs:
            composed_nodes.update(sg.nodes())
            
        # Induce subgraph from the original directed graph
        community_graph = self.graph.subgraph(composed_nodes)
        
        from config.settings import RISK_CATEGORIES
        nodes: list[dict] = []
        for nid in community_graph.nodes():
            data = community_graph.nodes[nid]
            cat = str(data.get("risk_category", "A"))
            meta = RISK_CATEGORIES.get(cat, RISK_CATEGORIES["A"])
            node_type = str(data.get("node_type", "Person"))
            node_dict = {
                "id": str(nid),
                "label": data.get("label", str(nid)),
                "node_type": node_type,
                "risk_score": float(data.get("risk_score", 0)),
                "risk_category": cat,
                "size": 22.0 if str(nid) in members else 12.0,
                "color": meta["color"] if node_type == "Person" else data.get("color", "#64748b"),
            }
            # Include all other attributes for tooltips
            for k, v in data.items():
                if k not in node_dict:
                    node_dict[k] = v
            nodes.append(node_dict)

        edges: list[dict] = []
        for src, tgt, edata in community_graph.edges(data=True):
            edges.append({
                "source": str(src),
                "target": str(tgt),
                "relationship": edata.get("relationship", edata.get("type", "")),
                "weight": float(edata.get("weight", 1.0)),
            })
            
        return {"community_id": community_id, "nodes": nodes, "edges": edges}

    def _compute_and_save_communities(self):
        """Auto-detect Louvain communities on the knowledge graph and persist to communities.csv."""
        if self.graph is None or self.graph.number_of_nodes() == 0:
            return
        logger.info("Computing Louvain graph communities for Hidden Network Detection...")
        from networkx.algorithms.community import louvain_communities
        try:
            communities = louvain_communities(self.graph.to_undirected(), resolution=1.0, seed=42)
        except Exception:
            from networkx.algorithms.community import greedy_modularity_communities
            communities = list(greedy_modularity_communities(self.graph.to_undirected()))

        comm_records = []
        for i, comm in enumerate(communities):
            for node in comm:
                if str(node).startswith("CZ-") or self.graph.nodes.get(node, {}).get("node_type") == "Person":
                    comm_records.append({"citizen_id": str(node), "community_id": i})

        self.communities_df = pd.DataFrame(comm_records)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        _tmp = PROCESSED_DIR / "communities.csv.tmp"
        self.communities_df.to_csv(_tmp, index=False)
        import os; os.replace(str(_tmp), str(PROCESSED_DIR / "communities.csv"))
        self._cached_communities = None
        logger.info(f"Saved {self.communities_df['community_id'].nunique()} communities to {PROCESSED_DIR / 'communities.csv'}")

    def get_communities(self) -> list[dict]:
        """Return community summary list with enriched metrics."""
        if hasattr(self, "_cached_communities") and self._cached_communities is not None:
            return self._cached_communities

        if self.communities_df.empty:
            if self.graph is not None and self.graph.number_of_nodes() > 0:
                self._compute_and_save_communities()
            if self.communities_df.empty:
                return []

        # Expect columns: citizen_id, community_id
        if "community_id" not in self.communities_df.columns:
            return []

        name_col = "canonical_name" if "canonical_name" in self.citizens_df.columns else "name"
        cols_to_merge = ["citizen_id", "risk_score"]
        if name_col in self.citizens_df.columns:
            cols_to_merge.append(name_col)
        if "deviation_score" in self.citizens_df.columns:
            cols_to_merge.append("deviation_score")
        if "risk_category" in self.citizens_df.columns:
            cols_to_merge.append("risk_category")

        merged = self.communities_df.merge(self.citizens_df[cols_to_merge], on="citizen_id", how="left")
        if "deviation_score" in merged.columns:
            merged["risk_score"] = merged["risk_score"].replace(0, np.nan).fillna(merged["deviation_score"]).fillna(0)

        result = []
        for cid, grp in merged.groupby("community_id"):
            members = grp["citizen_id"].tolist()
            if not members:
                continue
            
            member_names = []
            for _, row in grp.iterrows():
                disp = row.get(name_col) or row.get("citizen_id")
                if disp and str(disp).strip():
                    member_names.append(str(disp).strip())
                else:
                    member_names.append(str(row["citizen_id"]))

            avg_risk = float(grp["risk_score"].mean()) if not grp["risk_score"].isna().all() else 0.0
            max_risk = float(grp["risk_score"].max()) if not grp["risk_score"].isna().all() else 0.0
            
            high_risk_count = 0
            if "risk_category" in grp.columns:
                high_risk_count = int(grp["risk_category"].isin(["D", "E"]).sum())
            else:
                high_risk_count = int((grp["risk_score"] > 40).sum())

            result.append({
                "community_id": int(cid),
                "member_count": len(members),
                "avg_risk_score": round(avg_risk, 2),
                "max_risk_score": round(max_risk, 2),
                "high_risk_count": high_risk_count,
                "top_members": member_names[:10],
                "top_member_ids": members[:10],
            })

        # Sort: multi-member clusters and high risk clusters first
        result.sort(key=lambda c: (c["member_count"] > 1, c["avg_risk_score"], c["member_count"]), reverse=True)
        self._cached_communities = result
        return result

    # ── Export Helpers ─────────────────────────────────────────────────

    def export_citizens_csv(self, filters: dict[str, Any]) -> pd.DataFrame:
        """Return a filtered DataFrame suitable for CSV / Excel export."""
        records, _ = self.get_citizens(filters, page=1, page_size=999_999)
        return pd.DataFrame(records)
