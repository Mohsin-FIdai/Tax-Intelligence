"""
Tax Intelligence Platform — Reranker Service Layer

Handles second-stage re-ranking using bge-reranker-base.
"""

import logging

import torch

from backend.services.model_service import ModelService

logger = logging.getLogger(__name__)


class RerankerService:
    """Singleton reranker service using bge-reranker-base."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self._initialised = True
        self.model_service = ModelService()

    def is_ready(self) -> bool:
        """Check if the reranker model can be loaded."""
        try:
            self.model_service.get_reranker_model()
            return True
        except Exception:
            return False

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        text_field: str = "name",
        top_k: int = 10,
    ) -> list[dict]:
        """Rerank candidates based on query relevance.

        Args:
            query: The search query text.
            candidates: List of candidate dicts. Each must contain `text_field`.
            text_field: Key in each candidate dict to use as comparison text.
            top_k: Maximum number of results to return.

        Returns:
            Candidates sorted by reranker confidence with `reranker_score` added.
        """
        if not query or not candidates:
            return []

        model, tokenizer = self.model_service.get_reranker_model()

        pairs = []
        valid_candidates = []

        for cand in candidates:
            # Build an enriched profile description for high-precision reranking
            parts = []
            c_name = cand.get("canonical_name", "") or cand.get("name", "")
            f_name = cand.get("father_name", "")
            city = cand.get("city", "")
            prov = cand.get("province", "")
            cnic = cand.get("cnic", "")
            
            if c_name: parts.append(str(c_name))
            if f_name: parts.append(f"s/o {f_name}")
            if city: parts.append(str(city))
            if prov: parts.append(str(prov))
            if cnic: parts.append(f"CNIC {cnic}")
            
            text = " ".join(parts).strip()
            if not text:
                text = str(cand.get(text_field, ""))

            if text:
                pairs.append([query, str(text)])
                valid_candidates.append(cand)

        if not pairs:
            return []

        try:
            with torch.no_grad():
                inputs = tokenizer(
                    pairs,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    max_length=512,
                ).to(model.device)

                scores = model(**inputs, return_dict=True).logits.view(-1).float()
                # Apply sigmoid to get 0-1 scores
                probabilities = torch.sigmoid(scores).cpu().numpy().tolist()

            for cand, score in zip(valid_candidates, probabilities):
                cand["reranker_score"] = round(score, 4)
                cand["confidence_score"] = round(score, 4)

            # Sort by reranker_score descending
            valid_candidates.sort(
                key=lambda x: x.get("reranker_score", 0), reverse=True
            )
            return valid_candidates[:top_k]

        except Exception as e:
            logger.error("Reranking failed: %s", e)
            return candidates[:top_k]
