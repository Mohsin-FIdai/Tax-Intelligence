"""
Schema Detection Module — Automatically detects column types, data quality, and field semantics.
"""
import re
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np


# ─── Field-type detection patterns ──────────────────────────────────
_CNIC_PATTERN = re.compile(r"^\d{5}-\d{7}-\d$")
_PHONE_PATTERN = re.compile(r"^0[3]\d{2}-?\d{7}$")
_NTN_PATTERN = re.compile(r"^\d{7}(-\d)?$")
_EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$")

_NAME_KEYWORDS = {"name", "owner", "holder", "traveler", "person", "citizen", "applicant"}
_CNIC_KEYWORDS = {"cnic", "nic", "identity", "national_id"}
_PHONE_KEYWORDS = {"phone", "mobile", "cell", "contact", "telephone"}
_AMOUNT_KEYWORDS = {"amount", "value", "price", "income", "salary", "tax", "bill",
                     "worth", "balance", "revenue", "paid", "cost", "fee"}
_ADDRESS_KEYWORDS = {"address", "location", "street", "area", "sector"}
_DATE_KEYWORDS = {"date", "dob", "departure", "return", "registration", "filing"}


def detect_field_type(column_name: str, sample_values: pd.Series) -> str:
    """Infer the semantic type of a column from its name and sample values.

    Returns one of: 'cnic', 'phone', 'ntn', 'email', 'name', 'amount',
    'address', 'date', 'categorical', 'numeric', 'other'.
    """
    col_lower = column_name.lower().replace(" ", "_")
    non_null = sample_values.dropna().astype(str)

    # Pattern-based detection on values
    if non_null.size > 0:
        match_rate = non_null.apply(lambda v: bool(_CNIC_PATTERN.match(v.strip()))).mean()
        if match_rate > 0.5:
            return "cnic"

        match_rate = non_null.apply(lambda v: bool(_PHONE_PATTERN.match(v.strip()))).mean()
        if match_rate > 0.5:
            return "phone"

        match_rate = non_null.apply(lambda v: bool(_NTN_PATTERN.match(v.strip()))).mean()
        if match_rate > 0.4:
            return "ntn"

        match_rate = non_null.apply(lambda v: bool(_EMAIL_PATTERN.match(v.strip()))).mean()
        if match_rate > 0.5:
            return "email"

    # Keyword-based detection on column name
    tokens = set(col_lower.replace("-", "_").split("_"))
    if tokens & _CNIC_KEYWORDS:
        return "cnic"
    if tokens & _PHONE_KEYWORDS:
        return "phone"
    if tokens & _NAME_KEYWORDS:
        return "name"
    if tokens & _AMOUNT_KEYWORDS:
        return "amount"
    if tokens & _ADDRESS_KEYWORDS:
        return "address"
    if tokens & _DATE_KEYWORDS:
        return "date"

    # Dtype-based fallback
    if pd.api.types.is_numeric_dtype(sample_values):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(sample_values):
        return "date"
    if sample_values.nunique() < max(20, len(sample_values) * 0.05):
        return "categorical"

    return "other"


def detect_schema(filepath_or_df: Path | str | pd.DataFrame) -> dict[str, Any]:
    """Analyse a tabular file or DataFrame and return a detailed schema report.

    Parameters
    ----------
    filepath_or_df : path to a CSV, XLSX, or JSON file, OR a pandas DataFrame.

    Returns
    -------
    dict with keys: ``columns`` (list of column dicts), ``row_count``,
    ``file_type``, ``overall_quality_score``.
    """
    if isinstance(filepath_or_df, pd.DataFrame):
        df = filepath_or_df
        ext = ".csv"
        filename = "DataFrame"
    else:
        filepath = Path(filepath_or_df)
        ext = filepath.suffix.lower()
        filename = str(filepath.name)

        if ext == ".csv":
            df = pd.read_csv(filepath, low_memory=False)
        elif ext in {".xlsx", ".xls"}:
            df = pd.read_excel(filepath)
        elif ext == ".json":
            df = pd.read_json(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    columns_info: list[dict] = []
    quality_scores: list[float] = []

    for col in df.columns:
        series = df[col]
        null_pct = float(series.isna().mean())
        unique_count = int(series.nunique())
        dtype_str = str(series.dtype)
        sample = series.dropna().head(5).tolist()
        field_type = detect_field_type(col, series)

        # Column-level quality: penalise nulls and low uniqueness for IDs
        col_quality = 1.0 - null_pct
        if field_type in {"cnic", "phone", "ntn"} and unique_count < len(series) * 0.5:
            col_quality *= 0.8  # many duplicates in an ID column is suspicious
        quality_scores.append(col_quality)

        columns_info.append({
            "name": col,
            "dtype": dtype_str,
            "field_type": field_type,
            "null_count": int(series.isna().sum()),
            "null_pct": round(null_pct * 100, 2),
            "unique_count": unique_count,
            "sample_values": sample,
        })

    overall_quality = round(float(np.mean(quality_scores)) * 100, 1) if quality_scores else 0.0

    return {
        "file": filename,
        "file_type": ext.lstrip("."),
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns_info,
        "overall_quality_score": overall_quality,
    }


def generate_quality_report(filepath: str | Path) -> dict[str, Any]:
    """High-level quality report with actionable insights."""
    schema = detect_schema(filepath)
    issues: list[str] = []

    for col_info in schema["columns"]:
        if col_info["null_pct"] > 20:
            issues.append(f"Column '{col_info['name']}' has {col_info['null_pct']}% missing values")
        if col_info["field_type"] == "cnic" and col_info["unique_count"] < schema["row_count"] * 0.8:
            issues.append(f"Column '{col_info['name']}' (CNIC) has many duplicates")

    return {
        **schema,
        "issues": issues,
        "issue_count": len(issues),
        "recommendation": "Data is suitable for processing" if not issues else "Review flagged issues before processing",
    }

def detect_dataset_domain(schema: dict) -> str:
    """Identify the dataset domain (tax, property, vehicle, etc.) from its schema."""
    filename = str(schema.get("file", "")).lower()
    fields = [c["name"].lower().replace(" ", "_").replace("-", "_") for c in schema.get("columns", [])]
    field_types = [c.get("field_type", "") for c in schema.get("columns", [])]
    
    # 1. Vehicle records (Excise & Taxation Department)
    if "excise" in filename or "vehicle" in filename or "car" in filename or \
       any(f in ["vehicle_make", "vehicle_model", "vehicle_year", "engine_cc", "car_model", "license_plate"] for f in fields):
        return "vehicle_records"

    # 2. Tax records (Federal Board of Revenue - FBR)
    if "fbr" in filename or "income" in filename or \
       any(f in ["income_declared", "return_status", "declared_income", "tax_paid", "filer_status", "ntn"] for f in fields) or \
       ("tax" in filename and "excise" not in filename):
        return "tax_records"
        
    # 3. Property records (Real Estate)
    if "property" in filename or "estate" in filename or "land" in filename or \
       any(f in ["property_type", "plot_house_no", "size_marla"] for f in fields) or \
       ("property_type" in fields and "value_pkr" in fields):
        return "property_records"
        
    # 4. Utility bills (WAPDA / Sui Gas / LESCO)
    if "wapda" in filename or "utility" in filename or "bill" in filename or \
       any(f in ["utility_type", "provider", "monthly_bill_pkr", "electricity_bill", "gas_bill", "meter_no"] for f in fields):
        return "utility_bills"
        
    # 5. Business records (SECP)
    if "secp" in filename or "business" in filename or "company" in filename or \
       any(f in ["business_name", "business_type", "registration_status", "annual_turnover_pkr", "share_percentage"] for f in fields):
        return "business_records"
        
    # 6. Banking indicators (State Bank of Pakistan - SBP)
    if "bank" in filename or "sbp" in filename or "account" in filename or \
       any(f in ["account_last4", "bank_name", "account_type", "monthly_expenditure_pkr", "annual_expenditure_pkr", "avg_balance", "monthly_transactions"] for f in fields):
        return "banking_indicators"
        
    # 7. Travel records (Federal Investigation Agency - FIA)
    if "fia" in filename or "travel" in filename or "flight" in filename or \
       any(f in ["passport_last4", "destination", "travel_date", "international", "passport_no", "travel_class", "visa_type"] for f in fields):
        return "travel_records"
        
    # 8. Citizen identity records (NADRA)
    if "nadra" in filename or "citizen" in filename or \
       (all(f in fields for f in ["cnic", "name", "father_name", "phone", "address"]) and not any(f in fields for f in ["income_declared", "utility_type"])):
        return "nadra"
        
    # 9. Telecom / Mobile records (PTA)
    if "pta" in filename or "telecom" in filename or "mobile" in filename or \
       (all(f in fields for f in ["cnic", "name", "phone", "address"]) and "father_name" not in fields and not any(f in fields for f in ["utility_type", "income_declared"])):
        return "mobile_records"

    return "unknown_dataset"

