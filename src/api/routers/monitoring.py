"""Monitoring endpoints for system overview."""
from fastapi import APIRouter, Depends
from typing import Dict, Any
import subprocess
import json

from ...db.postgres import get_db_session
from ...db.qdrant import get_qdrant_client
from ...services.llm_service import LLMService
from ...api.dependencies import get_prediction_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1", tags=["monitoring"])


@router.get("/system_status")
async def get_system_status(
    db_session: AsyncSession = Depends(get_db_session),
    prediction_service = Depends(get_prediction_service),
) -> Dict[str, Any]:
    """
    Get comprehensive system status - Bird's Eye View.
    
    Returns:
        - Health status of all components
        - Database connection pool stats
        - Container resource usage
        - API metrics summary
    """
    status = {
        "timestamp": None,
        "health": {},
        "components": {},
        "database": {},
        "resources": {},
    }
    
    from datetime import datetime
    status["timestamp"] = datetime.now().isoformat()
    
    # Health checks
    try:
        # Database
        await db_session.execute("SELECT 1")
        status["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
    
    try:
        # Qdrant
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections()
        status["components"]["qdrant"] = {"status": "healthy", "collections": len(collections.collections)}
    except Exception as e:
        status["components"]["qdrant"] = {"status": "unhealthy", "error": str(e)}
    
    try:
        # Ollama
        llm_service = LLMService()
        is_healthy = await llm_service.health_check()
        status["components"]["ollama"] = {"status": "healthy" if is_healthy else "unhealthy"}
    except Exception as e:
        status["components"]["ollama"] = {"status": "unhealthy", "error": str(e)}
    
    try:
        # Model
        model_loaded = prediction_service.model is not None
        status["components"]["model"] = {"status": "loaded" if model_loaded else "not_loaded"}
    except Exception as e:
        status["components"]["model"] = {"status": "error", "error": str(e)}
    
    # Database connection pool stats
    try:
        # Get connection pool info from SQLAlchemy engine
        from ...db.postgres import engine
        pool = engine.pool
        status["database"] = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
        }
    except Exception as e:
        status["database"] = {"error": str(e)}
    
    # Container resource usage (if running in Docker)
    try:
        containers = ["ecommerce-api", "ecommerce-postgres", "ecommerce-qdrant", "ecommerce-ollama"]
        container_stats = {}
        for container in containers:
            try:
                result = subprocess.run(
                    ["docker", "stats", "--no-stream", "--format", "json", container],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout.strip())
                    container_stats[container] = {
                        "cpu_percent": data.get("CPUPerc", "0%"),
                        "memory_usage": data.get("MemUsage", "N/A"),
                        "memory_percent": data.get("MemPerc", "0%"),
                    }
            except Exception:
                pass
        
        if container_stats:
            status["resources"]["containers"] = container_stats
    except Exception:
        pass
    
    return status


@router.get("/system_summary")
async def get_system_summary() -> Dict[str, Any]:
    """
    Get quick system summary for dashboard.
    
    Returns a concise summary of system health.
    """
    summary = {
        "status": "healthy",
        "components": {},
        "warnings": [],
    }
    
    # Quick health checks
    try:
        from fastapi import status as http_status
        import httpx
        
        async with httpx.AsyncClient() as client:
            health_response = await client.get("http://localhost:8000/health", timeout=2)
            summary["components"]["api"] = "healthy" if health_response.status_code == 200 else "unhealthy"
            
            ready_response = await client.get("http://localhost:8000/ready", timeout=2)
            if ready_response.status_code == 200:
                ready_data = ready_response.json()
                summary["components"]["database"] = ready_data.get("database", "unknown")
                summary["components"]["qdrant"] = ready_data.get("qdrant", "unknown")
                summary["components"]["ollama"] = ready_data.get("ollama", "unknown")
                summary["components"]["model"] = ready_data.get("model", "unknown")
            else:
                summary["components"]["readiness"] = "not_ready"
    except Exception as e:
        summary["status"] = "error"
        summary["error"] = str(e)
    
    # Check for warnings
    if summary["components"].get("database") != "connected":
        summary["warnings"].append("Database connection issue")
    if summary["components"].get("ollama") != "connected":
        summary["warnings"].append("Ollama connection issue")
    
    if summary["warnings"]:
        summary["status"] = "degraded"
    
    return summary

