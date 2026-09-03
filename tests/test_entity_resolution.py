import pytest
import pandas as pd
from core.entity_resolution.entity_resolver import (
    normalize_cnic,
    normalize_phone,
    normalize_city,
    normalize_address,
)
from core.entity_resolution.name_normalizer import normalize_name, parse_name
from core.entity_resolution.confidence_scorer import score_match


def test_normalize_cnic():
    assert normalize_cnic("42201-1234567-8") == "4220112345678"
    assert normalize_cnic("4220112345678") == "4220112345678"
    assert normalize_cnic("  42201-1234567-8  ") == "4220112345678"
    
    # Invalid cases
    assert normalize_cnic("12345") == ""  # Too short
    assert normalize_cnic(None) == ""
    assert normalize_cnic("NaN") == ""
    assert normalize_cnic("N/A") == ""

def test_normalize_phone():
    assert normalize_phone("0300-1234567") == "03001234567"
    assert normalize_phone("03001234567") == "03001234567"
    assert normalize_phone("+923001234567") == "03001234567"
    assert normalize_phone("923001234567") == "03001234567"
    assert normalize_phone("3001234567") == "03001234567"
    
    # Invalid cases
    assert normalize_phone("0213456789") == ""  # Landline (if not starting with 03)
    assert normalize_phone("12345") == ""
    assert normalize_phone(None) == ""

def test_normalize_name():
    assert normalize_name("Muhammad Ali") == "Muhammad Ali"
    assert normalize_name("  Syed   Ali  Raza  ") == "Syed Ali Raza"
    assert normalize_name("NaN") == ""
    assert normalize_name("Unknown") == ""

def test_parse_name():
    rep = parse_name("Muhammad Ali Raza")
    assert rep.canonical == "Muhammad Ali Raza"
    assert len(rep.tokens) == 3
    
def test_score_match_exact_cnic():
    rec1 = {"_cnic_normalized": "4220112345678", "_name_canonical": "ali"}
    rec2 = {"_cnic_normalized": "4220112345678", "_name_canonical": "unknown"}
    score = score_match(rec1, rec2)
    assert score == 100.0

def test_score_match_conflict_cnic():
    rec1 = {"_cnic_normalized": "4220112345678", "_name_canonical": "ali"}
    rec2 = {"_cnic_normalized": "4220187654321", "_name_canonical": "ali"}
    score = score_match(rec1, rec2)
    # The scoring model gives 0 weight or penalizes when CNIC conflicts
    assert score < 50.0

def test_score_match_fuzzy():
    rec1 = {"_phone_normalized": "03001234567", "_name_canonical": "syed ali raza", "_city_normalized": "karachi"}
    rec2 = {"_phone_normalized": "03001234567", "_name_canonical": "ali raza", "_city_normalized": "karachi"}
    score = score_match(rec1, rec2)
    # Should be high score for same phone + strong name match + same city
    assert score > 70.0
