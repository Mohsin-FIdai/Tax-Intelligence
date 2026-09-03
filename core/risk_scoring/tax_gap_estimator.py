"""
Tax Gap Estimator — Predicts undeclared income and recoverable tax revenue.
"""

import pandas as pd
import numpy as np
from typing import Any

class TaxGapEstimator:
    """Estimates the tax gap (hidden income and recoverable tax)."""

    def __init__(self):
        # Simplified Pakistan Tax Slabs (2024-2025 approx)
        self.slabs = [
            (600_000, 0.0),       # Up to 600k: 0%
            (1_200_000, 0.05),    # 600k - 1.2M: 5%
            (2_200_000, 0.15),    # 1.2M - 2.2M: 15%
            (3_200_000, 0.25),    # 2.2M - 3.2M: 25%
            (4_100_000, 0.30),    # 3.2M - 4.1M: 30%
            (float("inf"), 0.35)  # > 4.1M: 35%
        ]

    def _calculate_tax(self, income: float) -> float:
        """Calculate tax based on progressive slabs."""
        if income <= 600_000:
            return 0.0
            
        tax = 0.0
        prev_limit = 600_000
        
        for limit, rate in self.slabs[1:]:
            if income > prev_limit:
                taxable_in_slab = min(income, limit) - prev_limit
                tax += taxable_in_slab * rate
                prev_limit = limit
            else:
                break
        return tax

    def estimate_gap(self, declared_income: Any, estimated_net_worth: Any) -> dict:
        """
        Estimate the hidden income and recoverable tax.
        Net worth is treated as a proxy for actual annual income/wealth accumulation
        for the sake of the intelligence platform.
        """
        # Safely parse floats, handling NaNs, Nones, and empty strings
        try:
            decl_inc = float(declared_income) if pd.notna(declared_income) and declared_income != '' else 0.0
        except (ValueError, TypeError):
            decl_inc = 0.0
            
        try:
            est_nw = float(estimated_net_worth) if pd.notna(estimated_net_worth) and estimated_net_worth != '' else 0.0
        except (ValueError, TypeError):
            est_nw = 0.0
            
        # Ensure we don't have negative values
        declared_income = max(0.0, decl_inc)
        estimated_net_worth = max(0.0, est_nw)
        
        # We assume the estimated net worth reflects the true economic capacity.
        # Hidden income is the difference between true capacity and declared income.
        hidden_income = max(0.0, estimated_net_worth - declared_income)
        
        # Recoverable tax is the difference between tax on true capacity and tax on declared income
        tax_on_true_capacity = self._calculate_tax(estimated_net_worth)
        tax_on_declared = self._calculate_tax(declared_income)
        
        recoverable_tax = max(0.0, tax_on_true_capacity - tax_on_declared)
        
        return {
            "estimated_hidden_income": hidden_income,
            "estimated_recoverable_tax": recoverable_tax
        }

    def process_dataframe(self, citizens_df: pd.DataFrame) -> pd.DataFrame:
        """Process an entire dataframe to add tax gap metrics."""
        df = citizens_df.copy()
        
        hidden_incomes = []
        recoverable_taxes = []
        
        for _, row in df.iterrows():
            declared = row.get("declared_income", 0)
            net_worth = row.get("estimated_net_worth", 0)
            
            # If the user is a non-filer, their declared income is effectively 0 for tax purposes,
            # but they might have declared income in the master DB. We'll use declared_income.
            
            res = self.estimate_gap(declared, net_worth)
            hidden_incomes.append(res["estimated_hidden_income"])
            recoverable_taxes.append(res["estimated_recoverable_tax"])
            
        df["estimated_hidden_income"] = hidden_incomes
        df["estimated_recoverable_tax"] = recoverable_taxes
        
        return df
