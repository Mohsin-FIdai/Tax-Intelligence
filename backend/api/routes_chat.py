"""
Tax Intelligence Platform — AI Chat & Summary API Routes

Endpoints for the AI chatbot and citizen investigation summaries.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.services.data_service import DataService
from backend.services.llm_service import LLMService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    citizen_id: Optional[str] = None
    stream: Optional[bool] = False


@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Chat with the AI assistant. Optionally provide citizen_id for context."""
    try:
        llm_svc = LLMService()
        svc = DataService()

        context_data = None
        has_context = False

        import re
        if not req.citizen_id:
            match = re.search(r'(CZ-[A-Z0-9]+)', req.message, re.IGNORECASE)
            if match:
                req.citizen_id = match.group(1).upper()

        if req.citizen_id:
            cit_data = svc.get_citizen_by_id(req.citizen_id)
            if cit_data:
                context_data = cit_data
                has_context = True
        else:
            # Dynamic system context for global questions
            msg_lower = req.message.lower()
            if "critical flag" in msg_lower or "high risk" in msg_lower:
                top_risks = svc.get_top_suspicious(limit=5)
                context_data = {
                    "system_status": "Active",
                    "top_critical_entities": [
                        {"id": c["citizen_id"], "name": c["name"], "risk": c["risk_score"], "category": c.get("risk_category", "")} for c in top_risks
                    ]
                }
                has_context = True
            elif "deviation score" in msg_lower or "risk score" in msg_lower:
                context_data = {
                    "documentation": "Deviation/Risk Score is calculated by aggregating: 1) Unexplained wealth gaps (declared income vs asset value), 2) Cross-border financial anomalies, 3) Real estate transactions not matching tax brackets. A score > 80 is considered Critical."
                }
                has_context = True
            else:
                # If no specific context, USE RAG! Run a semantic search on the user's message
                try:
                    from backend.services.embedding_service import EmbeddingService
                    emb_svc = EmbeddingService()
                    if emb_svc.is_ready():
                        search_results = emb_svc.search(req.message, top_k=5)
                        
                        rag_citizens = []
                        for res in search_results:
                            c = svc.get_citizen_by_id(res["citizen_id"])
                            if c:
                                rag_citizens.append({
                                    "name": c["canonical_name"],
                                    "id": c["citizen_id"],
                                    "risk": c["risk_score"],
                                    "assets": len(c.get("assets", [])),
                                    "address": c.get("address", "")
                                })
                        
                        if rag_citizens:
                            context_data = {
                                "Search Results relevant to the query": rag_citizens
                            }
                            has_context = True
                except Exception as e:
                    logger.warning(f"RAG search failed: {e}")

        if req.stream:
            async def event_stream():
                async for chunk in await llm_svc.chat(req.message, citizen_context=context_data, stream=True):
                    yield chunk
            return StreamingResponse(event_stream(), media_type="text/plain")

        response_text = await llm_svc.chat(req.message, citizen_context=context_data, stream=False)
        return {
            "success": True, 
            "response": response_text, 
            "citizen_context": has_context
        }
    except Exception as e:
        logger.error("Chat endpoint error: %s", e)
        raise HTTPException(status_code=500, detail="The AI service is currently unavailable. Please ensure Ollama is running.")


@router.get("/citizens/{citizen_id}/summary")
async def generate_citizen_summary(citizen_id: str, stream: bool = False):
    """Generate an AI investigation summary for a specific citizen."""
    try:
        svc = DataService()
        llm_svc = LLMService()

        cit_data = svc.get_citizen_by_id(citizen_id)
        if not cit_data:
            raise HTTPException(status_code=404, detail="Citizen not found")

        if stream:
            async def event_stream():
                async for chunk in await llm_svc.generate_citizen_summary(cit_data, stream=True):
                    yield chunk
            return StreamingResponse(event_stream(), media_type="text/plain")

        summary = await llm_svc.generate_citizen_summary(cit_data, stream=False)
        return {"success": True, "summary": summary, "citizen_id": citizen_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Summary generation error: %s", e)
        return {
            "success": False,
            "summary": "Unable to generate AI summary. Please ensure Ollama is running with Qwen2.5-3B.",
            "citizen_id": citizen_id,
        }


@router.get("/status")
async def ai_status():
    """Check the status of all AI services."""
    result = {"llm": False, "embeddings": False, "reranker": False}
    try:
        from backend.services.embedding_service import EmbeddingService
        from backend.services.reranker_service import RerankerService

        llm_svc = LLMService()
        emb_svc = EmbeddingService()

        result["llm"] = await llm_svc.is_available()
        result["embeddings"] = emb_svc.is_ready()

        try:
            rerank_svc = RerankerService()
            result["reranker"] = rerank_svc.is_ready()
        except Exception:
            pass
    except Exception as e:
        logger.warning("AI status check partial failure: %s", e)

    return result
