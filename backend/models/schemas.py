"""
Tax Intelligence Platform — Pydantic v2 Schema Definitions

All request/response models for the REST API. Uses Pydantic v2 conventions:
model_dump(), model_validate(), ConfigDict(from_attributes=True).
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Health Check ─────────────────────────────────────────────────────

class HealthCheck(BaseModel):
    """API health-check response."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="Service status", examples=["healthy"])
    version: str = Field(..., description="API version", examples=["1.0.0"])
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the check",
    )
    data_loaded: bool = Field(
        default=False, description="Whether the data layer is ready"
    )


# ─── Pagination & Filtering ──────────────────────────────────────────

class PaginationParams(BaseModel):
    """Query-level pagination parameters."""

    model_config = ConfigDict(from_attributes=True)

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=25, ge=1, le=200, description="Items per page (max 200)"
    )


class FilterParams(BaseModel):
    """Optional filter parameters for citizen listing."""

    model_config = ConfigDict(from_attributes=True)

    province: Optional[str] = Field(default=None, description="Filter by province")
    city: Optional[str] = Field(default=None, description="Filter by city")
    risk_level: Optional[str] = Field(
        default=None,
        description="Risk category letter: A, B, C, D, or E",
    )
    filing_status: Optional[str] = Field(
        default=None,
        description="Filer or Non-Filer",
    )
    min_income: Optional[float] = Field(
        default=None, ge=0, description="Minimum declared income"
    )
    max_income: Optional[float] = Field(
        default=None, ge=0, description="Maximum declared income"
    )
    min_risk_score: Optional[float] = Field(
        default=None, ge=0, le=100, description="Minimum risk score"
    )
    max_risk_score: Optional[float] = Field(
        default=None, ge=0, le=100, description="Maximum risk score"
    )
    sort_by: Optional[str] = Field(
        default="risk_score",
        description="Column to sort by",
    )
    sort_order: Optional[str] = Field(
        default="desc",
        description="Sort direction: asc or desc",
    )


# ─── Citizen Models ──────────────────────────────────────────────────

class CitizenSummary(BaseModel):
    """Lightweight citizen record for list views."""

    model_config = ConfigDict(from_attributes=True)

    citizen_id: str = Field(..., description="Unique citizen identifier")
    name: str = Field(..., description="Full name")
    canonical_name: str = Field(default="", description="Canonical resolved name")
    urdu_name: str = Field(default="", description="Native Urdu script name")
    cnic: str = Field(..., description="CNIC number (13 digits)")
    city: str = Field(default="", description="City of residence")
    province: str = Field(default="", description="Province")
    risk_score: float = Field(
        default=0.0, ge=0, le=100, description="Composite risk score 0-100"
    )
    risk_category: str = Field(default="A", description="Risk category letter A-E")
    filing_status: str = Field(default="Non-Filer", description="Filer / Non-Filer")
    declared_income: float = Field(default=0.0, description="Declared annual income")
    estimated_net_worth: float = Field(default=0.0, description="Estimated net worth")
    deviation_score: float = Field(default=0.0, description="Deviation score 0-100")
    estimated_hidden_income: float = Field(default=0.0, description="Estimated hidden income")
    estimated_recoverable_tax: float = Field(default=0.0, description="Estimated recoverable tax")
    match_method: Optional[str] = Field(default=None, description="Search match method: fuzzy, semantic, both")
    confidence_score: Optional[float] = Field(default=None, description="Similarity / reranking score")


class TaxRecord(BaseModel):
    """Single tax-year record."""

    model_config = ConfigDict(from_attributes=True)

    tax_year: Optional[str] = Field(default=None, description="Tax year")
    declared_income: float = Field(default=0.0)
    tax_paid: float = Field(default=0.0)
    tax_due: float = Field(default=0.0)
    filing_date: Optional[str] = Field(default=None)


class AuditTrailItem(BaseModel):
    """Single audit-trail flag for a citizen."""

    model_config = ConfigDict(from_attributes=True)

    description: str = Field(..., description="Human-readable flag description")
    severity: str = Field(
        default="info",
        description="Severity level: info, warning, critical",
    )
    value: Optional[float] = Field(
        default=None, description="Actual observed value"
    )
    threshold: Optional[float] = Field(
        default=None, description="Threshold that was exceeded"
    )


class AnomalyScores(BaseModel):
    """Per-model anomaly scores for a citizen."""

    model_config = ConfigDict(from_attributes=True)

    isolation_forest: Optional[float] = Field(default=None)
    xgboost: Optional[float] = Field(default=None)
    random_forest: Optional[float] = Field(default=None)
    ensemble: Optional[float] = Field(default=None)


class RiskDetail(BaseModel):
    """Detailed risk breakdown for a citizen."""

    model_config = ConfigDict(from_attributes=True)

    deviation_score: float = Field(default=0.0, description="Wealth-income deviation")
    suspicion_pct: float = Field(
        default=0.0, description="Suspicion percentage 0–100"
    )
    category: str = Field(default="A", description="Risk category letter")
    label: str = Field(default="Tax Compliant", description="Human-readable label")
    color: str = Field(default="#10b981", description="Hex colour for the category")
    anomaly_scores: AnomalyScores = Field(default_factory=AnomalyScores)
    income_networth_gap: float = Field(default=0.0)
    tax_gap: float = Field(default=0.0)
    lifestyle_gap: float = Field(default=0.0)
    filing_penalty: float = Field(default=0.0)


# ─── Asset Models ────────────────────────────────────────────────────

class VehicleAsset(BaseModel):
    """Vehicle record."""

    model_config = ConfigDict(from_attributes=True)

    vehicle_type: str = Field(default="", description="Car, Motorcycle, etc.")
    make: str = Field(default="")
    model: str = Field(default="")
    year: Optional[int] = Field(default=None)
    registration_number: str = Field(default="")
    estimated_value: float = Field(default=0.0)


class PropertyAsset(BaseModel):
    """Property record."""

    model_config = ConfigDict(from_attributes=True)

    property_type: str = Field(default="", description="Residential, Commercial, etc.")
    location: str = Field(default="")
    area_sqft: float = Field(default=0.0)
    estimated_value: float = Field(default=0.0)
    registration_date: Optional[str] = Field(default=None)


class BusinessAsset(BaseModel):
    """Business registration record."""

    model_config = ConfigDict(from_attributes=True)

    business_name: str = Field(default="")
    business_type: str = Field(default="")
    ntn: str = Field(default="", description="National Tax Number")
    annual_turnover: float = Field(default=0.0)
    registration_date: Optional[str] = Field(default=None)


class BankAccountAsset(BaseModel):
    """Bank account indicator record."""

    model_config = ConfigDict(from_attributes=True)

    record_id: str = Field(default="")
    account_last4: str = Field(default="")
    bank_name: str = Field(default="")
    account_type: str = Field(default="")
    monthly_expenditure_pkr: float = Field(default=0.0)
    annual_expenditure_pkr: float = Field(default=0.0)
    city: str = Field(default="")
    province: str = Field(default="")


class AssetBreakdown(BaseModel):
    """Full asset inventory for a citizen."""

    model_config = ConfigDict(from_attributes=True)

    vehicles: list[VehicleAsset] = Field(default_factory=list)
    properties: list[PropertyAsset] = Field(default_factory=list)
    businesses: list[BusinessAsset] = Field(default_factory=list)
    travel: list[dict] = Field(default_factory=list)
    utilities: list[dict] = Field(default_factory=list)
    banking: list[BankAccountAsset] = Field(default_factory=list)
    total_value: float = Field(default=0.0, description="Combined estimated value")


class CitizenProfile(BaseModel):
    """Full citizen profile — returned on detail view."""

    model_config = ConfigDict(from_attributes=True)

    citizen_id: str
    name: str
    canonical_name: str = ""
    urdu_name: str = ""
    cnic: str
    father_name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    city: str = ""
    province: str = ""
    date_of_birth: Optional[str] = None
    ntn: str = ""
    filing_status: str = "Non-Filer"
    declared_income: float = 0.0
    estimated_net_worth: float = 0.0
    risk_score: float = 0.0
    risk_category: str = "A"

    assets: AssetBreakdown = Field(default_factory=AssetBreakdown)
    tax_records: list[TaxRecord] = Field(default_factory=list)
    risk_details: RiskDetail = Field(default_factory=RiskDetail)
    audit_trail: list[AuditTrailItem] = Field(default_factory=list)


# ─── Entity Resolution Models ────────────────────────────────────────

class EntityMatch(BaseModel):
    """A pair of citizen records that likely refer to the same person."""

    model_config = ConfigDict(from_attributes=True)

    pair_id: str = Field(..., description="Unique match-pair identifier")
    record1_id: str = Field(..., description="First citizen ID")
    record2_id: str = Field(..., description="Second citizen ID")
    record1_name: str = Field(default="")
    record2_name: str = Field(default="")
    confidence: float = Field(
        ..., ge=0, le=100, description="Match confidence 0–100"
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Explanation strings for the match",
    )


# ─── Graph Models ────────────────────────────────────────────────────

class GraphStats(BaseModel):
    """Summary statistics for the knowledge graph."""

    model_config = ConfigDict(from_attributes=True)

    node_count: int = Field(default=0)
    edge_count: int = Field(default=0)
    density: float = Field(default=0.0)
    communities_count: int = Field(default=0)
    avg_degree: float = Field(default=0.0)
    connected_components: int = Field(default=0)


class GraphNode(BaseModel):
    """Single node in a graph payload."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str = ""
    node_type: str = "citizen"
    risk_score: float = 0.0
    risk_category: str = "A"
    size: float = 10.0
    color: str = "#00d4aa"


class GraphEdge(BaseModel):
    """Single edge in a graph payload."""

    model_config = ConfigDict(from_attributes=True)

    source: str
    target: str
    relationship: str = ""
    weight: float = 1.0


class EgoGraph(BaseModel):
    """Ego-network subgraph payload."""

    model_config = ConfigDict(from_attributes=True)

    center_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class CommunityInfo(BaseModel):
    """Community / cluster summary."""

    model_config = ConfigDict(from_attributes=True)

    community_id: int
    member_count: int = 0
    avg_risk_score: float = 0.0
    top_members: list[str] = Field(default_factory=list)


# ─── Search Models ───────────────────────────────────────────────────

class SearchResult(BaseModel):
    """Paginated search response."""

    model_config = ConfigDict(from_attributes=True)

    results: list[CitizenSummary] = Field(default_factory=list)
    total_count: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=25)
    query: str = Field(default="")
    search_type: str = Field(default="name")


# ─── Risk Aggregation Models ─────────────────────────────────────────

class RiskDistribution(BaseModel):
    """Category-level counts for the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    category: str
    label: str
    color: str
    count: int = 0
    percentage: float = 0.0


class RiskDistributionResponse(BaseModel):
    """Full risk distribution response."""

    model_config = ConfigDict(from_attributes=True)

    total_citizens: int = 0
    filer_count: int = 0
    non_filer_count: int = 0
    categories: list[RiskDistribution] = Field(default_factory=list)


class FeatureImportance(BaseModel):
    """Single feature importance entry."""

    model_config = ConfigDict(from_attributes=True)

    feature: str
    importance: float = 0.0


class FeatureImportanceResponse(BaseModel):
    """Feature importance response."""

    model_config = ConfigDict(from_attributes=True)

    model_name: str = "ensemble"
    features: list[FeatureImportance] = Field(default_factory=list)


# ─── Generic Wrappers ────────────────────────────────────────────────

class APIResponse(BaseModel):
    """Standard envelope for API responses."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    message: str = ""
    data: Any = None


class PaginatedResponse(BaseModel):
    """Paginated list envelope."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    data: list[Any] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 25
    total_pages: int = 0


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = False
    error: str = ""
    detail: str = ""
    status_code: int = 500
