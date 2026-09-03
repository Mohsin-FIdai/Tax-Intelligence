"""
PDF Report Generator — Professional citizen and investigation reports using fpdf2.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import REPORTS_DIR, RISK_CATEGORIES

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None


def _fmt_pkr(amount: float) -> str:
    """Format PKR amount."""
    if amount >= 1_00_00_000:
        return f"PKR {amount / 1_00_00_000:,.2f} Cr"
    elif amount >= 1_00_000:
        return f"PKR {amount / 1_00_000:,.1f} L"
    return f"PKR {amount:,.0f}"

def _s(text: Any) -> str:
    """Sanitize text to prevent FPDF unicode errors."""
    return str(text).encode('latin-1', 'replace').decode('latin-1')


class PDFReportGenerator:
    """Generate professional PDF reports for citizen profiles and investigations."""

    def __init__(self):
        if FPDF is None:
            raise ImportError("fpdf2 is required for PDF generation. Install with: pip install fpdf2")

    def generate_citizen_report(
        self,
        citizen_profile: dict,
        risk_result: dict,
        audit_trail: dict,
        output_path: str | Path | None = None,
    ) -> str:
        """Generate a detailed PDF report for a single citizen.

        Returns the path to the generated PDF.
        """
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        cid = citizen_profile.get("citizen_id", "UNKNOWN")
        if output_path is None:
            output_path = REPORTS_DIR / f"citizen_report_{cid}.pdf"
        output_path = Path(output_path)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # ── Header ─────────────────────────────────────────────────
        pdf.set_fill_color(10, 10, 15)
        pdf.rect(0, 0, 210, 35, "F")
        pdf.set_text_color(0, 212, 170)
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "Tax Intelligence Authority", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(200, 200, 210)
        pdf.cell(0, 6, "CONFIDENTIAL - Citizen Risk Assessment Report", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, _s(f"Report ID: RPT-{cid}  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

        # ── Citizen Profile Section ─────────────────────────────────
        pdf.set_text_color(0, 0, 0)
        self._section_header(pdf, "CITIZEN PROFILE")

        name = citizen_profile.get("canonical_name", citizen_profile.get("name", "Unknown"))
        cnic = citizen_profile.get("cnic", "N/A")
        city = citizen_profile.get("city", "N/A")
        province = citizen_profile.get("province", "N/A")
        filing = citizen_profile.get("filing_status", "N/A")

        profile_data = [
            ("Full Name", name),
            ("CNIC", cnic),
            ("City / Province", f"{city}, {province}"),
            ("Filing Status", filing),
            ("Citizen ID", cid),
        ]
        for label, value in profile_data:
            self._key_value_row(pdf, label, str(value))
        pdf.ln(4)

        # ── Risk Assessment Section ─────────────────────────────────
        self._section_header(pdf, "RISK ASSESSMENT")
        dev_score = risk_result.get("deviation_score", 0)
        risk_cat = risk_result.get("risk_category", "C")
        cat_info = RISK_CATEGORIES.get(risk_cat, RISK_CATEGORIES["C"])

        self._key_value_row(pdf, "Deviation Score", f"{dev_score:.0f} / 100")
        self._key_value_row(pdf, "Risk Category", f"Category {risk_cat} - {cat_info['label']}")
        self._key_value_row(pdf, "Suspicion Percentage",
                           f"{risk_result.get('suspicion_pct', dev_score):.1f}%")
        self._key_value_row(pdf, "Confidence",
                           f"{audit_trail.get('confidence', 0)}%")
        pdf.ln(4)

        # ── Financial Summary ───────────────────────────────────────
        self._section_header(pdf, "FINANCIAL SUMMARY")
        income = float(citizen_profile.get("declared_income", 0))
        net_worth = float(citizen_profile.get("estimated_net_worth", 0))
        tax_paid = float(citizen_profile.get("tax_paid", 0))
        prop_val = float(citizen_profile.get("total_property_value", 0))
        veh_val = float(citizen_profile.get("total_vehicle_value", 0))

        fin_data = [
            ("Declared Income", _fmt_pkr(income)),
            ("Tax Paid", _fmt_pkr(tax_paid)),
            ("Estimated Net Worth", _fmt_pkr(net_worth)),
            ("Total Property Value", _fmt_pkr(prop_val)),
            ("Total Vehicle Value", _fmt_pkr(veh_val)),
        ]
        for label, value in fin_data:
            self._key_value_row(pdf, label, value)
        pdf.ln(4)

        # ── Audit Trail ─────────────────────────────────────────────
        self._section_header(pdf, "AUDIT TRAIL - FLAGGING REASONS")
        flags = audit_trail.get("flags", [])
        for flag in flags:
            sev = flag.get("severity", "INFO")
            marker = {"CRITICAL": "[!]", "WARNING": "[*]", "INFO": "[i]", "OK": "[+]"}.get(sev, "[?]")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(10, 5, _s(marker))
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 5, _s(flag["description"]), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

        # ── Summary ─────────────────────────────────────────────────
        self._section_header(pdf, "SUMMARY")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _s(audit_trail.get("summary", "No summary available.")))
        pdf.ln(2)

        # ── Recommendations ─────────────────────────────────────────
        self._section_header(pdf, "RECOMMENDATIONS")
        for rec in audit_trail.get("recommendations", []):
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(5, 5, "-")  # bullet
            pdf.cell(0, 5, _s(f" {rec}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # ── Footer / Disclaimer ─────────────────────────────────────
        pdf.set_y(-30)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 4, "DISCLAIMER: This report is generated by an AI system using synthetic data.",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 4, "All analysis is indicative and must be verified by authorised officers before any action.",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 4, f"Page {pdf.page_no()}", align="C")

        pdf.output(str(output_path))
        return str(output_path)

    def generate_investigation_report(
        self,
        citizens_list: list[dict],
        output_path: str | Path | None = None,
    ) -> str:
        """Generate a bulk investigation report for multiple citizens."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = REPORTS_DIR / f"investigation_report_{ts}.pdf"
        output_path = Path(output_path)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page("L")  # Landscape

        # Header
        pdf.set_fill_color(10, 10, 15)
        pdf.rect(0, 0, 297, 30, "F")
        pdf.set_text_color(0, 212, 170)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Tax Intelligence Authority - Investigation Report", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(200, 200, 210)
        pdf.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
                        f"Total Subjects: {len(citizens_list)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

        # Table header
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(230, 230, 230)
        headers = ["#", "Citizen ID", "Name", "CNIC", "City", "Income", "Net Worth", "Score", "Category"]
        widths = [8, 20, 45, 35, 25, 30, 30, 15, 30]
        for h, w in zip(headers, widths):
            pdf.cell(w, 6, h, border=1, fill=True)
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 7)
        for i, c in enumerate(citizens_list[:200], 1):
            pdf.cell(widths[0], 5, _s(str(i)), border=1)
            pdf.cell(widths[1], 5, _s(str(c.get("citizen_id", ""))[:12]), border=1)
            pdf.cell(widths[2], 5, _s(str(c.get("canonical_name", ""))[:30]), border=1)
            pdf.cell(widths[3], 5, _s(str(c.get("cnic", ""))), border=1)
            pdf.cell(widths[4], 5, _s(str(c.get("city", ""))[:15]), border=1)
            pdf.cell(widths[5], 5, _s(_fmt_pkr(float(c.get("declared_income", 0)))), border=1)
            pdf.cell(widths[6], 5, _s(_fmt_pkr(float(c.get("estimated_net_worth", 0)))), border=1)
            pdf.cell(widths[7], 5, _s(f"{c.get('deviation_score', 0):.0f}"), border=1)
            cat = c.get("risk_category", "")
            label = RISK_CATEGORIES.get(cat, {}).get("label", cat)
            pdf.cell(widths[8], 5, _s(label[:18]), border=1)
            pdf.ln()

        pdf.output(str(output_path))
        return str(output_path)

    # ── Helper methods ──────────────────────────────────────────────

    @staticmethod
    def _section_header(pdf: "FPDF", title: str):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 100, 80)
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(0, 212, 170)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(3)

    @staticmethod
    def _key_value_row(pdf: "FPDF", key: str, value: str):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(55, 5, _s(key))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, _s(value), new_x="LMARGIN", new_y="NEXT")
