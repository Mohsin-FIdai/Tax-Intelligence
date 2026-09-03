"""
Tax Intelligence Platform — Model Service Layer

A thread-safe singleton that lazily loads AI models:
- bge-m3 (embeddings)
- bge-reranker-base (reranking)
- Ollama client for Qwen3-8B
"""

import importlib.util
_original_find_spec = importlib.util.find_spec
def _patched_find_spec(name, package=None):
    if name == 'tensorflow': return None
    return _original_find_spec(name, package)
importlib.util.find_spec = _patched_find_spec

import os
os.environ["HF_HUB_OFFLINE"] = "1"

import logging
import time
from threading import Lock
from typing import Optional, Tuple, Any

import httpx
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

class ModelService:
    """Thread-safe singleton for managing ML models."""

    _instance: Optional["ModelService"] = None
    _lock: Lock = Lock()

    def __new__(cls) -> "ModelService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialised = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialised:
            return
        self._initialised = True
        self._embedding_model: Optional[SentenceTransformer] = None
        self._reranker_model = None
        self._reranker_tokenizer = None
        self._llm_client: Optional[httpx.AsyncClient] = None
        self._lock = Lock()
        logger.info("ModelService initialized.")

    def get_embedding_model(self) -> SentenceTransformer:
        """Lazily load and return the embedding model."""
        if self._embedding_model is None:
            with self._lock:
                if self._embedding_model is None:
                    import os
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    start = time.time()
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    logger.info("Loading bge-m3 on %s (local files)...", device)
                    try:
                        self._embedding_model = SentenceTransformer("BAAI/bge-m3", device=device, local_files_only=True, model_kwargs={"torch_dtype": torch.float32})
                    except Exception:
                        self._embedding_model = SentenceTransformer("BAAI/bge-m3", device=device, model_kwargs={"torch_dtype": torch.float32})
                    logger.info("Loaded bge-m3 in %.2fs", time.time() - start)
        return self._embedding_model

    def get_reranker_model(self) -> Tuple[Any, Any]:
        """Lazily load and return the reranker model and tokenizer."""
        if self._reranker_model is None or self._reranker_tokenizer is None:
            with self._lock:
                if self._reranker_model is None:
                    import os
                    os.environ["HF_HUB_OFFLINE"] = "1"
                    start = time.time()
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    logger.info("Loading bge-reranker-base on %s (local files)...", device)
                    model_name = "BAAI/bge-reranker-base"
                    try:
                        self._reranker_tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
                        model = AutoModelForSequenceClassification.from_pretrained(
                            model_name,
                            local_files_only=True,
                            torch_dtype=torch.float32
                        )
                    except Exception:
                        self._reranker_tokenizer = AutoTokenizer.from_pretrained(model_name)
                        model = AutoModelForSequenceClassification.from_pretrained(
                            model_name,
                            torch_dtype=torch.float32
                        )
                    model.eval()
                    self._reranker_model = model.to(device)
                    logger.info("Loaded bge-reranker-base in %.2fs", time.time() - start)
        return self._reranker_model, self._reranker_tokenizer

    def get_llm_client(self) -> httpx.AsyncClient:
        """Return the httpx AsyncClient for Ollama."""
        if self._llm_client is None:
            with self._lock:
                if self._llm_client is None:
                    self._llm_client = httpx.AsyncClient(
                        base_url="http://localhost:11434",
                        timeout=120.0
                    )
                    logger.info("Initialized Ollama client.")
        return self._llm_client

    async def is_llm_available(self) -> bool:
        """Ping Ollama health endpoint to check availability."""
        client = self.get_llm_client()
        try:
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning("Ollama not available: %s", e)
            return False
