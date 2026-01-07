"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routers import health, prediction, rag, evaluation, explainability, monitoring, drift, retraining
from .middleware.request_id import RequestIDMiddleware
from .middleware.rate_limiter import RateLimiterMiddleware
from .middleware.metrics import MetricsMiddleware
from ..core.config import settings
from ..core.logging import setup_logging
from ..db.postgres import init_db
from ..db.qdrant import init_qdrant
from ..api.dependencies import get_prediction_service
from ..services.scheduler_service import SchedulerService

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    # Startup
    logger.info("Starting application...")
    
    # Initialize databases
    try:
        await init_db()
        await init_qdrant(vector_size=384)  # all-MiniLM-L6-v2 embedding size
        logger.info("Databases initialized")
    except Exception as e:
        logger.error(f"Failed to initialize databases: {e}")
    
    # Load ML model
    try:
        prediction_service = get_prediction_service()
        await prediction_service.initialize()
        logger.info("ML model loaded")
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}")
    
    # Start scheduler for drift detection
    scheduler = SchedulerService()
    try:
        await scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Shutdown scheduler
    if hasattr(app.state, 'scheduler'):
        await app.state.scheduler.shutdown()


# Create FastAPI app
app = FastAPI(
    title="E-commerce ML Intelligence System",
    description="Predictive ML and RAG-powered Q&A system for e-commerce",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",") if settings.allowed_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(MetricsMiddleware)

# Include routers
app.include_router(health.router)
app.include_router(prediction.router)
app.include_router(rag.router)
app.include_router(evaluation.router)
app.include_router(explainability.router)
app.include_router(monitoring.router)
app.include_router(drift.router)
app.include_router(retraining.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "E-commerce ML Intelligence System API",
        "version": "1.0.0",
        "docs": "/docs",
    }




