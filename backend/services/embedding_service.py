"""
Tax Intelligence Platform — Embedding Service Layer

Handles embedding computation and FAISS vector search.
"""

import logging
from pathlib import Path

import faiss
import numpy as np

from config.settings import PROCESSED_DIR
from backend.services.model_service import ModelService

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Singleton embedding service for FAISS vector search."""

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
        self.index_path = PROCESSED_DIR / "embeddings.faiss"
        self.ids_path = PROCESSED_DIR / "embedding_ids.npy"
        self.index = None
        self.embedding_ids = None

    def is_ready(self) -> bool:
        """Check if the FAISS index is loaded and ready."""
        return self.index is not None and self.embedding_ids is not None

    def initialize_index(self) -> None:
        """Load or build the FAISS index. Called from startup background task."""
        from backend.services.data_service import DataService
        svc = DataService()
        self.load_or_build_index(svc)

    def build_index(self, data_service) -> None:
        """Build FAISS index from citizen data."""
        logger.info("Building FAISS index...")
        if not data_service.is_loaded:
            logger.warning("DataService not loaded, cannot build index.")
            return

        citizens = data_service.citizens_df
        if citizens.empty:
            logger.warning("No citizens found, skipping index build.")
            return

        texts = []
        ids = []
        for _, row in citizens.iterrows():
            canonical_name = row.get("canonical_name", "")
            father_name = row.get("father_name", "")
            address = row.get("address", "")
            city = row.get("city", "")

            parts = []
            if canonical_name: parts.append(str(canonical_name))
            if father_name: parts.append(str(father_name))
            if address: parts.append(str(address))
            if city: parts.append(str(city))

            text = " ".join(parts).strip()
            if text:
                texts.append(text)
                ids.append(str(row.get("citizen_id", "")))

        if not texts:
            logger.warning("No valid text found for embeddings.")
            return

        model = self.model_service.get_embedding_model()
        logger.info("Encoding %d citizen records...", len(texts))

        embeddings = model.encode(
            texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True
        )

        # Normalize embeddings for cosine similarity with IndexFlatIP
        faiss.normalize_L2(embeddings)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        self.embedding_ids = np.array(ids)

        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        np.save(str(self.ids_path), self.embedding_ids)

        logger.info(
            "FAISS index built: %d vectors, %d dims, saved to %s",
            len(ids), dim, self.index_path,
        )

    def load_or_build_index(self, data_service) -> None:
        """Load index from disk or build if it doesn't exist."""
        if self.index_path.exists() and self.ids_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                self.embedding_ids = np.load(str(self.ids_path), allow_pickle=True)
                logger.info(
                    "Loaded FAISS index from disk (%d vectors).", self.index.ntotal
                )
            except Exception as e:
                logger.error("Failed to load FAISS index: %s", e)
                self.build_index(data_service)
        else:
            self.build_index(data_service)

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        """Search FAISS index for query."""
        if not self.is_ready():
            logger.warning("FAISS index not initialized.")
            return []

        model = self.model_service.get_embedding_model()
        query_emb = model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_emb)

        scores, indices = self.index.search(query_emb, min(top_k, len(self.embedding_ids)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                results.append({
                    "citizen_id": str(self.embedding_ids[idx]),
                    "score": float(score),
                })

        return results
