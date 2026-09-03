"""
Audit Trail Generator — Produces human-readable, evidence-based flagging narratives.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import RISK_CATEGORIES


def _fmt_pkr(amount: float) -> str:
    """Format a PKR amount with commas."""
    if amount >= 1_00_00_000:  # 1 crore
        return f"PKR {amount / 1_00_00_000:,.2f} Crore"
    elif amount >= 1_00_000:  # 1 lakh
        return f"PKR {amount / 1_00_000:,.1f} Lakh"
    else:
        return f"PKR {amount:,.0f}"


def _severity(level: str) -> dict:
    """Return style info for a severity level."""
    styles = {
        "CRITICAL": {"icon": "🔴", "color": "#ff3355"},
        "WARNING": {"icon": "🟠", "color": "#ff8c00"},
        "INFO": {"icon": "🔵", "color": "#4a9eff"},
        "OK": {"icon": "🟢", "color": "#00d4aa"},
    }
    return styles.get(level, styles["INFO"])


class AuditTrailGenerator:
    """Generate structured, human-readable audit trails explaining why a
    citizen was flagged."""

    def generate(
        self,
        citizen_profile: dict,
        risk_result: dict,
        shap_explanation: dict | None = None,
    ) -> dict:
        """Produce a full audit trail for a citizen.

        Parameters
        ----------
        citizen_profile : Merged citizen data with asset totals.
        risk_result : Output from deviation scorer / risk categorizer.
        shap_explanation : Optional SHAP output for ML-based explanations.

        Returns
        -------
        dict with ``flags``, ``summary``, ``risk_score``, ``risk_category``,
        ``confidence``, ``recommendations``.
        """
        flags: list[dict] = []
        dev_score = float(risk_result.get("deviation_score", 0))

        # ── Property flags ──────────────────────────────────────────
        prop_val = float(citizen_profile.get("total_property_value", 0))
        if prop_val > 0:
            sev = "CRITICAL" if prop_val > 20_000_000 else ("WARNING" if prop_val > 5_000_000 else "INFO")
            flags.append({
                "description": f"Owns property worth {_fmt_pkr(prop_val)}",
                "severity": sev,
                "value": prop_val,
                "threshold": 5_000_000,
                **_severity(sev),
            })

        # ── Vehicle flags ───────────────────────────────────────────
        veh_val = float(citizen_profile.get("total_vehicle_value", 0))
        if veh_val > 0:
            sev = "CRITICAL" if veh_val > 10_000_000 else ("WARNING" if veh_val > 3_000_000 else "INFO")
            veh_detail = citizen_profile.get("vehicle_detail", "")
            desc = f"Owns vehicle(s) worth {_fmt_pkr(veh_val)}"
            if veh_detail:
                desc += f" ({veh_detail})"
            flags.append({
                "description": desc,
                "severity": sev,
                "value": veh_val,
                "threshold": 3_000_000,
                **_severity(sev),
            })

        # ── Utility bill flags ──────────────────────────────────────
        elec = float(citizen_profile.get("avg_monthly_electricity", 0))
        if elec > 20_000:
            sev = "CRITICAL" if elec > 50_000 else "WARNING"
            flags.append({
                "description": f"Monthly electricity bill: {_fmt_pkr(elec)} (upper-class indicator)",
                "severity": sev,
                "value": elec,
                "threshold": 20_000,
                **_severity(sev),
            })

        gas = float(citizen_profile.get("avg_monthly_gas", 0))
        if gas > 10_000:
            sev = "WARNING" if gas > 20_000 else "INFO"
            flags.append({
                "description": f"Monthly gas bill: {_fmt_pkr(gas)}",
                "severity": sev,
                "value": gas,
                "threshold": 10_000,
                **_severity(sev),
            })

        # ── Income declaration ──────────────────────────────────────
        income = float(citizen_profile.get("declared_income", 0))
        net_worth = float(citizen_profile.get("estimated_net_worth", 0))

        if income < 600_000 and net_worth > 5_000_000:
            flags.append({
                "description": f"Declared annual income: {_fmt_pkr(income)} only",
                "severity": "CRITICAL",
                "value": income,
                "threshold": 600_000,
                **_severity("CRITICAL"),
            })
        elif income > 0:
            flags.append({
                "description": f"Declared annual income: {_fmt_pkr(income)}",
                "severity": "INFO",
                "value": income,
                "threshold": 0,
                **_severity("INFO"),
            })

        # ── Tax payment ─────────────────────────────────────────────
        tax_paid = float(citizen_profile.get("tax_paid", 0))
        filing = str(citizen_profile.get("filing_status", "")).lower()

        if tax_paid == 0 and net_worth > 2_000_000:
            flags.append({
                "description": "No tax paid despite significant assets",
                "severity": "CRITICAL",
                "value": tax_paid,
                "threshold": 1,
                **_severity("CRITICAL"),
            })

        if "non" in filing or filing == "" or filing == "non-filer":
            flags.append({
                "description": "Non-filer — no tax return filed",
                "severity": "CRITICAL",
                "value": 0,
                "threshold": 1,
                **_severity("CRITICAL"),
            })

        # ── Travel flags ────────────────────────────────────────────
        travel_count = int(citizen_profile.get("foreign_travel_count", 0))
        biz_trips = int(citizen_profile.get("business_class_trips", 0))
        if travel_count > 2:
            sev = "WARNING" if biz_trips > 0 else "INFO"
            desc = f"{travel_count} international trips"
            if biz_trips > 0:
                desc += f" ({biz_trips} in business/first class)"
            flags.append({
                "description": desc,
                "severity": sev,
                "value": travel_count,
                "threshold": 2,
                **_severity(sev),
            })

        # ── Business flags ──────────────────────────────────────────
        biz_count = int(citizen_profile.get("business_count", 0))
        if biz_count > 0:
            flags.append({
                "description": f"Director/owner of {biz_count} company(ies)",
                "severity": "WARNING" if biz_count > 1 else "INFO",
                "value": biz_count,
                "threshold": 0,
                **_severity("WARNING" if biz_count > 1 else "INFO"),
            })

        # ── Income-to-asset ratio ───────────────────────────────────
        if net_worth > 0 and income > 0:
            ratio = income / net_worth
            if ratio < 0.05:
                flags.append({
                    "description": f"Income-to-Asset Ratio: {ratio:.3f} (expected > 0.15)",
                    "severity": "CRITICAL",
                    "value": ratio,
                    "threshold": 0.15,
                    **_severity("CRITICAL"),
                })
            elif ratio < 0.15:
                flags.append({
                    "description": f"Income-to-Asset Ratio: {ratio:.3f} (below expected 0.15)",
                    "severity": "WARNING",
                    "value": ratio,
                    "threshold": 0.15,
                    **_severity("WARNING"),
                })

        # ── SHAP-based factors ──────────────────────────────────────
        if shap_explanation and "top_positive_factors" in shap_explanation:
            for factor in shap_explanation["top_positive_factors"][:3]:
                flags.append({
                    "description": f"ML factor: {factor['feature']} = {factor['feature_value']:.0f} "
                                   f"(contribution: {factor['shap_value']:.3f})",
                    "severity": "INFO",
                    "value": factor["shap_value"],
                    "threshold": 0,
                    **_severity("INFO"),
                })

        # ── Determine risk category ─────────────────────────────────
        risk_cat = risk_result.get("risk_category", "C")
        cat_info = RISK_CATEGORIES.get(risk_cat, RISK_CATEGORIES["C"])

        # ── Confidence based on number of critical flags ────────────
        critical_count = sum(1 for f in flags if f["severity"] == "CRITICAL")
        warning_count = sum(1 for f in flags if f["severity"] == "WARNING")
        confidence = min(50 + critical_count * 15 + warning_count * 5, 99)

        # ── Summary narrative ───────────────────────────────────────
        name = citizen_profile.get("canonical_name", citizen_profile.get("name", "Unknown"))
        summary_parts = [f"Citizen '{name}' has been flagged with a deviation score of {dev_score:.0f}/100."]
        if critical_count > 0:
            summary_parts.append(f"{critical_count} critical indicator(s) detected.")
        if net_worth > 0 and income > 0:
            summary_parts.append(
                f"Estimated net worth ({_fmt_pkr(net_worth)}) significantly exceeds "
                f"declared income ({_fmt_pkr(income)})."
            )
        summary = " ".join(summary_parts)

        # ── Recommendations ─────────────────────────────────────────
        recommendations = []
        if dev_score >= 80:
            recommendations.append("Immediate investigation recommended")
            recommendations.append("Issue notice under Section 114 (Income Tax Ordinance)")
        elif dev_score >= 60:
            recommendations.append("Schedule for detailed tax audit")
            recommendations.append("Request asset disclosure under Section 116")
        elif dev_score >= 40:
            recommendations.append("Flag for periodic review")
        else:
            recommendations.append("No immediate action required")

        return {
            "flags": flags,
            "summary": summary,
            "risk_score": dev_score,
            "risk_category": risk_cat,
            "risk_label": cat_info["label"],
            "risk_color": cat_info["color"],
            "confidence": confidence,
            "recommendations": recommendations,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "total_flags": len(flags),
        }
