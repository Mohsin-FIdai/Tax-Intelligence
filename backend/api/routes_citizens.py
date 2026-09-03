"""
Tax Intelligence Platform — Citizen API Routes

Endpoints for listing, filtering, and inspecting citizen profiles,
their assets, and audit trail.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.models.schemas import (
    APIResponse,
    AssetBreakdown,
    CitizenProfile,
    CitizenSummary,
    AuditTrailItem,
    ErrorResponse,
    PaginatedResponse,
)
from backend.services.data_service import DataService

router = APIRouter(prefix="/api/v1/citizens", tags=["Citizens"])


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List citizens with pagination and filtering",
    responses={500: {"model": ErrorResponse}},
)
async def list_citizens(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=10000, description="Page size"),
    search_query: Optional[str] = Query(None, description="Search name or CNIC"),
    province: Optional[str] = Query(None, description="Filter by province"),
    city: Optional[str] = Query(None, description="Filter by city"),
    risk_level: Optional[str] = Query(None, description="Risk category A–E"),
    filing_status: Optional[str] = Query(None, description="Filer or Non-Filer"),
    min_income: Optional[float] = Query(None, ge=0, description="Min income"),
    max_income: Optional[float] = Query(None, ge=0, description="Max income"),
    min_risk_score: Optional[float] = Query(None, ge=0, le=100),
    max_risk_score: Optional[float] = Query(None, ge=0, le=100),
    sort_by: Optional[str] = Query("risk_score", description="Sort column"),
    sort_order: Optional[str] = Query("desc", description="asc or desc"),
) -> PaginatedResponse:
    """Return a paginated, optionally filtered list of citizen summaries.

    Supports filtering by province, city, risk category, filing status,
    income range, and risk-score range. Results are sortable by any
    summary column.
    """
    svc = DataService()
    filters = {
        "search_query": search_query,
        "province": province,
        "city": city,
        "risk_level": risk_level,
        "filing_status": filing_status,
        "min_income": min_income,
        "max_income": max_income,
        "min_risk_score": min_risk_score,
        "max_risk_score": max_risk_score,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    records, total = svc.get_citizens(filters, page, page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 1

    return PaginatedResponse(
        success=True,
        data=records,
        total_count=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{citizen_id}",
    response_model=APIResponse,
    summary="Get full citizen profile",
    responses={404: {"model": ErrorResponse}},
)
async def get_citizen(citizen_id: str) -> APIResponse:
    """Return the complete profile for a single citizen including assets,
    tax records, risk details, and audit trail.
    """
    svc = DataService()
    profile = svc.get_citizen_by_id(citizen_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Citizen '{citizen_id}' not found",
        )
    return APIResponse(success=True, data=profile)


@router.get(
    "/{citizen_id}/assets",
    response_model=APIResponse,
    summary="Get citizen asset breakdown",
    responses={404: {"model": ErrorResponse}},
)
async def get_citizen_assets(citizen_id: str) -> APIResponse:
    """Return the asset breakdown (vehicles, properties, businesses) for
    a citizen.
    """
    svc = DataService()
    # Verify citizen exists
    row = svc.citizens_df[svc.citizens_df["citizen_id"] == citizen_id]
    if row.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Citizen '{citizen_id}' not found",
        )
    assets = svc.get_citizen_assets(citizen_id)
    return APIResponse(success=True, data=assets)


@router.get(
    "/{citizen_id}/audit-trail",
    response_model=APIResponse,
    summary="Get citizen audit trail",
    responses={404: {"model": ErrorResponse}},
)
async def get_citizen_audit_trail(citizen_id: str) -> APIResponse:
    """Return the list of audit-trail flags for a citizen."""
    svc = DataService()
    row = svc.citizens_df[svc.citizens_df["citizen_id"] == citizen_id]
    if row.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Citizen '{citizen_id}' not found",
        )
    trail = svc.get_citizen_audit_trail(citizen_id)
    return APIResponse(success=True, data=trail)
