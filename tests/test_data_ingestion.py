import pytest
import pandas as pd
from io import StringIO
from core.data_ingestion.data_cleaner import clean_dataframe
from core.data_ingestion.schema_detector import detect_field_type

def test_detect_field_type():
    # Test CNIC detection
    cnic_series = pd.Series(["42201-1234567-8", "42201-1234567-1", "invalid"])
    assert detect_field_type("id_number", cnic_series) == "cnic"

    # Test Phone detection
    phone_series = pd.Series(["0300-1234567", "0345-7654321", "123"])
    assert detect_field_type("contact", phone_series) == "phone"

def test_clean_dataframe():
    # Test dataframe cleaning (removing empty columns, normalizing headers)
    csv_data = """Name  , CNIC Number ,   EmptyCol, Phone\nAli , 42201-1234567-8, , 0300-1234567\n"""
    df = pd.read_csv(StringIO(csv_data))
    
    cleaned_df = clean_dataframe(df)
    
    # Headers should be lowercased and stripped of spaces, and mapped by schema
    assert "canonical_name" in cleaned_df.columns
    assert "cnic_number" in cleaned_df.columns
    assert "phone" in cleaned_df.columns
    
    assert "emptycol" in cleaned_df.columns

    # Values should be stripped
    assert cleaned_df.iloc[0]["canonical_name"] == "Ali "
