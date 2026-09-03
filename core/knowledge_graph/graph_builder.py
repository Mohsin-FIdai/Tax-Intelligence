"""
Knowledge Graph Builder — Constructs a comprehensive graph from citizen profiles and assets.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import PROCESSED_DIR, MODELS_DIR, THEME

# ─── Node-type colour palette ──────────────────────────────────────
NODE_COLORS = {
    "Person": "#00d4aa",
    "Vehicle": "#4a9eff",
    "Property": "#ff8c00",
    "Utility": "#ffd000",
    "Business": "#9b59b6",
    "TaxReturn": "#2ecc71",
    "Phone": "#1abc9c",
    "BankAccount": "#e74c3c",
    "Travel": "#3498db",
    "Company": "#9b59b6",
    "Address": "#95a5a6",
}

EDGE_TYPES = [
    "OWNS", "PAYS", "LIVES_AT", "DIRECTOR_OF", "USES",
    "TRAVELLED_TO", "HAS_TAX_RETURN", "CONNECTED_TO",
    "SHARES_ADDRESS", "SHARES_PHONE",
]


def _safe_float(val: Any) -> float:
    try:
        if pd.isna(val) or val == "":
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _clean_cnic(val: Any) -> str:
    """Normalize CNIC string representations to ensure robust matching across int/float/str casting."""
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.lower() in ("nan", "none", "unknown"):
        return ""
    return s.replace("-", "")


class KnowledgeGraphBuilder:
    """Build a directed knowledge graph from resolved citizen data."""

    def __init__(self):
        self.G: nx.DiGraph = nx.DiGraph()

    def build_graph(
        self,
        citizens_df: pd.DataFrame,
        vehicles_df: pd.DataFrame | None = None,
        properties_df: pd.DataFrame | None = None,
        utilities_df: pd.DataFrame | None = None,
        travel_df: pd.DataFrame | None = None,
        business_df: pd.DataFrame | None = None,
        banking_df: pd.DataFrame | None = None,
        mobile_df: pd.DataFrame | None = None,
    ) -> nx.DiGraph:
        """Construct the full knowledge graph.

        Parameters
        ----------
        citizens_df : Master citizen profiles (must have ``citizen_id``, ``cnic``).
        *_df : Optional asset DataFrames linked by ``cnic``.
        """
        self.G.clear()
        cnic_to_cid: dict[str, str] = {}

        # ── Person nodes ────────────────────────────────────────────
        for row in citizens_df.to_dict('records'):
            cid = str(row.get("citizen_id", ""))
            cnic = _clean_cnic(row.get("cnic"))
            if cid:
                self.G.add_node(cid,
                    label=str(row.get("canonical_name", cid)),
                    node_type="Person",
                    color=NODE_COLORS["Person"],
                    cnic=cnic,
                    city=str(row.get("city", "")),
                    province=str(row.get("province", "")),
                    risk_score=_safe_float(row.get("deviation_score", 0)),
                    risk_category=str(row.get("risk_category", "")),
                    filing_status=str(row.get("filing_status", "")),
                    declared_income=_safe_float(row.get("declared_income", 0)),
                    contact_no=str(row.get("phone", row.get("contact_no", ""))),
                )
                if cnic:
                    cnic_to_cid[cnic] = cid

        # ── Vehicle nodes ───────────────────────────────────────────
        if vehicles_df is not None:
            for row in vehicles_df.to_dict('records'):
                cnic = _clean_cnic(row.get("cnic"))
                cid = cnic_to_cid.get(cnic)
                if not cid:
                    continue
                vid = f"VEH-{row.get('record_id', str(hash(str(row)))[:8])}"
                label = f"{row.get('vehicle_make', '')} {row.get('vehicle_model', '')}".strip()
                self.G.add_node(vid,
                    label=label or vid,
                    node_type="Vehicle",
                    color=NODE_COLORS["Vehicle"],
                    reg_no=str(row.get("car_registration_number", row.get("registration_number", ""))),
                    market_value=_safe_float(row.get("market_value", 0)),
                    vehicle_type=str(row.get("vehicle_type", "")),
                    car_model=str(row.get("car_model", "")),
                    model_year=str(row.get("model_year", "")),
                    car_brand=str(row.get("car_brand", row.get("vehicle_make", ""))),
                    engine_size_cc=str(row.get("engine_size_cc", "")),
                )
                self.G.add_edge(cid, vid, relationship="OWNS",
                                weight=_safe_float(row.get("market_value", 0)))

        # ── Property nodes ──────────────────────────────────────────
        if properties_df is not None:
            for row in properties_df.to_dict('records'):
                cnic = _clean_cnic(row.get("cnic"))
                cid = cnic_to_cid.get(cnic)
                if not cid:
                    continue
                pid = f"PROP-{row.get('record_id', str(hash(str(row)))[:8])}"
                self.G.add_node(pid,
                    label=f"{row.get('property_type', 'Property')} - {row.get('area_name', '')}",
                    node_type="Property",
                    color=NODE_COLORS["Property"],
                    property_value=_safe_float(row.get("property_value", row.get("market_value", 0))),
                    property_type=str(row.get("property_type", "")),
                    city=str(row.get("city", "")),
                    size_marla=_safe_float(row.get("size_marla", 0)),
                    plot_house_no=str(row.get("plot_house_no", "")),
                    society_name=str(row.get("society_name", "")),
                    area=str(row.get("area", "")),
                    ownership_status=str(row.get("ownership_status", "")),
                    market_value=_safe_float(row.get("market_value", 0)),
                )
                self.G.add_edge(cid, pid, relationship="OWNS",
                                weight=_safe_float(row.get("property_value", row.get("market_value", 0))))

                # City node
                city_name = str(row.get("city", "")).strip().title()
                if city_name and city_name.lower() not in ["", "nan", "none", "unknown"]:
                    city_id = f"CITY-{hash(city_name.lower()) % 10**8}"
                    if not self.G.has_node(city_id):
                        self.G.add_node(city_id, label=city_name, node_type="City", color="#ffaa00")
                    self.G.add_edge(pid, city_id, relationship="LOCATED_IN")
                    self.G.add_edge(cid, city_id, relationship="OWNS_PROPERTY_IN")

                # Address node
                addr = str(row.get("address", ""))
                if addr:
                    addr_id = f"ADDR-{hash(addr) % 10**8}"
                    if not self.G.has_node(addr_id):
                        self.G.add_node(addr_id, label=addr[:50], node_type="Address",
                                        color=NODE_COLORS["Address"])
                    self.G.add_edge(cid, addr_id, relationship="LIVES_AT")

        # ── Utility nodes ───────────────────────────────────────────
        if utilities_df is not None:
            for row in utilities_df.to_dict('records'):
                cnic = _clean_cnic(row.get("cnic"))
                cid = cnic_to_cid.get(cnic)
                if not cid:
                    continue
                uid = f"UTIL-{row.get('record_id', str(hash(str(row)))[:8])}"
                
                # Deduce utility type if possible
                utype = str(row.get("utility_type", ""))
                if not utype:
                    if "gas" in str(row.get("consumer_id", "")).lower() or "ssgc" in str(row.get("provider", "")).lower():
                        utype = "Gas"
                    else:
                        utype = "Electricity"

                self.G.add_node(uid,
                    label=f"{utype} - {row.get('consumer_id', uid)}",
                    node_type="Utility",
                    color=NODE_COLORS["Utility"],
                    monthly_amount=_safe_float(row.get("monthly_amount", 0)),
                    utility_type=utype,
                    consumer_id=str(row.get("consumer_id", uid)),
                    meter_no=str(row.get("meter_no", "")),
                )
                self.G.add_edge(cid, uid, relationship="PAYS",
                                weight=_safe_float(row.get("monthly_amount", 0)))

        # ── Travel nodes ────────────────────────────────────────────
        if travel_df is not None:
            for row in travel_df.to_dict('records'):
                cnic = _clean_cnic(row.get("cnic"))
                cid = cnic_to_cid.get(cnic)
                if not cid:
                    continue
                tid = f"TRVL-{row.get('record_id', str(hash(str(row)))[:8])}"
                self.G.add_node(tid,
                    label=f"{row.get('destination', '')} ({row.get('travel_class', '')})",
                    node_type="Travel",
                    color=NODE_COLORS["Travel"],
                    destination=str(row.get("destination", "")),
                    airline=str(row.get("airline", "")),
                    travel_class=str(row.get("travel_class", "")),
                    passport_no=str(row.get("passport_no", "")),
                    visa_type=str(row.get("visa_type", "")),
                    reason_to_travel=str(row.get("reason_to_travel", "")),
                )
                self.G.add_edge(cid, tid, relationship="TRAVELLED_TO")

        # ── Business nodes ──────────────────────────────────────────
        if business_df is not None:
            for row in business_df.to_dict('records'):
                cnic = _clean_cnic(row.get("cnic"))
                cid = cnic_to_cid.get(cnic)
                if not cid:
                    continue
                bid = f"BIZ-{row.get('record_id', str(hash(str(row)))[:8])}"
                self.G.add_node(bid,
                    label=str(row.get("company_name", row.get("business_name", bid))),
                    node_type="Company",
                    color=NODE_COLORS["Company"],
                    business_type=str(row.get("business_type", "")),
                    annual_revenue=_safe_float(row.get("annual_revenue", 0)),
                    city=str(row.get("city", "")),
                    company_name=str(row.get("company_name", "")),
                    entity_type=str(row.get("entity_type", "")),
                    status=str(row.get("status", "")),
                    registered_office_address=str(row.get("registered_office_address", "")),
                )
                role = str(row.get("role", "OWNS"))
                rel = "DIRECTOR_OF" if "director" in role.lower() else "OWNS"
                self.G.add_edge(cid, bid, relationship=rel,
                                share_pct=_safe_float(row.get("share_percentage", 0)))

        # ── Phone nodes ─────────────────────────────────────────────
        if mobile_df is not None:
            phone_owners: dict[str, list[str]] = {}
            for row in mobile_df.to_dict('records'):
                cnic = _clean_cnic(row.get("cnic"))
                cid = cnic_to_cid.get(cnic)
                phone = str(row.get("phone_number", ""))
                if not cid or not phone:
                    continue
                phone_id = f"PHN-{phone.replace('-', '')}"
                if not self.G.has_node(phone_id):
                    self.G.add_node(phone_id, label=phone, node_type="Phone",
                                    color=NODE_COLORS["Phone"],
                                    annual_recharge_amount=_safe_float(row.get("annual_recharge_amount", 0)),
                                    original_phone=str(row.get("original_phone", "")))
                self.G.add_edge(cid, phone_id, relationship="USES")
                phone_owners.setdefault(phone, []).append(cid)

            # SHARES_PHONE edges
            for phone, owners in phone_owners.items():
                if len(owners) > 1:
                    for i in range(len(owners)):
                        for j in range(i + 1, len(owners)):
                            self.G.add_edge(owners[i], owners[j],
                                            relationship="SHARES_PHONE",
                                            shared_phone=phone)

        # ── Banking nodes ───────────────────────────────────────────
        if banking_df is not None:
            for row in banking_df.to_dict('records'):
                cnic = _clean_cnic(row.get("cnic"))
                cid = cnic_to_cid.get(cnic)
                if not cid:
                    continue
                bkid = f"BANK-{row.get('record_id', str(hash(str(row)))[:8])}"
                
                acc_last4 = str(row.get("account_last4", ""))
                bank_name_val = str(row.get("bank_name", "Bank")).strip()
                acc_type = str(row.get("account_type", "Current")).strip()
                m_exp = _safe_float(row.get("monthly_expenditure_pkr", row.get("monthly_expenditure", 0)))
                a_exp = _safe_float(row.get("annual_expenditure_pkr", row.get("annual_expenditure", 0)))
                
                label = f"Acct: ****{acc_last4} ({bank_name_val})" if acc_last4 else f"Acct ({bank_name_val})"

                self.G.add_node(bkid,
                    label=label,
                    node_type="BankAccount",
                    color=NODE_COLORS["BankAccount"],
                    account_last4=acc_last4,
                    account_number=f"****{acc_last4}",
                    bank_name=bank_name_val,
                    account_type=acc_type,
                    monthly_expenditure=m_exp,
                    annual_expenditure=a_exp,
                    monthly_expenditure_pkr=m_exp,
                    annual_expenditure_pkr=a_exp,
                    city=str(row.get("city", "")),
                    province=str(row.get("province", "")),
                )
                self.G.add_edge(cid, bkid, relationship="HOLDS_ACCOUNT", weight=m_exp)

                # Bank organization node
                if bank_name_val and bank_name_val.lower() not in ["", "nan", "none", "unknown"]:
                    bank_org_id = f"BANKORG-{hash(bank_name_val.lower()) % 10**8}"
                    if not self.G.has_node(bank_org_id):
                        self.G.add_node(bank_org_id, label=bank_name_val, node_type="Bank", color="#00d4aa")
                    self.G.add_edge(bkid, bank_org_id, relationship="HELD_AT")
                    if not self.G.has_edge(cid, bank_org_id):
                        self.G.add_edge(cid, bank_org_id, relationship="BANKS_WITH")

        # ── SHARES_ADDRESS edges ────────────────────────────────────
        address_nodes = [n for n, d in self.G.nodes(data=True) if d.get("node_type") == "Address"]
        for addr_id in address_nodes:
            predecessors = list(self.G.predecessors(addr_id))
            persons = [p for p in predecessors
                       if self.G.nodes[p].get("node_type") == "Person"]
            if len(persons) > 1:
                for i in range(len(persons)):
                    for j in range(i + 1, len(persons)):
                        if not self.G.has_edge(persons[i], persons[j]):
                            self.G.add_edge(persons[i], persons[j],
                                            relationship="SHARES_ADDRESS")

        # ── Implicit Cross-Dataset Links (Syndicate Detection) ──────
        # Group citizens by common attributes to find implicit networks
        def _add_implicit_edges(group_col: str, edge_type: str):
            if group_col not in citizens_df.columns:
                return
            
            # Drop empty or invalid strings
            valid_df = citizens_df[citizens_df[group_col].astype(str).str.strip().astype(bool)]
            
            for attr_val, group in valid_df.groupby(group_col):
                cids = group["citizen_id"].dropna().astype(str).tolist()
                if len(cids) > 1:
                    for i in range(len(cids)):
                        for j in range(i + 1, len(cids)):
                            if self.G.has_node(cids[i]) and self.G.has_node(cids[j]):
                                if not self.G.has_edge(cids[i], cids[j]):
                                    self.G.add_edge(cids[i], cids[j], relationship=edge_type)
                                    
        # Father Name
        _add_implicit_edges("father_name", "SHARES_FATHER")
        
        # Exact Address Match
        _add_implicit_edges("address", "SHARES_ADDRESS")
        
        # Phone Number
        _add_implicit_edges("contact_number", "SHARES_PHONE")

        print(f"  Knowledge Graph: {self.G.number_of_nodes():,} nodes, "
              f"{self.G.number_of_edges():,} edges")
        return self.G

    def save_graph(self, path: Path | str | None = None) -> str:
        """Serialize the graph to disk."""
        path = Path(path) if path else MODELS_DIR / "knowledge_graph.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.G, f)
        return str(path)

    def load_graph(self, path: Path | str | None = None) -> nx.DiGraph:
        """Load a previously saved graph."""
        path = Path(path) if path else MODELS_DIR / "knowledge_graph.pkl"
        with open(path, "rb") as f:
            self.G = pickle.load(f)
        return self.G
