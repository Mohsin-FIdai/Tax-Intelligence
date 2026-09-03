"""
Tax Intelligence Platform — FastAPI Application Entry Point

Creates the FastAPI app, attaches CORS middleware, registers all API
routers, and exposes a health-check endpoint.
"""

import importlib.util
_original_find_spec = importlib.util.find_spec
def _patched_find_spec(name, package=None):
    if name == 'tensorflow': return None
    return _original_find_spec(name, package)
importlib.util.find_spec = _patched_find_spec

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from backend.api import (
    routes_citizens,
    routes_graph,
    routes_reports,
    routes_risk,
    routes_search,
    routes_resolution,
    routes_chat,
    routes_email,
    routes_ingestion,
)
from backend.models.schemas import HealthCheck
from backend.services.data_service import DataService

# ─── Logging ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Lifespan ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook.

    On startup the DataService singleton is instantiated so that all CSV
    and pickle files are loaded into memory before the first request.
    """
    logger.info("Tax Intelligence API — starting up …")
    svc = DataService()
    logger.info(
        "DataService initialised  (data loaded = %s, citizens = %d)",
        svc.is_loaded,
        len(svc.citizens_df),
    )
    # Warm up resolution and raw record cache in background
    try:
        from backend.api.routes_resolution import _init_raw_cache, get_resolution_reviews
        _init_raw_cache()
        get_resolution_reviews(page=1, limit=50, filter_decision="REVIEW", svc=svc)
        logger.info("Resolution caches pre-warmed successfully.")
    except Exception as e:
        logger.warning("Cache pre-warm skipped: %s", e)

    # Re-initialize embeddings index in background
    try:
        from backend.services.embedding_service import EmbeddingService
        emb_svc = EmbeddingService()
        emb_svc.initialize_index()
    except Exception as e:
        logger.warning("Embedding init skipped: %s", e)


    yield
    logger.info("Tax Intelligence API — shutting down …")


# ─── App Factory ──────────────────────────────────────────────────────

app = FastAPI(
    title="Tax Intelligence API",
    description=(
        "Backend REST API for the Graph AI Tax Intelligence Platform — "
        "citizen profiling, risk scoring, knowledge-graph analytics, "
        "entity resolution, and reporting for Pakistan's tax ecosystem."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────

app.include_router(routes_citizens.router)
app.include_router(routes_graph.router)
app.include_router(routes_risk.router)
app.include_router(routes_search.router)
app.include_router(routes_reports.router)
app.include_router(routes_resolution.router)
app.include_router(routes_chat.router)
app.include_router(routes_email.router)
app.include_router(routes_ingestion.router)

# ─── Health Check ─────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthCheck,
    tags=["Health"],
    summary="API health check",
)
async def health_check() -> HealthCheck:
    """Return the current health status of the API.

    Includes service status, API version, current UTC timestamp,
    and whether the data layer has been loaded successfully.
    """
    svc = DataService()
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        data_loaded=svc.is_loaded,
    )


@app.get("/", tags=["Health"], summary="Root redirect info")
async def root() -> dict:
    """Root endpoint — provides discovery links."""
    return {
        "service": "Tax Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }

@app.post("/system/reload", tags=["System"], summary="Reload DataService")
async def system_reload() -> dict:
    """Force the backend DataService to reload all files into memory."""
    svc = DataService()
    svc.reload()
    return {
        "status": "success",
        "message": "Data reloaded successfully",
        "citizens": len(svc.citizens_df)
    }
