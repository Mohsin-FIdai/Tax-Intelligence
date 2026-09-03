import pytest
import pandas as pd
from core.ml.feature_engineering import FeatureEngineer
from core.risk_scoring.risk_categorizer import RiskCategorizer

def test_extract_features():
    fe = FeatureEngineer()
    
    citizens = pd.DataFrame([{"citizen_id": "1", "declared_income": 500000, "tax_paid": 10000, "filing_status": "Filer"}])
    vehicles = pd.DataFrame([{"citizen_id": "1", "value": 5000000}])
    properties = pd.DataFrame([{"citizen_id": "1", "property_value": 20000000}])
    utilities = pd.DataFrame([{"citizen_id": "1", "bill_amount": 0}])
    travel = pd.DataFrame([{"citizen_id": "1", "ticket_class": "Economy", "destination": "UAE"}])
    business = pd.DataFrame([{"citizen_id": "1", "revenue_declared": 0}])
    banking = pd.DataFrame([{"citizen_id": "1", "credit_turnover": 0}])
    graph = pd.DataFrame([{"citizen_id": "1", "degree_centrality": 0}])
    
    features = fe.extract_features(
        citizens, vehicles, properties, utilities, travel, business, banking, graph
    )
    
    assert not features.empty
    assert features.iloc[0]["declared_income"] == 500000
    assert features.iloc[0]["tax_paid"] == 10000
    assert features.iloc[0]["total_property_value"] == 20000000
    assert features.iloc[0]["total_vehicle_value"] == 5000000
    # Net worth to income ratio -> represented by income_to_asset_ratio
    assert "income_to_asset_ratio" in features.columns

def test_categorize_risk():
    rc = RiskCategorizer()
    assert rc.categorize(10)["category"] == "A"
    assert rc.categorize(30)["category"] == "B"
    assert rc.categorize(50)["category"] == "C"
    assert rc.categorize(70)["category"] == "D"
    assert rc.categorize(90)["category"] == "E"
