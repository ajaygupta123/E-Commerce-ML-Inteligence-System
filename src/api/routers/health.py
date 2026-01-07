"""Health check endpoints."""
from fastapi import APIRouter, Depends
from prometheus_client import generate_latest
from starlette.responses import Response

from ..schemas.common import HealthResponse
from ...services.prediction_service import PredictionService
from ...db.postgres import engine
from ...db.qdrant import get_qdrant_client
from ...services.llm_service import LLMService
from ...api.dependencies import get_prediction_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Basic health check."""
    return HealthResponse(status="healthy")


@router.get("/ready")
async def ready(prediction_service: PredictionService = Depends(get_prediction_service)):
    """Readiness check (DB, model loaded)."""
    checks = {
        "database": False,
        "qdrant": False,
        "model": False,
        "ollama": False,
    }
    
    # Check database
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    
    # Check Qdrant
    try:
        client = get_qdrant_client()
        client.get_collections()
        checks["qdrant"] = True
    except Exception:
        pass
    
    # Check model
    checks["model"] = prediction_service.is_ready
    
    # Check Ollama
    try:
        llm_service = LLMService()
        checks["ollama"] = await llm_service.health_check()
        await llm_service.close()
    except Exception:
        pass
    
    all_ready = all(checks.values())
    
    if all_ready:
        return {"status": "ready", "checks": checks}
    else:
        return Response(
            content=str({"status": "not ready", "checks": checks}),
            status_code=503
        )


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

