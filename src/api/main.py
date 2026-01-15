"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx
import asyncio
import json

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
    
    # Pull Ollama model if not already available (non-blocking)
    async def pull_ollama_model():
        """Pull Ollama model in background."""
        try:
            ollama_url = f"http://{settings.ollama_host}:{settings.ollama_port}"
            # Wait for Ollama to be ready
            for i in range(30):  # Wait up to 60 seconds
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{ollama_url}/api/tags")
                        if response.status_code == 200:
                            break
                except Exception:
                    pass
                await asyncio.sleep(2)
            
            # Check if model is already available
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{ollama_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    if settings.llm_model in model_names:
                        logger.info(f"Ollama model {settings.llm_model} already available")
                        return
            
            # Pull the model
            logger.info(f"Pulling Ollama model {settings.llm_model} (this may take a few minutes)...")
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout for pull
                try:
                    # Use streaming to track progress and wait for completion
                    async with client.stream(
                        "POST",
                        f"{ollama_url}/api/pull",
                        json={"name": settings.llm_model},
                        timeout=300.0
                    ) as response:
                        if response.status_code == 200:
                            # Stream the response to completion
                            pull_complete = False
                            async for line in response.aiter_lines():
                                if line:
                                    try:
                                        data = json.loads(line)
                                        status = data.get("status", "")
                                        if status == "success":
                                            logger.info(f"Successfully pulled Ollama model {settings.llm_model}")
                                            pull_complete = True
                                            break
                                        elif status == "pulling":
                                            # Log progress occasionally
                                            if "total" in data or "completed" in data:
                                                pass  # Progress update
                                    except:
                                        pass
                            if not pull_complete:
                                logger.info(f"Ollama model pull initiated (may still be downloading)")
                        else:
                            logger.warning(f"Failed to pull Ollama model: {response.status_code}. It will be pulled on first use.")
                except Exception as pull_err:
                    logger.warning(f"Error during model pull: {pull_err}. It will be pulled on first use.")
        except Exception as e:
            logger.warning(f"Failed to pull Ollama model: {e}. It will be pulled on first use.")
    
    # Start pulling Ollama model in background (non-blocking)
    asyncio.create_task(pull_ollama_model())
    
    # Initialize databases
    try:
        await init_db()
        await init_qdrant(vector_size=384)  # all-MiniLM-L6-v2 embedding size
        logger.info("Databases initialized")
        
        # Check if Qdrant collection is empty and seed if needed
        async def check_and_seed():
            """Check if collection is empty and seed if needed."""
            try:
                from ..db.qdrant import get_qdrant_client
                from ..core.config import settings
                import sys
                from pathlib import Path
                
                # Wait a bit for Qdrant to be fully ready
                await asyncio.sleep(3)
                
                qdrant_client = get_qdrant_client()
                collection_name = settings.qdrant_collection_name
                
                # Simple check: try to scroll and see if we get any points
                has_data = False
                try:
                    result = qdrant_client.scroll(collection_name, limit=1)
                    if result and len(result) >= 2 and len(result[0]) > 0:
                        has_data = True
                        logger.info(f"Qdrant collection has data. Skipping seeding.")
                except Exception as e:
                    # If scroll fails, assume empty (might be version issue)
                    logger.debug(f"Could not check collection via scroll: {e}")
                
                if not has_data:
                    logger.info("Qdrant collection appears empty. Seeding database with sample products...")
                    try:
                        # Import seed function
                        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                        from scripts.seed_database import seed_products
                        await seed_products()
                        logger.info("Database seeding completed successfully")
                    except Exception as e:
                        logger.warning(f"Failed to seed database: {e}. You can seed manually using: docker exec ecommerce-api python scripts/seed_database.py")
            except Exception as e:
                logger.warning(f"Could not check/seed Qdrant collection: {e}")
        
        # Run seeding check in background (non-blocking)
        asyncio.create_task(check_and_seed())
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




