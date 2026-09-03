"""
Tax Intelligence Platform - Search API Routes

Global search endpoint that dispatches to the DataService search engine.
Enhanced with optional semantic search and re-ranking pipeline.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
import asyncio
import math
import numpy as np

from backend.models.schemas import APIResponse, SearchResult
from backend.services.data_service import DataService

router = APIRouter(prefix="/api/v1/search", tags=["Search"])
logger = logging.getLogger(__name__)

ALLOWED_SEARCH_TYPES = {"name", "cnic", "phone", "vehicle", "business"}

@router.get(
    "",
    response_model=APIResponse,
    summary="Global citizen search",
)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    type: str = Query(
        "name",
        description="Search type: name, cnic, phone, vehicle, business",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=200, description="Page size"),
    semantic: bool = Query(False, description="Use AI semantic search")
) -> APIResponse:
    search_type = type.lower()
    if search_type not in ALLOWED_SEARCH_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid search type '{type}'. Allowed: {', '.join(sorted(ALLOWED_SEARCH_TYPES))}"
        )

    svc = DataService()
    
    # Run the base search
    base_results = svc.search_citizens(q, search_type=search_type)
    
    results_map = {}
    for r in base_results:
        c_id = r.get("citizen_id")
        if c_id:
            r["match_method"] = "fuzzy/exact"
            r["confidence_score"] = 0.5
            results_map[c_id] = r
            
    if semantic and search_type == "name":
        try:
            from backend.services.embedding_service import EmbeddingService
            from backend.services.reranker_service import RerankerService
            
            emb_svc = EmbeddingService()
            sem_results = emb_svc.search(q, top_k=50)
            
            if sem_results:
                reranker = RerankerService()
                candidates = []
                for hit in sem_results:
                    c_id = hit["citizen_id"]
                    df = svc.citizens_df
                    match_df = df[df['citizen_id'] == c_id]
                    if not match_df.empty:
                        rec = match_df.iloc[0].to_dict()
                        rec["semantic_score"] = hit["score"]
                        candidates.append(rec)
                        
                reranked = reranker.rerank(q, candidates, text_field="canonical_name", top_k=50)
                
                for hit in reranked:
                    c_id = hit["citizen_id"]
                    if c_id in results_map:
                        results_map[c_id]["match_method"] = "both"
                        results_map[c_id]["confidence_score"] = hit.get("reranker_score", 0.9)
                    else:
                        hit["match_method"] = "semantic"
                        hit["confidence_score"] = hit.get("reranker_score", 0.8)
                        results_map[c_id] = hit
        except Exception as e:
            logger.error(f"Semantic search pipeline failed: {e}")
            
    if semantic:
        for hit in results_map.values():
            c_name = str(hit.get("canonical_name", "")).lower()
            q_lower = q.lower().strip()
            first_word = q_lower.split()[0] if q_lower else ""
            
            # If the primary name actually contains the main search term, give it a slight boost
            # so it ranks above relational matches (e.g. parent's name matching)
            if first_word and len(first_word) > 2 and first_word in c_name:
                hit["confidence_score"] = min(1.0, hit.get("confidence_score", 0.0) + 0.05)
                
        all_results = sorted(list(results_map.values()), key=lambda x: x.get("confidence_score", 0.0), reverse=True)
    else:
        all_results = base_results

    total_count = len(all_results)
    start = (page - 1) * page_size
    end = start + page_size
    final_results = all_results[start:end]

    for r in final_results:
        # Convert nan to empty strings for all string fields
        for k, v in list(r.items()):
            if isinstance(v, float) and math.isnan(v):
                r[k] = ""
            elif str(v).lower() == "nan":
                r[k] = ""

        if "cnic" in r and r["cnic"] is not None:
            r["cnic"] = str(r["cnic"]).replace(".0", "")
        for num_col in ["declared_income", "estimated_net_worth", "deviation_score", "estimated_hidden_income", "estimated_recoverable_tax", "risk_score"]:
            if num_col in r:
                val = r[num_col]
                if val is None or str(val) == "" or str(val).lower() == "nan" or (isinstance(val, float) and math.isnan(val)):
                    r[num_col] = 0.0
                else:
                    try:
                        r[num_col] = float(val)
                    except ValueError:
                        r[num_col] = 0.0

    search_result = SearchResult(
        results=final_results,
        total_count=total_count,
        page=page,
        page_size=page_size,
        query=q,
        search_type=search_type,
    )

    return APIResponse(success=True, data=search_result.model_dump())
