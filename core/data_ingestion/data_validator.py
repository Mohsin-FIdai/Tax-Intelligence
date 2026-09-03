"""
Data Validation Module — Validates CNICs, phone numbers, NTNs, and full DataFrames.
"""
import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


# ─── Compiled patterns ──────────────────────────────────────────────
_CNIC_RE = re.compile(r"^(\d{5})-(\d{7})-(\d)$")
_PHONE_RE = re.compile(r"^(03\d{2})-?(\d{7})$")
_NTN_RE = re.compile(r"^(\d{7})(?:-(\d))?$")

_VALID_PROVINCE_CODES = {"1", "2", "3", "4", "5", "6", "7"}
_VALID_OPERATOR_PREFIXES = {
    "0300", "0301", "0302", "0303", "0304", "0305", "0306", "0307", "0308", "0309",
    "0310", "0311", "0312", "0313", "0314", "0315", "0316", "0317", "0318", "0319",
    "0320", "0321", "0322", "0323", "0324", "0325", "0326", "0327", "0328", "0329",
    "0330", "0331", "0332", "0333", "0334", "0335", "0336", "0337", "0338", "0339",
    "0340", "0341", "0342", "0343", "0344", "0345", "0346", "0347", "0348", "0349",
    "0355", "0370", "0371",
}


@dataclass
class ValidationReport:
    """Container for validation results of a DataFrame."""
    total_rows: int = 0
    valid_rows: int = 0
    error_count: int = 0
    errors_by_field: dict[str, int] = field(default_factory=dict)
    error_samples: list[dict[str, Any]] = field(default_factory=list)

    @property
    def validity_pct(self) -> float:
        return round(self.valid_rows / max(self.total_rows, 1) * 100, 2)


# ─── Individual validators ─────────────────────────────────────────

def validate_cnic(cnic: str | None) -> tuple[bool, str]:
    """Validate a Pakistani CNIC number.

    Expected format: XXXXX-XXXXXXX-X  (13 digits with hyphens).

    Returns
    -------
    (is_valid, reason)
    """
    if cnic is None or (isinstance(cnic, float)):
        return False, "CNIC is missing"

    cnic = str(cnic).strip()
    if not cnic:
        return False, "CNIC is empty"

    m = _CNIC_RE.match(cnic)
    if not m:
        # Try to normalise a raw 13-digit string
        digits = cnic.replace("-", "")
        if len(digits) == 13 and digits.isdigit():
            cnic = f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
            m = _CNIC_RE.match(cnic)
        if not m:
            return False, f"Invalid format: expected XXXXX-XXXXXXX-X, got '{cnic}'"

    province_code = m.group(1)[0]
    if province_code not in _VALID_PROVINCE_CODES:
        return False, f"Invalid province code '{province_code}'"

    return True, "Valid"


def validate_phone(phone: str | None) -> tuple[bool, str]:
    """Validate a Pakistani mobile phone number.

    Expected format: 03XX-XXXXXXX or 03XXXXXXXXX (11 digits).
    """
    if phone is None or (isinstance(phone, float)):
        return False, "Phone is missing"

    phone = str(phone).strip()
    if not phone:
        return False, "Phone is empty"

    m = _PHONE_RE.match(phone)
    if not m:
        return False, f"Invalid format: expected 03XX-XXXXXXX, got '{phone}'"

    prefix = m.group(1)
    if prefix not in _VALID_OPERATOR_PREFIXES:
        return False, f"Invalid operator prefix '{prefix}'"

    return True, "Valid"


def validate_ntn(ntn: str | None) -> tuple[bool, str]:
    """Validate a Pakistani National Tax Number."""
    if ntn is None or (isinstance(ntn, float)):
        return False, "NTN is missing"

    ntn = str(ntn).strip()
    if not ntn:
        return False, "NTN is empty"

    # NTN can be a CNIC (for individuals) or a 7-digit number
    if _CNIC_RE.match(ntn):
        return True, "Valid (CNIC-based NTN)"

    if _NTN_RE.match(ntn):
        return True, "Valid (7-digit NTN)"

    return False, f"Invalid NTN format: '{ntn}'"


def validate_dataframe(df: pd.DataFrame, schema_type: str = "auto") -> ValidationReport:
    """Validate all identifiable fields in a DataFrame.

    Parameters
    ----------
    df : DataFrame to validate.
    schema_type : Hint about the dataset ('tax', 'vehicle', 'property', etc.) or 'auto'.
    """
    report = ValidationReport(total_rows=len(df))
    row_valid_flags = [True] * len(df)

    # Identify columns to validate
    cols_lower = {c: c.lower().replace(" ", "_") for c in df.columns}

    for original_col, lower_col in cols_lower.items():
        validator = None
        label = None

        if "cnic" in lower_col or "nic" in lower_col:
            validator = validate_cnic
            label = "cnic"
        elif "phone" in lower_col or "mobile" in lower_col:
            validator = validate_phone
            label = "phone"
        elif "ntn" in lower_col:
            validator = validate_ntn
            label = "ntn"

        if validator is None:
            continue

        field_errors = 0
        for idx, val in df[original_col].items():
            is_valid, reason = validator(val)
            if not is_valid:
                field_errors += 1
                row_valid_flags[idx] = False
                if len(report.error_samples) < 50:
                    report.error_samples.append({
                        "row": int(idx),
                        "field": original_col,
                        "value": str(val),
                        "reason": reason,
                    })

        if field_errors:
            report.errors_by_field[label] = field_errors
            report.error_count += field_errors

    report.valid_rows = sum(row_valid_flags)
    return report
