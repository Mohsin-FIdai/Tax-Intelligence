import pytest
import os
import pandas as pd
from pathlib import Path
from core.data_ingestion.etl_pipeline import ETLPipeline
from backend.services.data_service import DataService

@pytest.fixture
def test_fixture_dir(tmp_path):
    """Creates a small, deterministic test fixture dataset for end-to-end testing."""
    fixture_dir = tmp_path / "test_fixtures"
    fixture_dir.mkdir()
    
    # 1. Tax Records
    tax_df = pd.DataFrame({
        "CNIC": ["42201-1111111-1", "42201-2222222-2"],
        "Name": ["Ali Khan", "Sara Ahmed"],
        "Income_Declared": [500000, 1200000],
        "Tax_Paid": [5000, 45000]
    })
    tax_df.to_csv(fixture_dir / "tax_records.csv", index=False)
    
    # 2. Property Records
    property_df = pd.DataFrame({
        "Owner_CNIC": ["42201-1111111-1", "42201-3333333-3"],
        "Owner_Name": ["Ali Khan", "Zainab Ali"],
        "Property_Value": [25000000, 8000000]
    })
    property_df.to_csv(fixture_dir / "property_records.csv", index=False)
    
    return fixture_dir

def test_end_to_end_pipeline(test_fixture_dir):
    # 1. Initialize Pipeline
    pipeline = ETLPipeline()
    
    # 2. Run Pipeline on Test Fixtures
    # Do not call synthetic_dir, use source_dir
    results = pipeline.run_full_pipeline(source_dir=test_fixture_dir)
    
    # Assert ETL succeeded
    assert "tax_records" in results
    assert "property_records" in results
    
    # Assert data was parsed
    assert results["tax_records"]["rows_out"] == 2
    assert results["property_records"]["rows_out"] == 2
