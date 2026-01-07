"""Drift detection endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging

from ...services.drift_detection_service import DriftDetectionService
from ...db.repositories.log_repo import LogRepository
from ...db.models.drift_log import DriftLog
from ...db.postgres import AsyncSessionLocal
from ...api.dependencies import get_log_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["drift"])


def get_drift_service(log_repo: LogRepository = Depends(get_log_repo)) -> DriftDetectionService:
    """Dependency for drift detection service."""
    return DriftDetectionService(log_repo)


@router.get("/drift/check")
async def check_drift(
    drift_service: DriftDetectionService = Depends(get_drift_service),
    data_threshold: Optional[float] = None,
    performance_threshold: Optional[float] = None,
):
    """
    Check for data and performance drift.
    
    Returns comprehensive drift analysis including:
    - Data drift scores per feature
    - Performance drift metrics (if ground truth available)
    - Overall recommendation (retrain, monitor, no_action)
    """
    try:
        result = await drift_service.check_drift(
            data_drift_threshold=data_threshold,
            performance_drift_threshold=performance_threshold
        )
        
        # Log drift detection result
        try:
            async with AsyncSessionLocal() as session:
                from ...db.repositories.log_repo import LogRepository
                log_repo = LogRepository(session)
                
                drift_log = DriftLog(
                    data_drift_score=result["data_drift"].get("data_drift_score", 0.0),
                    performance_drift_score=result["performance_drift"].get("performance_drift_score"),
                    drift_detected=result["drift_detected"],
                    recommendation=result["recommendation"],
                    drift_metadata={
                        "data_drift": result["data_drift"],
                        "performance_drift": result["performance_drift"]
                    }
                )
                await log_repo.log_drift(drift_log)
                await session.commit()
        except Exception as log_error:
            logger.warning(f"Failed to log drift detection: {log_error}", exc_info=True)
        
        return result
    except Exception as e:
        logger.error(f"Drift detection error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drift/history")
async def get_drift_history(
    limit: int = 10,
    log_repo: LogRepository = Depends(get_log_repo),
):
    """Get drift detection history."""
    try:
        drift_logs = await log_repo.get_drift_logs(limit=limit)
        return {
            "count": len(drift_logs),
            "history": [
                {
                    "id": str(log.id),
                    "detection_date": log.detection_date.isoformat(),
                    "data_drift_score": log.data_drift_score,
                    "performance_drift_score": log.performance_drift_score,
                    "drift_detected": log.drift_detected,
                    "recommendation": log.recommendation,
                    "metadata": log.drift_metadata
                }
                for log in drift_logs
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching drift history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drift/status")
async def get_drift_status(
    drift_service: DriftDetectionService = Depends(get_drift_service),
    log_repo: LogRepository = Depends(get_log_repo),
):
    """Get current drift status (latest detection result)."""
    try:
        # Get latest drift log
        drift_logs = await log_repo.get_drift_logs(limit=1)
        
        if not drift_logs:
            return {
                "status": "unknown",
                "message": "No drift detection has been run yet",
                "last_check": None
            }
        
        latest = drift_logs[0]
        
        return {
            "status": "drift_detected" if latest.drift_detected else "no_drift",
            "data_drift_score": latest.data_drift_score,
            "performance_drift_score": latest.performance_drift_score,
            "recommendation": latest.recommendation,
            "last_check": latest.detection_date.isoformat(),
            "metadata": latest.drift_metadata
        }
    except Exception as e:
        logger.error(f"Error fetching drift status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

