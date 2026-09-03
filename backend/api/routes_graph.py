"""
Tax Intelligence Platform — Graph API Routes

Endpoints for knowledge-graph statistics, ego-network subgraphs,
and community summaries.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.models.schemas import (
    APIResponse,
    CommunityInfo,
    EgoGraph,
    ErrorResponse,
    GraphStats,
)
from backend.services.data_service import DataService

router = APIRouter(prefix="/api/v1/graph", tags=["Graph"])


@router.get(
    "/stats",
    response_model=APIResponse,
    summary="Get knowledge-graph statistics",
)
async def get_graph_stats() -> APIResponse:
    """Return high-level statistics about the knowledge graph including
    node count, edge count, density, communities, and connected components.
    """
    svc = DataService()
    stats = svc.get_graph_stats()
    return APIResponse(success=True, data=stats)


@router.get(
    "/communities/{community_id}",
    response_model=APIResponse,
    summary="Get subgraph for a specific community",
)
async def get_community(community_id: int) -> APIResponse:
    """Return the subgraph nodes and edges for a specific community."""
    svc = DataService()
    subgraph = svc.get_community_graph(community_id)
    return APIResponse(success=True, data=subgraph)


@router.get(
    "/ego/{citizen_id}",
    response_model=APIResponse,
    summary="Get ego-network for a citizen",
    responses={404: {"model": ErrorResponse}},
)
async def get_ego_graph(
    citizen_id: str,
    radius: int = Query(1, ge=1, le=3, description="Hop radius from centre"),
) -> APIResponse:
    """Return the ego-network subgraph centred on a citizen.

    Each node includes label, type, risk score, category, and colour.
    Each edge includes source, target, relationship type, and weight.

    The *radius* parameter controls how many hops from the centre to include
    (default 1, max 3 to prevent excessively large payloads).
    """
    svc = DataService()

    # Check the citizen exists in the master data
    row = svc.citizens_df[svc.citizens_df["citizen_id"] == citizen_id]
    if row.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Citizen '{citizen_id}' not found",
        )

    ego = svc.get_ego_graph(citizen_id, radius=radius)
    return APIResponse(success=True, data=ego)


@router.get(
    "/communities",
    response_model=APIResponse,
    summary="List graph communities",
)
async def get_communities(
    limit: int = Query(50000, ge=1, le=100000, description="Max communities to return"),
) -> APIResponse:
    """Return a summary of detected communities in the knowledge graph.

    Each community entry includes its ID, member count, average risk score,
    and a list of the top member citizen IDs.
    """
    svc = DataService()
    communities = svc.get_communities()

    # Sort by member count descending, then trim
    communities.sort(key=lambda c: c.get("member_count", 0), reverse=True)
    communities = communities[:limit]

    return APIResponse(success=True, data=communities)
