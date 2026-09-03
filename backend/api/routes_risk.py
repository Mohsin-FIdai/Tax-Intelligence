"""
Tax Intelligence Platform — Risk API Routes

Endpoints for risk distribution, top-suspicious citizens, and
ML feature importance.
"""

from fastapi import APIRouter, Query

from backend.models.schemas import (
    APIResponse,
    FeatureImportanceResponse,
    RiskDistributionResponse,
)
from backend.services.data_service import DataService

router = APIRouter(prefix="/api/v1/risk", tags=["Risk"])


@router.get(
    "/distribution",
    response_model=APIResponse,
    summary="Risk category distribution",
)
async def get_risk_distribution() -> APIResponse:
    """Return the number and percentage of citizens in each risk category
    (A through E), along with filer / non-filer counts.
    """
    svc = DataService()
    dist = svc.get_risk_distribution()
    return APIResponse(success=True, data=dist)

@router.get(
    "/income-wealth-gap",
    response_model=APIResponse,
    summary="Income to wealth gap analysis data",
)
async def get_income_wealth_gap() -> APIResponse:
    """Return scatter plot data comparing income to net worth ratios
    against deviation (risk) scores.
    """
    svc = DataService()
    data = svc.get_income_wealth_gap()
    return APIResponse(success=True, data=data)


@router.get(
    "/top-suspicious",
    response_model=APIResponse,
    summary="Top suspicious citizens",
)
async def get_top_suspicious(
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
) -> APIResponse:
    """Return the top-N citizens with the highest risk scores, ordered
    descending. Default limit is 20.
    """
    svc = DataService()
    results = svc.get_top_suspicious(limit=limit)
    return APIResponse(success=True, data=results)


@router.get(
    "/feature-importance",
    response_model=APIResponse,
    summary="ML feature importance",
)
async def get_feature_importance() -> APIResponse:
    """Return the feature-importance ranking used by the ML ensemble model.

    If a pre-computed feature importance file exists in ``data/processed/``,
    it is returned directly.  Otherwise a reasonable fallback importance
    derived from the configured deviation weights is returned.
    """
    svc = DataService()
    importance = svc.get_feature_importance()
    return APIResponse(success=True, data=importance)
