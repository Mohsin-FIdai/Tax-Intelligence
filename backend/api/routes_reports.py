"""
Tax Intelligence Platform — Report API Routes

Endpoints for on-the-fly PDF generation and bulk CSV / Excel export.
"""

import io
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.models.schemas import ErrorResponse
from backend.services.data_service import DataService
from config.settings import RISK_CATEGORIES, REPORTS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


# ─── PDF Generation ──────────────────────────────────────────────────

def _build_pdf_bytes(profile: dict) -> bytes:
    """Generate a PDF report for a single citizen profile.

    Uses *fpdf2* to produce a clean, multi-section document containing
    personal information, risk assessment, asset summary, and audit trail.

    Returns:
        Raw PDF bytes ready for streaming to the client.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Title ─────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Tax Intelligence — Citizen Report", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        0, 6,
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        ln=True, align="C",
    )
    pdf.ln(8)

    # ── Personal Information ──────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(230, 230, 240)
    pdf.cell(0, 9, "  Personal Information", ln=True, fill=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    fields = [
        ("Citizen ID", profile.get("citizen_id", "")),
        ("Name", profile.get("name", "")),
        ("CNIC", profile.get("cnic", "")),
        ("Father Name", profile.get("father_name", "")),
        ("Phone", profile.get("phone", "")),
        ("Email", profile.get("email", "")),
        ("Address", profile.get("address", "")),
        ("City", profile.get("city", "")),
        ("Province", profile.get("province", "")),
        ("Date of Birth", profile.get("date_of_birth", "")),
        ("NTN", profile.get("ntn", "")),
        ("Filing Status", profile.get("filing_status", "")),
    ]
    for label, value in fields:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 7, f"{label}:", align="L")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, str(value), ln=True)
    pdf.ln(6)

    # ── Risk Assessment ───────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "  Risk Assessment", ln=True, fill=True)
    pdf.ln(3)

    risk = profile.get("risk_details", {})
    cat = risk.get("category", profile.get("risk_category", "A"))
    meta = RISK_CATEGORIES.get(cat, RISK_CATEGORIES["A"])

    risk_fields = [
        ("Risk Score", f"{profile.get('risk_score', 0):.1f} / 100"),
        ("Risk Category", f"{cat} — {meta['label']}"),
        ("Deviation Score", f"{risk.get('deviation_score', 0):.2f}"),
        ("Suspicion %", f"{risk.get('suspicion_pct', 0):.1f}%"),
        ("Declared Income", f"PKR {float(profile.get('declared_income', 0)):,.0f}"),
        ("Estimated Net Worth", f"PKR {float(profile.get('estimated_net_worth', 0)):,.0f}"),
    ]
    for label, value in risk_fields:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 7, f"{label}:", align="L")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, str(value), ln=True)
    pdf.ln(6)

    # ── Asset Summary ─────────────────────────────────────────────────
    assets = profile.get("assets", {})
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "  Asset Summary", ln=True, fill=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    vehicles = assets.get("vehicles", [])
    properties = assets.get("properties", [])
    businesses = assets.get("businesses", [])
    pdf.cell(0, 7, f"Vehicles: {len(vehicles)}", ln=True)
    pdf.cell(0, 7, f"Properties: {len(properties)}", ln=True)
    pdf.cell(0, 7, f"Businesses: {len(businesses)}", ln=True)
    pdf.cell(
        0, 7,
        f"Total Estimated Value: PKR {assets.get('total_value', 0):,.0f}",
        ln=True,
    )

    if vehicles:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Vehicles:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for v in vehicles:
            line = (
                f"  {v.get('make', '')} {v.get('model', '')} "
                f"({v.get('year', '')}) — {v.get('registration_number', '')} "
                f"— PKR {float(v.get('estimated_value', 0)):,.0f}"
            )
            pdf.cell(0, 6, line, ln=True)

    if properties:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Properties:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for p in properties:
            line = (
                f"  {p.get('property_type', '')} at {p.get('location', '')} "
                f"— {p.get('area_sqft', 0)} sqft "
                f"— PKR {float(p.get('estimated_value', 0)):,.0f}"
            )
            pdf.cell(0, 6, line, ln=True)

    if businesses:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Businesses:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for b in businesses:
            line = (
                f"  {b.get('business_name', '')} ({b.get('business_type', '')}) "
                f"— NTN: {b.get('ntn', '')} "
                f"— Turnover: PKR {float(b.get('annual_turnover', 0)):,.0f}"
            )
            pdf.cell(0, 6, line, ln=True)

    pdf.ln(6)

    # ── Audit Trail ───────────────────────────────────────────────────
    trail = profile.get("audit_trail", [])
    if trail:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 9, "  Audit Trail", ln=True, fill=True)
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 9)
        for item in trail:
            severity = item.get("severity", "info").upper()
            desc = item.get("description", "")
            pdf.cell(0, 6, f"[{severity}] {desc}", ln=True)

    # ── Footer ────────────────────────────────────────────────────────
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0, 5,
        "This report is auto-generated by the Graph AI Tax Intelligence Platform. "
        "Confidential — for authorized personnel only.",
        ln=True,
        align="C",
    )

    return pdf.output()


@router.get(
    "/citizen/{citizen_id}/pdf",
    summary="Generate PDF report for a citizen",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF file"},
        404: {"model": ErrorResponse},
    },
)
async def generate_citizen_pdf(citizen_id: str) -> StreamingResponse:
    """Generate and stream a downloadable PDF report for a specific citizen.

    The report includes personal information, risk assessment, asset summary,
    and audit trail.
    """
    svc = DataService()
    profile = svc.get_citizen_by_id(citizen_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Citizen '{citizen_id}' not found",
        )

    try:
        pdf_bytes = _build_pdf_bytes(profile)
    except Exception as exc:
        logger.exception("PDF generation failed for %s", citizen_id)
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {exc}",
        ) from exc

    # Optionally persist a copy to the reports directory
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / f"citizen_{citizen_id}.pdf"
        with open(report_path, "wb") as fh:
            fh.write(pdf_bytes)
    except Exception:
        logger.warning("Could not save report copy for %s", citizen_id)

    filename = f"tax_report_{citizen_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Bulk Export ──────────────────────────────────────────────────────

@router.get(
    "/export",
    summary="Export filtered citizen data as CSV or Excel",
    responses={
        200: {
            "content": {
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            },
            "description": "Exported file",
        },
    },
)
async def export_data(
    format: str = Query(  # noqa: A002
        "csv",
        description="Export format: csv or excel",
    ),
    province: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    filing_status: Optional[str] = Query(None),
    min_income: Optional[float] = Query(None, ge=0),
    max_income: Optional[float] = Query(None, ge=0),
    min_risk_score: Optional[float] = Query(None, ge=0, le=100),
    max_risk_score: Optional[float] = Query(None, ge=0, le=100),
) -> StreamingResponse:
    """Export the filtered citizen dataset as a downloadable CSV or Excel file.

    Accepts the same filter parameters as the citizens list endpoint.
    """
    export_format = format.lower()
    if export_format not in ("csv", "excel"):
        raise HTTPException(
            status_code=400,
            detail="Format must be 'csv' or 'excel'.",
        )

    svc = DataService()
    filters = {
        "province": province,
        "city": city,
        "risk_level": risk_level,
        "filing_status": filing_status,
        "min_income": min_income,
        "max_income": max_income,
        "min_risk_score": min_risk_score,
        "max_risk_score": max_risk_score,
    }

    df = svc.export_citizens_csv(filters)

    buffer = io.BytesIO()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if export_format == "excel":
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        filename = f"tax_intelligence_export_{timestamp}.xlsx"
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        csv_text = df.to_csv(index=False)
        buffer.write(csv_text.encode("utf-8"))
        buffer.seek(0)
        filename = f"tax_intelligence_export_{timestamp}.csv"
        media = "text/csv"

    return StreamingResponse(
        buffer,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
